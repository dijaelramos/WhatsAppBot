import json

from datetime import datetime
from config import ARQUIVO_ESTADO
from core.logger import log


def salvar_progresso(
    indice,
    nome,
    telefone,
    enviados=0,
    erros=0,
    enviados_indices=None,
    falhos_indices=None,
):
    """
    Salva o andamento atual do envio em JSON.

    Os indices sao persistidos para diferenciar contatos ja enviados de
    contatos que precisam ser tentados novamente depois de uma falha.
    """
    # Garante que o diretorio runtime exista antes de criar o arquivo.
    ARQUIVO_ESTADO.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    # O formato e simples e legivel para facilitar diagnostico manual.
    dados = {
        "ultimo_indice": indice,
        "nome": nome,
        "telefone": telefone,
        "enviados": enviados,
        "erros": erros,
        "enviados_indices": sorted(enviados_indices or []),
        "falhos_indices": sorted(falhos_indices or []),
        "data_hora": datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        ),
    }
    with open(
        ARQUIVO_ESTADO,
        "w",
        encoding="utf-8",
    ) as arquivo:

        json.dump(
            dados,
            arquivo,
            indent=4,
            ensure_ascii=False,
        )

def carregar_progresso():
    """
    Retorna o progresso salvo ou None.
    """
    # Ausencia de estado significa que a campanha deve comecar do zero.
    if not ARQUIVO_ESTADO.exists():
        return None
    if ARQUIVO_ESTADO.stat().st_size == 0:
        log("")
        log("Arquivo estado.json vazio.")
        log("Removendo arquivo...")
        limpar_progresso()
        return None

    # JSON invalido nao deve impedir uma nova execucao limpa.
    try:
        with open(
            ARQUIVO_ESTADO,
            "r",
            encoding="utf-8",
        ) as arquivo:
            return json.load(arquivo)
    except json.JSONDecodeError:
        log("")
        log("Arquivo estado.json corrompido.")
        log("O arquivo será removido automaticamente.")
        limpar_progresso()
        return None
    except Exception as erro:
        log("")
        log("Erro ao carregar estado.json")
        log(str(erro))
        limpar_progresso()
        return None

def existe_progresso():
    """
    Retorna True quando existe um progresso válido.
    """
    return carregar_progresso() is not None

def limpar_progresso():
    """
    Remove o arquivo de progresso.
    """
    # O arquivo so e removido quando todos os contatos foram resolvidos.
    try:

        if ARQUIVO_ESTADO.exists():
            ARQUIVO_ESTADO.unlink()
            log("estado.json removido.")
    except Exception as erro:
        log(f"Erro ao remover estado.json: {erro}")