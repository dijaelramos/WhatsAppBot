import time
import shutil
import tempfile
from uuid import uuid4

import pyautogui

from pathlib import Path
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
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


def clicar_com_retentativa(driver, locator, tentativas=5):
    """Reencontra e clica no elemento caso o WhatsApp reconstrua o menu."""
    for tentativa in range(tentativas):
        try:
            WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable(locator)
            ).click()
            return
        except StaleElementReferenceException:
            if tentativa == tentativas - 1:
                raise
            time.sleep(0.3)


def clicar_qualquer_anexo(driver):
    """Clica no botão de anexar usando seletores compatíveis com versões do WhatsApp Web."""
    seletores = [
        (By.XPATH, "//button[@aria-label='Anexar']"),
        (By.XPATH, "//div[@role='button' and @aria-label='Anexar']"),
        (By.XPATH, "//span[@data-testid='clip']"),
        (By.XPATH, "//span[@data-testid='plus-rounded']"),
        (By.XPATH, "//div[@data-testid='attach']"),
        (By.XPATH, "//div[@aria-label='Anexar']"),
    ]

    ultimo_erro = None
    for selector in seletores:
        try:
            elemento = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable(selector)
            )
            elemento.click()
            return True
        except Exception as erro:
            ultimo_erro = erro

    if ultimo_erro is not None:
        raise ultimo_erro
    return False


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
    caminho_upload = pasta_temporaria / (
        f"{uuid4().hex}_{caminho_original.name}"
    )
    shutil.copy2(caminho_original, caminho_upload)

    log(f"Anexando mídia: {caminho_original}")
    log(f"Cópia local para upload: {caminho_upload}")

    fechar_dialogo_nativo()

    clicar_qualquer_anexo(driver)

    log("Menu aberto.")

    seletores_fotos = [
        (By.XPATH, "//div[contains(@aria-label,'Fotos e vídeos')]"),
        (By.XPATH, "//span[contains(text(),'Fotos e vídeos')]"),
        (By.XPATH, "//div[contains(@aria-label,'Photos and videos')]"),
        (By.XPATH, "//div[contains(@aria-label,'Galeria')]"),
    ]

    ultimo_erro = None
    for selector in seletores_fotos:
        try:
            elemento = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable(selector)
            )
            elemento.click()
            log("Cliquei em Fotos e vídeos")
            break
        except Exception as erro:
            ultimo_erro = erro
    else:
        if ultimo_erro is not None:
            raise ultimo_erro
        raise TimeoutError("Não encontrei o item de mídia do WhatsApp Web.")

    seletor_inputs = (By.XPATH, "//input[@type='file']")

    def selecionar_input(detalhe):
        inputs = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(seletor_inputs)
        )
        log(f"Foram encontrados {len(inputs)} inputs.")

        caminho_extensao = caminho_upload.suffix.lower()
        candidatos_midia = []

        for i, inp in enumerate(inputs):
            accept = inp.get_attribute("accept") or ""
            print("-" * 32)
            print(f"Input: {i}")
            print(f"accept: {accept}")

            tipos_aceitos = {
                tipo.strip().lower()
                for tipo in accept.split(",")
                if tipo.strip()
            }
            aceita_imagem = "image/*" in tipos_aceitos
            aceita_video = "video/*" in tipos_aceitos or "video/mp4" in tipos_aceitos

            if aceita_imagem and aceita_video:
                candidatos_midia.append(inp)

        if len(candidatos_midia) == 1:
            candidatos_midia[0].send_keys(str(caminho_upload))
            return

        if len(candidatos_midia) > 1:
            candidatos_midia[-1].send_keys(str(caminho_upload))
            return

        raise Exception(
            "Não encontrei o input exclusivo de Fotos e Vídeos "
            f"({detalhe}); extensão selecionada: {caminho_extensao}."
        )

    for tentativa in range(5):
        try:
            selecionar_input(f"tentativa {tentativa + 1}")
            break
        except StaleElementReferenceException:
            if tentativa == 4:
                raise
            time.sleep(0.3)
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
    """Digita o texto na caixa de mensagem sem enviá-lo."""

    caixa = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located(
            (By.XPATH, "//footer//div[@contenteditable='true']")
        )
    )

    caixa.click()
    time.sleep(0.3)

    linhas = texto.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for indice, linha in enumerate(linhas):
        if linha:
            caixa.send_keys(linha)
        if indice < len(linhas) - 1:
            caixa.send_keys(Keys.SHIFT, Keys.ENTER)

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
