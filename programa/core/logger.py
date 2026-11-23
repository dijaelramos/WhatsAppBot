from datetime import datetime
from config import LOGS

ARQUIVO_LOG = LOGS / (
    f"envio_{datetime.now():%Y%m%d_%H%M%S}.txt"
)


def log(texto):
    """Escreve no console e no arquivo; falha de disco nao interrompe o envio."""
    texto = str(texto)
    print(texto)
    try:
        ARQUIVO_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(
            ARQUIVO_LOG,
            "a",
            encoding="utf-8",
        ) as arquivo:
            arquivo.write(texto + "\n")
    except OSError as erro:
        print(f"AVISO: não consegui gravar o log: {erro}")

def linha():
    # Separador visual usado nas secoes do log.
    log("=" * 70)

def titulo(texto):
    """Registra um titulo destacado no console e no arquivo."""
    linha()
    log(texto)
    linha()

def iniciar_log():
    """Abre a identificacao da campanha atual."""
    titulo("WHATSAPP BOT")
    log(
        f"Data/Hora: {datetime.now():%d/%m/%Y %H:%M:%S}"
    )
    log("")

def finalizar_log(total, progresso):
    """Registra o resumo final da campanha."""
    log("")
    linha()
    log("RESUMO")
    linha()
    log(f"Total na fila...........: {total}")
    log(f"Enviados................: {len(progresso.enviados)}")
    log(f"Sem confirmação visual..: {len(progresso.nao_confirmados)}")
    log(f"Falhas pendentes........: {len(progresso.falhos)}")
    log(f"Números inválidos.......: {len(progresso.invalidos)}")
    log(f"Tentativas com erro.....: {progresso.erros}")
    log(
        f"Finalizado em: {datetime.now():%d/%m/%Y %H:%M:%S}"
    )
    linha()
