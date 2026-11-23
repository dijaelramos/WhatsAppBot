import time
from datetime import datetime, timedelta

from config import HORA_FIM_PAUSA_NOTURNA, HORA_INICIO_PAUSA_NOTURNA


def em_pausa_noturna(
    momento,
    inicio=HORA_INICIO_PAUSA_NOTURNA,
    fim=HORA_FIM_PAUSA_NOTURNA,
):
    """Indica se o horario esta na pausa, inclusive quando ela cruza a meia-noite."""
    if inicio == fim:
        return False
    if inicio < fim:
        return inicio <= momento.hour < fim
    return momento.hour >= inicio or momento.hour < fim


def fim_da_pausa(momento, fim=HORA_FIM_PAUSA_NOTURNA):
    """Retorna o proximo horario de fim da pausa depois de `momento`."""
    alvo = momento.replace(hour=fim, minute=0, second=0, microsecond=0)
    if alvo <= momento:
        alvo += timedelta(days=1)
    return alvo


def ajustar_fim_da_espera(
    agora,
    segundos,
    inicio=HORA_INICIO_PAUSA_NOTURNA,
    fim=HORA_FIM_PAUSA_NOTURNA,
):
    """Adia para o fim da pausa uma espera que terminaria durante ela."""
    fim_previsto = agora + timedelta(seconds=segundos)
    if em_pausa_noturna(fim_previsto, inicio, fim):
        return fim_da_pausa(fim_previsto, fim)
    return fim_previsto


def dormir_ate(alvo, agora=datetime.now, dormir=time.sleep):
    """Espera em etapas curtas para nao errar se o computador suspender."""
    while True:
        restante = (alvo - agora()).total_seconds()
        if restante <= 0:
            return
        dormir(min(restante, 60))
