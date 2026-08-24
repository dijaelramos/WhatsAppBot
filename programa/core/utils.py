import time

from core.logger import log


def executar_com_retry(funcao, *args, tentativas=3, **kwargs):
    """Executa uma funcao novamente quando uma tentativa falha."""
    ultimo_erro = None
    # A excecao da ultima tentativa e propagada para o fluxo principal.
    for tentativa in range(1, tentativas + 1):
        try:
            return funcao(*args, **kwargs)
        except Exception as erro:
            ultimo_erro = erro
            log(
                f"Tentativa {tentativa}/{tentativas} falhou."
            )
            time.sleep(3)

    raise ultimo_erro
