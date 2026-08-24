import time
import shutil
import tempfile

import pyperclip
import pyautogui

from pathlib import Path
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from core.logger import log


def fechar_dialogo_nativo():
    """Fecha qualquer diálogo nativo do Windows (ex: 'Abrir arquivo')
    que tenha ficado travado por engano. O Selenium não enxerga janelas
    do sistema operacional, então isso é feito no nível do teclado."""

    try:
        pyautogui.press("esc")
        time.sleep(0.3)
    except Exception:
        pass


def abrir_conversa(driver, telefone):
    print("=" * 60)
    print(f"Abrindo conversa: {telefone}")

    url = f"https://web.whatsapp.com/send?phone={telefone}"

    driver.get(url)

    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located(
            (By.XPATH, "//footer//div[@contenteditable='true']")
        )
    )

    log("Conversa aberta.")


def anexar_midia(driver, caminho_arquivo):
    """Abre o menu de anexo e seleciona um arquivo (imagem OU vídeo -
    o campo 'Fotos e vídeos' do WhatsApp aceita os dois pelo mesmo
    input). NÃO envia - só deixa a pré-visualização pronta. Quem envia
    é a enviar_midia(), em seguida."""

    caminho_original = Path(caminho_arquivo).resolve()
    if not caminho_original.is_file():
        raise FileNotFoundError(
            f"Arquivo de mídia não encontrado: {caminho_original}"
        )

    # O Chrome pode não conseguir acessar diretamente um caminho UNC de rede.
    # A cópia local também evita falhas quando o compartilhamento oscila durante o upload.
    pasta_temporaria = Path(tempfile.gettempdir()) / "WhatsAppBot" / "uploads"
    pasta_temporaria.mkdir(parents=True, exist_ok=True)
    caminho_upload = pasta_temporaria / caminho_original.name
    shutil.copy2(caminho_original, caminho_upload)

    log(f"Anexando mídia: {caminho_original}")
    log(f"Cópia local para upload: {caminho_upload}")

    fechar_dialogo_nativo()

    WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//span[@data-testid='plus-rounded']")
        )
    ).click()

    log("Menu aberto.")

    WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//span[contains(text(),'Fotos e vídeos')]")
        )
    ).click()

    log("Cliquei em Fotos e vídeos")

    inputs = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//input[@type='file']")
        )
    )

    log(f"Foram encontrados {len(inputs)} inputs.")

    input_file = None

    for i, inp in reversed(list(enumerate(inputs))):
        accept = inp.get_attribute("accept")
        print("-" * 32)
        print(f"Input: {i}")
        print(f"accept: {accept}")

        if accept and "video/mp4" in accept:
            input_file = inp
            break

    if input_file is None:
        raise Exception("Não encontrei o input de Fotos e Vídeos.")

    input_file.send_keys(str(caminho_upload))

    log("Arquivo selecionado.")

    # Vídeo demora mais pra gerar a pré-visualização/thumbnail do que
    # imagem, por isso o tempo maior aqui (60s em vez de 30s).
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[@role='button' and contains(@aria-label,'Enviar')]")
        )
    )

    log("Pré-visualização aberta.")


def enviar_midia(driver):
    """Confirma o envio da mídia (imagem ou vídeo) que já foi anexada,
    sem legenda. O texto vai depois, como mensagem separada, via
    escrever_texto() + enviar_texto()."""

    WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[@role='button' and contains(@aria-label,'Enviar')]")
        )
    ).click()

    log("Mídia enviada.")

    # Vídeo pode levar um tempinho a mais pra concluir o upload antes
    # da caixa de texto voltar a ficar disponível.
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located(
            (By.XPATH, "//footer//div[@contenteditable='true']")
        )
    )


def escrever_texto(driver, texto):
    """Cola o texto na caixa de mensagem da conversa (ainda não envia).
    Usa clipboard (Ctrl+V) em vez de send_keys puro, porque evita
    problemas com acentos e emojis no Windows."""

    caixa = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located(
            (By.XPATH, "//footer//div[@contenteditable='true']")
        )
    )

    pyperclip.copy(texto)

    caixa.click()
    time.sleep(0.3)

    caixa.send_keys(Keys.CONTROL, "v")
    time.sleep(0.5)

    log("Texto escrito na caixa de mensagem.")


def enviar_texto(driver):
    """Envia o texto que já foi escrito na caixa de mensagem
    (via escrever_texto)."""

    caixa = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located(
            (By.XPATH, "//footer//div[@contenteditable='true']")
        )
    )

    caixa.send_keys(Keys.ENTER)

    log("Texto enviado.")
