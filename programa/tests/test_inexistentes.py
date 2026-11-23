import unittest
from unittest import mock

import pandas as pd
from openpyxl import load_workbook

from core import inexistentes as modulo
from core.destinatarios import montar_destinatarios
from core.envio import aviso_de_numero_inexistente
from core.erros import EntradaInvalida
from core.estado import Progresso
from core.excel import ler_contatos, remover_contatos
from tests.base import TesteIsolado


class AvisoTeste(unittest.TestCase):
    def test_reconhece_avisos_de_numero_inexistente(self):
        for aviso in (
            "O número de telefone compartilhado por URL é inválido.",
            "Phone number shared via url is invalid.",
            "Este número não existe no WhatsApp",
            "Contato não foi encontrado",
            "O NÚMERO NÃO ESTÁ NO WHATSAPP",
            "This phone number isn’t on WhatsApp, it was not found",
        ):
            self.assertTrue(aviso_de_numero_inexistente(aviso), aviso)

    def test_ignora_outros_avisos(self):
        for aviso in (
            "Sessão inválida, tente novamente",
            "Iniciando conversa",
            "Não foi possível conectar ao telefone",
            "Página não encontrada",
            "",
        ):
            self.assertFalse(aviso_de_numero_inexistente(aviso), aviso)


class ListaTeste(TesteIsolado):
    def test_registra_com_o_aviso_e_le_somente_o_numero(self):
        modulo.registrar_inexistente("5581999999999", "número inválido # 1")
        modulo.registrar_inexistente("5581988888888", "não existe")
        self.assertEqual(
            modulo.carregar_inexistentes(),
            {"5581999999999", "5581988888888"},
        )

    def test_triagem_tira_inexistentes_da_campanha(self):
        contatos = [
            {1: "Ana", 2: "81999999999"},
            {1: "Bia", 2: "81988888888"},
        ]
        selecao = montar_destinatarios(
            contatos, "Oi {var1}", 2, True, 1, set(), {"5581999999999"}
        )
        self.assertEqual(selecao.inexistentes, [1])
        self.assertEqual(
            [d.nome for d in selecao.destinatarios], ["Bia"]
        )


class RemocaoTeste(TesteIsolado):
    def setUp(self):
        super().setUp()
        self.arquivo = self.pasta / "contatos.xlsx"
        pd.DataFrame(
            [
                ["Nome", "Fone"],
                ["Ana", 5581999999990],
                ["Bia", 5581999999991],
                ["Cid", 5581999999992],
                ["Dan", 5581999999993],
            ]
        ).to_excel(self.arquivo, header=False, index=False)
        patcher = mock.patch("core.excel.ARQUIVO_EXCEL", self.arquivo)
        patcher.start()
        self.addCleanup(patcher.stop)

    def nomes(self):
        return [c[1] for c in ler_contatos(self.arquivo)]

    def test_remove_somente_os_numeros_informados_e_faz_backup(self):
        backup = remover_contatos(
            {"5581999999991", "5581999999993"}, 2, False, 2, self.arquivo
        )
        self.assertEqual(self.nomes(), ["Ana", "Cid"])
        self.assertTrue(backup.exists())
        self.assertEqual(len(ler_contatos(backup)), 4)
        self.assertEqual(
            load_workbook(self.arquivo).worksheets[0]["A1"].value, "Nome"
        )

    def test_quantidade_divergente_nao_altera_a_planilha(self):
        with self.assertRaises(EntradaInvalida):
            remover_contatos({"5581999999991"}, 2, False, 2, self.arquivo)
        self.assertEqual(len(self.nomes()), 4)
        self.assertEqual(list(self.pasta.glob("*_backup_*.xlsx")), [])

    def test_planilha_aberta_mantem_o_original(self):
        with mock.patch("core.excel.os.replace", side_effect=PermissionError("aberta")):
            with self.assertRaises(EntradaInvalida):
                remover_contatos({"5581999999991"}, 2, False, 1, self.arquivo)
        self.assertEqual(len(self.nomes()), 4)
        self.assertEqual(list(self.pasta.glob("*_remocao_temp*")), [])

    def oferecer(self, resposta, progresso=None):
        contatos = ler_contatos(self.arquivo)
        with mock.patch(
            "core.menu.perguntar_remover_inexistentes", return_value=resposta
        ):
            return modulo.oferecer_remocao(contatos, 2, False, progresso)

    def test_recusar_nao_altera_nada(self):
        modulo.registrar_inexistente("5581999999991", "x")
        self.assertEqual(len(self.oferecer(False)), 4)
        self.assertEqual(len(self.nomes()), 4)

    def test_sem_inexistentes_nao_pergunta(self):
        contatos = ler_contatos(self.arquivo)
        with mock.patch("core.menu.perguntar_remover_inexistentes") as pergunta:
            modulo.oferecer_remocao(contatos, 2, False)
        pergunta.assert_not_called()

    def test_corrige_posicao_salva_para_nao_pular_contatos(self):
        modulo.registrar_inexistente("5581999999990", "x")
        modulo.registrar_inexistente("5581999999993", "x")
        progresso = Progresso(ultimo_indice=2, telefone="5581999999992")

        contatos = self.oferecer(True, progresso)

        self.assertEqual(len(contatos), 2)
        self.assertEqual(progresso.ultimo_indice, 1)
        self.assertEqual(list(contatos[1].values())[0], "Cid")
        self.assertTrue(self.arquivo_estado.exists())
        self.assertTrue(progresso.planilha_sha256)


if __name__ == "__main__":
    unittest.main()
