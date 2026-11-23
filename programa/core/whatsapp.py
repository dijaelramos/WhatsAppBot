from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchWindowException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urllib3.exceptions import HTTPError

from config import (
    CHROME_BINARY,
    PROFILE,
    SCREENSHOTS,
    TEMPO_ESPERA,
    USER_DATA,
)
from core import envio, seletores
from core.erros import NumeroInvalido, SessaoPerdida
from core.logger import log
from core.preparar_ambiente import finalizar_chrome, remover_lock

MAXIMO_CAPTURAS = 30

_SINAIS_SESSAO_ENCERRADA = (
    "chrome not reachable",
    "disconnected",
    "invalid session id",
    "no such session",
    "session deleted",
    "tab crashed",
    "target window already closed",
)


def iniciar_chrome():
    """Cria o Chrome com o perfil isolado usado pela automacao."""
    # O perfil isolado preserva o login do WhatsApp sem misturar o Chrome pessoal.
    options = Options()

    options.binary_location = CHROME_BINARY

    options.add_argument(fr"--user-data-dir={USER_DATA}")
    options.add_argument(fr"--profile-directory={PROFILE}")

    # NAO defina --remote-debugging-port manualmente: o chromedriver cuida
    # disso, e forcar essa flag impede a criacao do DevToolsActivePort.
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


def _capturar_tela(driver, prefixo):
    """Salva a tela para diagnostico, mantendo apenas as capturas mais recentes."""
    try:
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)
        destino = SCREENSHOTS / f"{prefixo}_{datetime.now():%Y%m%d_%H%M%S_%f}.png"
        driver.save_screenshot(str(destino))
        log(f"Captura de tela: {destino}")

        capturas = sorted(SCREENSHOTS.glob("*.png"), key=lambda p: p.stat().st_mtime)
        for antiga in capturas[:-MAXIMO_CAPTURAS]:
            antiga.unlink(missing_ok=True)
    except Exception as erro:
        log(f"AVISO: não consegui salvar a captura de tela: {erro}")


def abrir_whatsapp_web(driver):
    """Abre o WhatsApp Web e aguarda uma sessao autenticada."""
    print(f"Navegando para {seletores.URL_WHATSAPP} ...")
    driver.get(seletores.URL_WHATSAPP)

    print(f"URL atual: {driver.current_url}")
    print(f"Título da página: {driver.title}")

    # Primeiro aceita tanto a tela logada quanto a tela de QR Code.
    try:
        WebDriverWait(driver, TEMPO_ESPERA).until(
            EC.presence_of_element_located(seletores.TELA_INICIAL)
        )
        log("Algum elemento do WhatsApp Web apareceu (login ou QR).")

    except Exception as e:
        log(f"ERRO: nada apareceu em {TEMPO_ESPERA}s. Detalhe: {e}")
        _capturar_tela(driver, "erro_whatsapp")
        log(f"HTML da página (primeiros 500 chars): {driver.page_source[:500]}")
        raise

    # Depois exige a tela logada; se necessario, aguarda o usuario ler o QR Code.
    try:
        WebDriverWait(driver, TEMPO_ESPERA).until(
            EC.presence_of_element_located(seletores.LISTA_CONVERSAS)
        )
        log("WhatsApp Web carregado (sessão já logada).")

    except Exception:
        log(
            "Sessão ainda não logada neste perfil. "
            "Escaneie o QR Code na janela do Chrome e aguarde..."
        )
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located(seletores.LISTA_CONVERSAS)
        )
        log("Login concluído. WhatsApp Web carregado.")

    return driver


def sessao_encerrada(erro):
    """Indica se o erro significa que o navegador deixou de responder."""
    if isinstance(
        erro,
        (
            InvalidSessionIdException,
            NoSuchWindowException,
            ConnectionError,
            HTTPError,
        ),
    ):
        return True
    if isinstance(erro, WebDriverException):
        mensagem = str(erro).lower()
        return any(sinal in mensagem for sinal in _SINAIS_SESSAO_ENCERRADA)
    return False


class CanalWhatsApp:
    """Sessao do WhatsApp Web usada pela campanha."""

    def __init__(self):
        self.driver = None

    def iniciar(self):
        self.driver = iniciar_chrome()
        abrir_whatsapp_web(self.driver)

    def encerrar(self):
        """Fecha o navegador, tolerando uma sessao que ja morreu."""
        if self.driver is None:
            return
        try:
            self.driver.quit()
        except Exception as erro:
            log(f"AVISO: o navegador não fechou normalmente: {erro}")
        self.driver = None

    def reiniciar(self):
        self.encerrar()
        finalizar_chrome()
        remover_lock()
        self.iniciar()

    def _executar(self, acao, *argumentos):
        """Traduz falhas do navegador para os erros tratados pela campanha."""
        try:
            return acao(self.driver, *argumentos)
        except (NumeroInvalido, SessaoPerdida):
            raise
        except Exception as erro:
            if sessao_encerrada(erro):
                raise SessaoPerdida(str(erro)) from erro
            _capturar_tela(self.driver, "falha_envio")
            raise

    def abrir_conversa(self, telefone):
        self._executar(envio.abrir_conversa, telefone)

    def anexar_midia(self, caminho_upload):
        self._executar(envio.anexar_midia, caminho_upload)

    def enviar_midia(self):
        self._executar(envio.enviar_midia)

    def enviar_texto(self, texto):
        return self._executar(envio.enviar_texto, texto)
