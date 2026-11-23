import hashlib
import os
import shutil
from datetime import datetime

import pandas as pd
from openpyxl import load_workbook

from config import ARQUIVO_EXCEL
from core.erros import EntradaInvalida
from core.telefone import normalizar_telefone


def ler_contatos(arquivo=None):
    """Le a planilha sem depender dos titulos da primeira linha."""
    arquivo = arquivo or ARQUIVO_EXCEL
    print("Lendo planilha...")

    if not arquivo.exists():
        raise EntradaInvalida(f"Planilha não encontrada: {arquivo}")

    # A primeira linha e apenas informativa; as variaveis usam a posicao.
    try:
        df = pd.read_excel(arquivo, header=None)
    except PermissionError as erro:
        raise EntradaInvalida(
            f"Não consegui abrir {arquivo}. Feche a planilha e tente de novo."
        ) from erro

    df = df.iloc[1:].dropna(how="all")

    if len(df.columns) < 2:
        raise EntradaInvalida(
            "A planilha precisa ter pelo menos duas colunas."
        )
    if df.empty:
        raise EntradaInvalida("A planilha não tem contatos.")

    df.columns = range(1, len(df.columns) + 1)
    print(f"Colunas encontradas: {len(df.columns)}")
    print(df.head())

    # Celulas vazias viram None para nunca chegarem ao texto como "nan".
    df = df.astype(object).where(df.notna(), None)
    contatos = df.to_dict("records")

    print(f"{len(contatos)} contatos encontrados.")

    return contatos


def remover_contatos(
    telefones,
    coluna_contato,
    acrescentar_codigo_brasil,
    quantidade_esperada,
    arquivo=None,
):
    """Tira os telefones da planilha, guardando antes uma copia de seguranca.

    Grava em arquivo temporario e confere o resultado antes de substituir a
    planilha original. Retorna o caminho do backup.
    """
    arquivo = arquivo or ARQUIVO_EXCEL
    temporario = arquivo.with_name(f"{arquivo.stem}_remocao_temp.xlsx")
    try:
        total_antes = len(ler_contatos(arquivo))
        livro = load_workbook(arquivo)
        planilha = livro.worksheets[0]
        linhas = [
            linha
            for linha in range(2, planilha.max_row + 1)
            if normalizar_telefone(
                planilha.cell(linha, coluna_contato).value,
                acrescentar_codigo_brasil,
            ) in telefones
        ]
        if len(linhas) != quantidade_esperada:
            raise EntradaInvalida(
                f"Esperava remover {quantidade_esperada} linha(s), "
                f"mas encontrei {len(linhas)}. A planilha não foi alterada."
            )

        for linha in reversed(linhas):
            planilha.delete_rows(linha)
        livro.save(temporario)

        total_depois = len(ler_contatos(temporario))
        if total_depois != total_antes - len(linhas):
            raise EntradaInvalida(
                "A conferência da remoção falhou. A planilha não foi alterada."
            )

        backup = arquivo.with_name(
            f"{arquivo.stem}_backup_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
        )
        shutil.copy2(arquivo, backup)
        os.replace(temporario, arquivo)
        return backup
    except OSError as erro:
        raise EntradaInvalida(
            f"Não consegui alterar {arquivo}. Feche a planilha e tente de novo. "
            f"Detalhe: {erro}"
        ) from erro
    finally:
        temporario.unlink(missing_ok=True)


def impressao_digital(arquivo=None):
    """Identifica o conteudo da planilha para avisar quando ela mudar."""
    arquivo = arquivo or ARQUIVO_EXCEL
    return hashlib.sha256(arquivo.read_bytes()).hexdigest()
