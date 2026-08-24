import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from core.logger import log

from config import (
    CHROME_BINARY,
    USER_DATA,
    PROFILE,
    TEMPO_ESPERA,
    SCREENSHOTS,
)


def iniciar_chrome():
    """Cria o Chrome com o perfil isolado usado pela automacao."""
    # O perfil isolado preserva o login do WhatsApp sem misturar o Chrome pessoal.
    options = Options()

    options.binary_location = CHROME_BINARY

    options.add_argument(fr"--user-data-dir={USER_DATA}")
    options.add_argument(fr"--profile-directory={PROFILE}")

    # Reduz instabilidade em máquinas Windows / perfis "sujos"
    # (NÃO defina --remote-debugging-port manualmente: o chromedriver
    # já cuida disso sozinho, e forçar essa flag causa conflito que
    # impede o arquivo DevToolsActivePort de ser criado corretamente)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--start-maximized")

    options.add_experimental_option(
        "excludeSwitches", ["enable-automation"]
    )

    try:
        driver = webdriver.Chrome(options=options)
    except Exception as erro:
        log("ERRO ao iniciar o Chrome pelo Selenium.")
        log(f"Executavel do Chrome: {CHROME_BINARY}")
        log(f"Perfil da automacao: {Path(USER_DATA) / PROFILE}")
        log(
            "O Chrome fechou antes de criar a sessao. "
            "Verifique se o perfil nao esta aberto em outra instancia."
        )
        raise erro

    driver.maximize_window()

    return driver


def abrir_whatsapp_web(driver):
    """Abre o WhatsApp Web e aguarda uma sessao autenticada."""
    print("Navegando para https://web.whatsapp.com ...")
    driver.get("https://web.whatsapp.com")

    print(f"URL atual: {driver.current_url}")
    print(f"Título da página: {driver.title}")

    # Primeiro aceita tanto a tela logada quanto a tela de QR Code.
    seletor = "div[id='pane-side'], canvas[aria-label], div[data-testid='qrcode'], div[data-ref]"

    try:
        WebDriverWait(driver, TEMPO_ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
        )
        log("Algum elemento do WhatsApp Web apareceu (login ou QR).")

    except Exception as e:
        log(f"ERRO: nada apareceu em {TEMPO_ESPERA}s. Detalhe: {e}")
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)
        driver.save_screenshot(str(SCREENSHOTS / "erro_whatsapp.png"))
        log(f"Screenshot salvo em {SCREENSHOTS / 'erro_whatsapp.png'}")
        log(f"HTML da página (primeiros 500 chars): {driver.page_source[:500]}")
        raise

    # Depois exige a tela logada; se necessario, aguarda o usuario ler o QR Code.
    try:
        WebDriverWait(driver, TEMPO_ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[id='pane-side']"))
        )
        log("WhatsApp Web carregado (sessão já logada).")

    except Exception:
        log(
            "Sessão ainda não logada neste perfil. "
            "Escaneie o QR Code na janela do Chrome e aguarde..."
        )
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[id='pane-side']"))
        )
        log("Login concluído. WhatsApp Web carregado.")

    return driver
