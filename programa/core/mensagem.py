import re

from config import ARQUIVO_MENSAGEM


def carregar_mensagem():
    """Carrega o texto-base que sera personalizado para cada contato."""
    print("Carregando mensagem...")
    with open(
        ARQUIVO_MENSAGEM,
        "r",
        encoding="utf-8"
    ) as arquivo:
        return arquivo.read()

def personalizar_mensagem(
    texto,
    contato,
    quantidade_variaveis=5,
    coluna_contato=None,
):
    """Substitui {variavel} pelo valor correspondente do contato,
    sem diferenciar maiúsculas/minúsculas.

    Ex: {nome} casa com a coluna 'Nome', 'NOME' ou 'nome' do Excel.
    Se a variável não existir no contato, o texto é mantido como está
    (não quebra a mensagem)."""

    valores = list(contato.values())
    if coluna_contato is not None:
        indice_contato = coluna_contato - 1
        valores_texto = [
            valor
            for indice, valor in enumerate(valores)
            if indice != indice_contato
        ][:quantidade_variaveis]
    else:
        indice_contato = None
        valores_texto = valores[:quantidade_variaveis]

    def substituir(match):
        # Mantem o marcador original quando a coluna nao existe na planilha.
        variavel = match.group(1).strip().lower()
        if variavel.startswith("var") and variavel[3:].isdigit():
            indice = int(variavel[3:]) - 1
            if 0 <= indice < len(valores_texto):
                return str(valores_texto[indice])
            return match.group(0)
        return match.group(0)

    return re.sub(r"\{(\w+)\}", substituir, texto)
