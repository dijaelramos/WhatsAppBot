import re

_TELEFONE_BRASIL = re.compile(r"55[1-9][1-9]\d{8,9}")


def normalizar_telefone(valor, acrescentar_codigo_brasil):
    """Retorna o telefone no formato 55 + DDD + numero, ou None se for invalido.

    O codigo do pais e decidido pelo tamanho, e nao pelo prefixo: um numero
    do DDD 55 (RS) sem codigo do pais tambem comeca com 55.
    """
    bruto = str(valor).strip()
    if bruto.endswith(".0"):
        bruto = bruto[:-2]
    digitos = re.sub(r"\D", "", bruto)

    if acrescentar_codigo_brasil:
        digitos = digitos.lstrip("0")
        if len(digitos) in {10, 11}:
            digitos = "55" + digitos

    return digitos if _TELEFONE_BRASIL.fullmatch(digitos) else None
