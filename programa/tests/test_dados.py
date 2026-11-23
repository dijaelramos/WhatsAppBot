import json
import unittest
from datetime import datetime, timedelta

import pandas as pd

from core.destinatarios import carregar_descadastro, montar_destinatarios
from core.erros import EntradaInvalida, ErroEstado
from core.estado import (
    Progresso,
    arquivar_progresso,
    carregar_estado,
    progresso_de_dados,
    salvar_progresso,
)
from core.excel import ler_contatos
from core.horario import ajustar_fim_da_espera, em_pausa_noturna, fim_da_pausa
from core.mensagem import personalizar_mensagem, validar_variaveis
from core.telefone import normalizar_telefone
from tests.base import TesteIsolado


class TelefoneTeste(unittest.TestCase):
    def test_acrescenta_55(self):
        self.assertEqual(
            normalizar_telefone("(85) 99999-9999", True), "5585999999999"
        )

    def test_ddd_55_recebe_codigo_do_pais(self):
        self.assertEqual(
            normalizar_telefone("55999998888", True), "5555999998888"
        )

    def test_mantem_numero_completo(self):
        self.assertEqual(
            normalizar_telefone(5581999999999.0, True), "5581999999999"
        )
        self.assertEqual(
            normalizar_telefone("5581999999999", False), "5581999999999"
        )

    def test_remove_zero_de_discagem(self):
        self.assertEqual(
            normalizar_telefone("085999999999", True), "5585999999999"
        )

    def test_rejeita_invalidos(self):
        for valor in (None, float("nan"), "", "123", "abc"):
            self.assertIsNone(normalizar_telefone(valor, True), valor)
        self.assertIsNone(normalizar_telefone("85999999999", False))


class HorarioTeste(unittest.TestCase):
    def test_pausa_comum(self):
        self.assertTrue(em_pausa_noturna(datetime(2026, 1, 1, 3), 0, 6))
        self.assertFalse(em_pausa_noturna(datetime(2026, 1, 1, 6), 0, 6))

    def test_pausa_cruzando_meia_noite(self):
        self.assertTrue(em_pausa_noturna(datetime(2026, 1, 1, 23), 20, 8))
        self.assertTrue(em_pausa_noturna(datetime(2026, 1, 1, 7), 20, 8))
        self.assertFalse(em_pausa_noturna(datetime(2026, 1, 1, 12), 20, 8))

    def test_espera_que_termina_na_pausa_e_adiada(self):
        agora = datetime(2026, 1, 1, 23, 55)
        self.assertEqual(
            ajustar_fim_da_espera(agora, 600, 0, 6),
            datetime(2026, 1, 2, 6, 0),
        )

    def test_espera_que_termina_depois_da_pausa_nao_muda(self):
        agora = datetime(2026, 1, 1, 23, 0)
        self.assertEqual(
            ajustar_fim_da_espera(agora, 8 * 3600, 0, 6),
            agora + timedelta(hours=8),
        )

    def test_fim_da_pausa_no_dia_seguinte(self):
        self.assertEqual(
            fim_da_pausa(datetime(2026, 1, 1, 23), 8),
            datetime(2026, 1, 2, 8),
        )


class MensagemTeste(unittest.TestCase):
    def test_ignora_coluna_do_telefone(self):
        contato = {1: "Ana", 2: "Bruno", 3: "5581999999999", 4: "Python"}
        self.assertEqual(
            personalizar_mensagem("{var1} {VAR2} {var3}", contato, 3, 3),
            "Ana Bruno Python",
        )

    def test_formata_numeros_e_datas(self):
        contato = {1: 12.0, 2: datetime(2026, 11, 9), 3: "5581999999999"}
        self.assertEqual(
            personalizar_mensagem("{var1} {var2}", contato, 2, 3),
            "12 09/11/2026",
        )

    def test_bloqueia_variavel_sem_coluna(self):
        with self.assertRaises(EntradaInvalida):
            validar_variaveis("{var1} {var3}", 2, 5)
        validar_variaveis("{var1} {var2}", 2, 5)


class PlanilhaTeste(TesteIsolado):
    def criar_planilha(self, linhas):
        arquivo = self.pasta / "contatos.xlsx"
        pd.DataFrame(linhas).to_excel(arquivo, header=False, index=False)
        return arquivo

    def test_celula_vazia_nunca_vira_nan(self):
        arquivo = self.criar_planilha(
            [["Nome", "Fone"], [None, 5581999999999], ["Bia", 5581988888888]]
        )
        contatos = ler_contatos(arquivo)
        self.assertIsNone(contatos[0][1])

        selecao = montar_destinatarios(
            contatos, "Oi {var1}", 2, True, 1, set()
        )
        self.assertEqual(selecao.incompletos, [1])
        self.assertEqual(selecao.destinatarios[0].texto, "Oi Bia")

    def test_planilha_sem_contatos(self):
        arquivo = self.criar_planilha([["Nome", "Fone"]])
        with self.assertRaises(EntradaInvalida):
            ler_contatos(arquivo)

    def test_triagem(self):
        contatos = [
            {1: "Ana", 2: "81999999999"},
            {1: "Ana de novo", 2: "(81) 99999-9999"},
            {1: "Sem fone", 2: None},
            {1: "Saiu", 2: "81977777777"},
        ]
        selecao = montar_destinatarios(
            contatos, "Oi {var1}", 2, True, 1, {"5581977777777"}
        )
        self.assertEqual(len(selecao.destinatarios), 1)
        self.assertEqual(selecao.duplicados, [2])
        self.assertEqual(selecao.invalidos, [3])
        self.assertEqual(selecao.descadastrados, [4])

    def test_descadastro(self):
        arquivo = self.pasta / "descadastro.txt"
        self.assertEqual(carregar_descadastro(arquivo), set())
        self.assertTrue(arquivo.exists())

        arquivo.write_text(
            "# comentario\n(81) 97777-7777\n5581966666666\nlixo\n",
            encoding="utf-8",
        )
        self.assertEqual(
            carregar_descadastro(arquivo),
            {"5581977777777", "5581966666666"},
        )


class EstadoTeste(TesteIsolado):
    def test_salva_e_carrega(self):
        salvar_progresso(Progresso(enviados={"a"}, falhos={"b"}, erros=2))
        progresso = progresso_de_dados(carregar_estado(), [])
        self.assertEqual(progresso.enviados, {"a"})
        self.assertEqual(progresso.falhos, {"b"})
        self.assertEqual(progresso.erros, 2)

    def test_arquivo_corrompido_usa_backup(self):
        salvar_progresso(Progresso(enviados={"a"}))
        salvar_progresso(Progresso(enviados={"a", "b"}))
        self.arquivo_estado.write_text("{quebrado", encoding="utf-8")

        progresso = progresso_de_dados(carregar_estado(), [])
        self.assertEqual(progresso.enviados, {"a"})
        self.assertTrue(self.arquivo_estado.exists())

    def test_corrompido_sem_backup_para_e_nao_apaga(self):
        self.arquivo_estado.write_text("", encoding="utf-8")
        with self.assertRaises(ErroEstado):
            carregar_estado()
        self.assertTrue(self.arquivo_estado.exists())

    def test_migra_formato_antigo_por_telefone(self):
        self.arquivo_estado.write_text("{}", encoding="utf-8")
        dados = {
            "ultimo_indice": 2,
            "enviados": 1,
            "erros": 3,
            "enviados_indices": [0],
            "falhos_indices": [0, 1, 2, 99],
        }
        progresso = progresso_de_dados(dados, ["tel0", "tel1", None])
        self.assertEqual(progresso.enviados, {"tel0"})
        self.assertEqual(progresso.falhos, {"tel1"})
        self.assertEqual(progresso.erros, 3)
        self.assertEqual(
            len(list(self.pasta.glob("estado_formato_antigo_*.json"))), 1
        )

    def test_arquiva_em_vez_de_apagar(self):
        salvar_progresso(Progresso(enviados={"a"}))
        arquivar_progresso()
        self.assertFalse(self.arquivo_estado.exists())
        arquivados = list(self.pasta.glob("estado_arquivado_*.json"))
        self.assertEqual(len(arquivados), 1)
        conteudo = json.loads(arquivados[0].read_text(encoding="utf-8"))
        self.assertEqual(conteudo["enviados"], ["a"])


if __name__ == "__main__":
    unittest.main()
