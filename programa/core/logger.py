from datetime import datetime
from config import LOGS

LOGS.mkdir(
    parents=True,
    exist_ok=True,
)

ARQUIVO_LOG = LOGS / (
    f"envio_{datetime.now():%Y%m%d_%H%M%S}.txt"
)


def log(texto):
    """Escreve a mesma informacao no console e no arquivo da campanha."""
    texto = str(texto)
    print(texto)
    with open(
        ARQUIVO_LOG,
        "a",
        encoding="utf-8",
    ) as arquivo:
        arquivo.write(texto + "\n")

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
    titulo("INFINITY CURSOS - WHATSAPP BOT")
    log(
        f"Data/Hora: {datetime.now():%d/%m/%Y %H:%M:%S}"
    )
    log("")

def finalizar_log(total, enviados, erros):
    """Registra o resumo final da campanha."""
    log("")
    linha()
    log("RESUMO")
    linha()
    log(f"Total........: {total}")
    log(f"Enviados.....: {enviados}")
    log(f"Erros........: {erros}")
    log(
        f"Finalizado em: {datetime.now():%d/%m/%Y %H:%M:%S}"
    )
    linha()
