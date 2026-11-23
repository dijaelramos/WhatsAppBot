import math
import re
from datetime import datetime

from config import ARQUIVO_MENSAGEM
from core.erros import EntradaInvalida

_VARIAVEL = re.compile(r"\{var(\d+)\}", re.IGNORECASE)


def carregar_mensagem(arquivo=None):
    """Carrega o texto-base que sera personalizado para cada contato."""
    arquivo = arquivo or ARQUIVO_MENSAGEM
    print("Carregando mensagem...")
    try:
        texto = arquivo.read_text(encoding="utf-8")
    except OSError as erro:
        raise EntradaInvalida(f"Não consegui ler {arquivo}: {erro}") from erro

    if not texto.strip():
        raise EntradaInvalida(f"A mensagem está vazia: {arquivo}")
    return texto


def formatar_valor(valor):
    """Converte uma celula em texto sem expor 'nan' ou '12.0' ao cliente."""
    if valor is None:
        return ""
    if isinstance(valor, float):
        if math.isnan(valor):
            return ""
        if valor.is_integer():
            return str(int(valor))
    if isinstance(valor, datetime):
        return f"{valor:%d/%m/%Y}"
    return str(valor).strip()


def valores_das_variaveis(contato, coluna_contato, quantidade_variaveis):
    """Lista os valores de {var1}, {var2}... ignorando a coluna do telefone."""
    valores = [
        formatar_valor(valor)
        for indice, valor in enumerate(contato.values(), start=1)
        if indice != coluna_contato
    ]
    return valores[:quantidade_variaveis]


def variaveis_usadas(texto):
    """Retorna os numeros das variaveis {varN} presentes no texto."""
    return {int(numero) for numero in _VARIAVEL.findall(texto)}


def validar_variaveis(texto, quantidade_variaveis, colunas_disponiveis):
    """Impede que um marcador sem coluna seja enviado literalmente ao cliente."""
    limite = min(quantidade_variaveis, colunas_disponiveis)
    invalidas = sorted(
        numero
        for numero in variaveis_usadas(texto)
        if not 1 <= numero <= limite
    )
    if invalidas:
        nomes = ", ".join(f"{{var{numero}}}" for numero in invalidas)
        raise EntradaInvalida(
            f"A mensagem usa {nomes}, mas só há {limite} variável(is) "
            "disponível(is). Ajuste a mensagem ou a quantidade de variáveis."
        )


def variaveis_vazias(texto, contato, coluna_contato, quantidade_variaveis):
    """Retorna as variaveis usadas na mensagem que estao em branco no contato."""
    valores = valores_das_variaveis(
        contato,
        coluna_contato,
        quantidade_variaveis,
    )
    return sorted(
        numero
        for numero in variaveis_usadas(texto)
        if numero <= len(valores) and not valores[numero - 1]
    )


def personalizar_mensagem(
    texto,
    contato,
    quantidade_variaveis=5,
    coluna_contato=None,
):
    """Substitui {varN} pelo valor da coluna correspondente do contato."""
    valores = valores_das_variaveis(
        contato,
        coluna_contato,
        quantidade_variaveis,
    )

    def substituir(match):
        indice = int(match.group(1)) - 1
        if 0 <= indice < len(valores):
            return valores[indice]
        return match.group(0)

    return _VARIAVEL.sub(substituir, texto)
