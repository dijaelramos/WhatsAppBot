from datetime import datetime

from config import ARQUIVO_INEXISTENTES
from core import menu
from core.destinatarios import carregar_telefones, telefones_por_indice
from core.erros import EntradaInvalida
from core.estado import salvar_progresso
from core.excel import impressao_digital, ler_contatos, remover_contatos
from core.logger import log

_CABECALHO = (
    "# Telefones que o WhatsApp informou que não existem.\n"
    "# Preenchido pelo bot. Estes números ficam fora de todas as campanhas.\n"
    "# Apague a linha se um número passar a existir.\n"
)


def carregar_inexistentes(arquivo=None):
    """Le os telefones que o WhatsApp ja informou que nao existem."""
    return carregar_telefones(arquivo or ARQUIVO_INEXISTENTES, _CABECALHO)


def registrar_inexistente(telefone, motivo, arquivo=None):
    """Guarda o numero e o aviso do WhatsApp, valendo para campanhas futuras."""
    arquivo = arquivo or ARQUIVO_INEXISTENTES
    try:
        carregar_inexistentes(arquivo)
        with open(arquivo, "a", encoding="utf-8") as lista:
            lista.write(f"{telefone}  # {datetime.now():%d/%m/%Y %H:%M} {motivo}\n")
    except OSError as erro:
        log(f"AVISO: não consegui registrar o número inexistente: {erro}")


def oferecer_remocao(contatos, coluna, acrescentar_55, progresso=None):
    """Pergunta se deve tirar da planilha os numeros inexistentes.

    Retorna a lista de contatos atualizada. O indice salvo no progresso e
    corrigido para que "continuar" nao pule contatos depois da remocao.
    """
    inexistentes = carregar_inexistentes()
    telefones = telefones_por_indice(contatos, coluna, acrescentar_55)
    posicoes = [
        indice
        for indice, telefone in enumerate(telefones)
        if telefone in inexistentes
    ]
    if not posicoes or not menu.perguntar_remover_inexistentes(len(posicoes)):
        return contatos

    try:
        backup = remover_contatos(
            inexistentes,
            coluna,
            acrescentar_55,
            len(posicoes),
        )
    except EntradaInvalida as erro:
        log(f"Os contatos não foram removidos: {erro}")
        return contatos

    log(f"{len(posicoes)} contato(s) removido(s) da planilha. Backup: {backup}")

    if progresso is not None:
        progresso.ultimo_indice -= sum(
            indice <= progresso.ultimo_indice for indice in posicoes
        )
        progresso.planilha_sha256 = impressao_digital()
        salvar_progresso(progresso)

    return ler_contatos()
