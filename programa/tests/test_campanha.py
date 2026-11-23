import unittest
from datetime import datetime, timedelta
from unittest import mock

from core.campanha import Campanha
from core.destinatarios import Destinatario
from core.erros import ErroEstado, NumeroInvalido, SessaoPerdida
from core.estado import Progresso
from tests.base import TesteIsolado


class CanalFalso:
    """Registra as acoes e falha conforme o roteiro de cada teste."""

    def __init__(self, falhas=None):
        self.falhas = falhas or {}
        self.acoes = []
        self.reinicios = 0

    def _acao(self, nome, telefone):
        self.acoes.append((nome, telefone))
        roteiro = self.falhas.get((nome, telefone))
        if roteiro:
            raise roteiro.pop(0)

    def abrir_conversa(self, telefone):
        self.atual = telefone
        self._acao("abrir", telefone)

    def anexar_midia(self, caminho):
        self._acao("anexar", self.atual)

    def enviar_midia(self):
        self._acao("midia", self.atual)

    def enviar_texto(self, texto):
        self._acao("texto", self.atual)
        return True

    def reiniciar(self):
        self.reinicios += 1

    def contagem(self, nome, telefone):
        return self.acoes.count((nome, telefone))


class RelogioFalso:
    def __init__(self, inicio=datetime(2026, 1, 5, 10)):
        self.momento = inicio
        self.esperas = []

    def agora(self):
        return self.momento

    def dormir(self, segundos):
        self.esperas.append(segundos)
        self.momento += timedelta(seconds=segundos)


def pessoas(quantidade):
    return [
        Destinatario(indice, f"P{indice}", f"tel{indice}", "oi")
        for indice in range(quantidade)
    ]


class CampanhaTeste(TesteIsolado):
    def rodar(self, destinatarios, canal, progresso=None, midia=None, **opcoes):
        self.relogio = RelogioFalso(opcoes.pop("inicio", datetime(2026, 1, 5, 10)))
        self.progresso = progresso or Progresso()
        parametros = {
            "intervalo": (1, 1),
            "tamanho_lote": 1000,
            "pausa_lote": 3600,
            "limite_erros": 3,
            "limite_reinicios": 2,
        }
        parametros.update(opcoes)
        campanha = Campanha(
            destinatarios,
            destinatarios,
            self.progresso,
            canal,
            midia,
            len(destinatarios),
            agora=self.relogio.agora,
            dormir=self.relogio.dormir,
            **parametros,
        )
        return campanha.executar()

    def test_envia_para_todos(self):
        canal = CanalFalso()
        self.assertTrue(self.rodar(pessoas(3), canal))
        self.assertEqual(self.progresso.enviados, {"tel0", "tel1", "tel2"})
        self.assertFalse(self.progresso.falhos)

    def test_midia_nao_repete_quando_texto_falha(self):
        canal = CanalFalso({("texto", "tel0"): [RuntimeError("falhou")]})
        self.rodar(pessoas(1), canal, midia="foto.png")
        self.assertEqual(canal.contagem("midia", "tel0"), 1)
        self.assertEqual(canal.contagem("texto", "tel0"), 2)
        self.assertIn("tel0", self.progresso.enviados)
        self.assertFalse(self.progresso.midia_enviada)

    def test_falha_e_refeita_na_varredura_final(self):
        canal = CanalFalso({("abrir", "tel0"): [RuntimeError("timeout")]})
        self.assertTrue(self.rodar(pessoas(2), canal))
        self.assertEqual(
            [a for a in canal.acoes if a[0] == "abrir"],
            [("abrir", "tel0"), ("abrir", "tel1"), ("abrir", "tel0")],
        )
        self.assertFalse(self.progresso.falhos)

    def test_numero_invalido_nao_e_refeito(self):
        canal = CanalFalso({("abrir", "tel0"): [NumeroInvalido("x")]})
        self.rodar(pessoas(2), canal)
        self.assertEqual(canal.contagem("abrir", "tel0"), 1)
        self.assertEqual(self.progresso.invalidos, {"tel0"})
        self.assertEqual(canal.reinicios, 0)

    def test_numero_inexistente_fica_registrado_e_nao_conta_como_envio(self):
        erro = NumeroInvalido("5581999999999: número inválido")
        canal = CanalFalso({("abrir", "tel0"): [erro]})
        self.rodar(pessoas(2), canal)
        self.assertEqual(self.progresso.enviados, {"tel1"})
        self.assertFalse(self.progresso.falhos)
        conteudo = (self.pasta / "inexistentes.txt").read_text(encoding="utf-8")
        self.assertIn("tel0  # ", conteudo)

    def test_sessao_perdida_reinicia_e_refaz_o_contato(self):
        canal = CanalFalso({("abrir", "tel0"): [SessaoPerdida("caiu")]})
        self.assertTrue(self.rodar(pessoas(1), canal))
        self.assertEqual(canal.reinicios, 1)
        self.assertEqual(self.progresso.enviados, {"tel0"})

    def test_erros_seguidos_reiniciam_e_recolocam_o_bloco(self):
        falhas = {
            ("abrir", f"tel{i}"): [RuntimeError("x")] for i in range(3)
        }
        canal = CanalFalso(falhas)
        self.assertTrue(self.rodar(pessoas(4), canal))
        self.assertEqual(canal.reinicios, 1)
        self.assertEqual(len(self.progresso.enviados), 4)

    def test_problema_persistente_interrompe_a_campanha(self):
        falhas = {
            ("abrir", f"tel{i}"): [RuntimeError("x")] * 50 for i in range(50)
        }
        canal = CanalFalso(falhas)
        self.assertFalse(self.rodar(pessoas(50), canal))
        self.assertEqual(canal.reinicios, 2)
        self.assertLessEqual(self.progresso.erros, 9)
        self.assertTrue(self.arquivo_estado.exists())

    def test_falha_ao_reiniciar_nao_derruba_o_programa(self):
        canal = CanalFalso({("abrir", "tel0"): [SessaoPerdida("caiu")]})
        canal.reiniciar = mock.Mock(side_effect=RuntimeError("sem chrome"))
        self.assertFalse(self.rodar(pessoas(1), canal))
        self.assertEqual(canal.reiniciar.call_count, 2)

    def test_erro_ao_salvar_para_a_campanha(self):
        canal = CanalFalso()
        with mock.patch(
            "core.campanha.salvar_progresso",
            side_effect=ErroEstado("disco"),
        ):
            with self.assertRaises(ErroEstado):
                self.rodar(pessoas(2), canal)

    def test_pausa_de_lote_fica_salva_e_termina(self):
        canal = CanalFalso()
        self.rodar(pessoas(3), canal, tamanho_lote=2, pausa_lote=3600)
        self.assertGreaterEqual(sum(self.relogio.esperas), 3602)
        self.assertIsNone(self.progresso.retomar_apos)

    def test_retoma_pausa_de_lote_salva(self):
        canal = CanalFalso()
        inicio = datetime(2026, 1, 5, 10)
        progresso = Progresso(
            retomar_apos=(inicio + timedelta(hours=2)).isoformat()
        )
        self.rodar(pessoas(1), canal, progresso=progresso, inicio=inicio)
        self.assertGreaterEqual(self.relogio.momento, inicio + timedelta(hours=2))
        self.assertIsNone(self.progresso.retomar_apos)

    def test_nao_envia_durante_a_pausa_noturna(self):
        canal = CanalFalso()
        inicio = datetime(2026, 1, 5, 3)
        self.rodar(pessoas(1), canal, inicio=inicio)
        self.assertGreaterEqual(self.relogio.momento.hour, 6)

    def test_falha_de_campanha_antiga_nao_entra_em_outra_lista(self):
        canal = CanalFalso()
        progresso = Progresso(falhos={"telefone_que_saiu_da_planilha"})
        self.assertTrue(self.rodar(pessoas(1), canal, progresso=progresso))
        self.assertEqual(
            {a[1] for a in canal.acoes if a[0] == "abrir"}, {"tel0"}
        )


if __name__ == "__main__":
    unittest.main()
