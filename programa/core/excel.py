import pandas as pd

from config import ARQUIVO_EXCEL


def ler_contatos():
    """Le a planilha sem depender dos titulos da primeira linha."""
    print("Lendo planilha...")

    # A primeira linha e apenas informativa; as variaveis usam a posicao.
    df = pd.read_excel(ARQUIVO_EXCEL, header=None)
    df = df.iloc[1:].dropna(how="all")

    if len(df.columns) < 2:
        raise ValueError(
            "A planilha precisa ter pelo menos duas colunas."
        )

    df.columns = range(1, len(df.columns) + 1)
    print(f"Colunas encontradas: {len(df.columns)}")
    print(df.head())

    contatos = df.to_dict("records")

    print(f"{len(contatos)} contatos encontrados.")

    return contatos
