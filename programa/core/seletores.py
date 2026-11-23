"""Tudo que depende da pagina do WhatsApp Web fica neste arquivo.

Quando o WhatsApp mudar a interface, normalmente so este arquivo precisa mudar.
Os textos cobrem a interface em portugues e em ingles.
"""
from selenium.webdriver.common.by import By

URL_WHATSAPP = "https://web.whatsapp.com"
URL_CONVERSA = URL_WHATSAPP + "/send?phone={telefone}"

CAIXA_MENSAGEM = (By.XPATH, "//footer//div[@contenteditable='true']")

LISTA_CONVERSAS = (By.CSS_SELECTOR, "div[id='pane-side']")

TELA_LOGIN = (
    By.CSS_SELECTOR,
    "div[data-ref], div[data-testid='qrcode'], canvas[aria-label*='QR']",
)

TELA_INICIAL = (
    By.CSS_SELECTOR,
    "div[id='pane-side'], div[data-ref], div[data-testid='qrcode'], "
    "canvas[aria-label]",
)

DIALOGOS = (By.CSS_SELECTOR, "[role='dialog'], [data-animate-modal-popup='true']")

# Um aviso so conta como numero inexistente se citar o numero E o problema.
# Os textos ficam sem acento e em minusculas. Se o WhatsApp usar outra frase,
# ela aparece no log ("Avisos na tela") e basta acrescenta-la aqui.
AVISO_ASSUNTO = ("numero", "telefone", "contato", "phone", "number", "contact")
AVISO_PROBLEMA = (
    "invalid",
    "nao existe",
    "nao foi encontrad",
    "nao encontrad",
    "nao esta no whatsapp",
    "nao tem whatsapp",
    "not on whatsapp",
    "doesn't exist",
    "does not exist",
    "not found",
)

BOTAO_ANEXAR = [
    (By.XPATH, "//button[@aria-label='Anexar' or @aria-label='Attach']"),
    (By.XPATH, "//div[@role='button' and (@aria-label='Anexar' or @aria-label='Attach')]"),
    (By.XPATH, "//span[@data-testid='clip']"),
    (By.XPATH, "//span[@data-testid='plus-rounded']"),
    (By.XPATH, "//div[@data-testid='attach']"),
]

ITEM_FOTOS_VIDEOS = [
    (By.XPATH, "//div[contains(@aria-label,'Fotos e vídeos')]"),
    (By.XPATH, "//span[contains(text(),'Fotos e vídeos')]"),
    (By.XPATH, "//div[contains(@aria-label,'Photos and videos')]"),
    (By.XPATH, "//div[contains(@aria-label,'Photos & videos')]"),
    (By.XPATH, "//span[contains(text(),'Photos & videos')]"),
    (By.XPATH, "//div[contains(@aria-label,'Galeria')]"),
]

INPUT_ARQUIVO = (By.XPATH, "//input[@type='file']")

BOTAO_ENVIAR_MIDIA = [
    (
        By.XPATH,
        "//div[@role='button' and "
        "(contains(@aria-label,'Enviar') or contains(@aria-label,'Send'))]",
    ),
]

# Resume a ultima mensagem enviada: identificador e se ainda esta pendente.
SCRIPT_ULTIMA_ENVIADA = """
const enviadas = document.querySelectorAll('div.message-out');
if (!enviadas.length) { return null; }
const ultima = enviadas[enviadas.length - 1];
const comId = ultima.closest('[data-id]') || ultima.querySelector('[data-id]');
return {
    id: comId ? comId.getAttribute('data-id') : '',
    total: enviadas.length,
    pendente: !!ultima.querySelector("[data-icon='msg-time']"),
};
"""
