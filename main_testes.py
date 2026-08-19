from preparar_ambiente import preparar

from whatsapp import (
    iniciar_chrome,
    abrir_whatsapp_web
)

from excel import ler_contatos

from envio import abrir_conversa

preparar()

driver = iniciar_chrome()

abrir_whatsapp_web(driver)

contatos = ler_contatos()

abrir_conversa(
    driver,
    contatos[0]["telefone"]
)

input("ENTER")