import shutil
import tempfile
import time
import unicodedata
from pathlib import Path
from uuid import uuid4

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core import seletores
from core.erros import NumeroInvalido, SessaoPerdida
from core.logger import log

TEMPO_ABRIR_CONVERSA = 60
TEMPO_MENU_ANEXO = 15
TEMPO_INPUT_SEM_CLIQUE = 2
TEMPO_INPUT_DE_MIDIA = 30
TEMPO_PREVIA_MIDIA = 60
TEMPO_CAIXA_ESVAZIAR = 10
TEMPO_CONFIRMAR_TEXTO = 30
TEMPO_CONFIRMAR_MIDIA = 60


def _pasta_uploads():
    return Path(tempfile.gettempdir()) / "WhatsAppBot" / "uploads"


def preparar_copia_local(caminho_arquivo):
    """Copia a midia para o disco local uma unica vez por campanha.

    O Chrome pode nao acessar um caminho de rede, e a copia local evita falhas
    quando o compartilhamento oscila durante o upload.
    """
    original = Path(caminho_arquivo).resolve()
    limpar_uploads()
    pasta = _pasta_uploads()
    pasta.mkdir(parents=True, exist_ok=True)
    copia = pasta / f"{uuid4().hex}_{original.name}"
    shutil.copy2(original, copia)
    log(f"Mídia: {original}")
    log(f"Cópia local para upload: {copia}")
    return copia


def limpar_uploads():
    """Remove copias locais de midia deixadas por esta ou por execucoes antigas."""
    shutil.rmtree(_pasta_uploads(), ignore_errors=True)


def _clicar(driver, opcoes, tempo_maximo):
    """Clica na primeira opcao visivel, tolerando o WhatsApp reconstruir a tela."""
    prazo = time.monotonic() + tempo_maximo
    while True:
        for seletor in opcoes:
            try:
                for elemento in driver.find_elements(*seletor):
                    if elemento.is_displayed() and elemento.is_enabled():
                        elemento.click()
                        return
            except (
                StaleElementReferenceException,
                ElementClickInterceptedException,
                ElementNotInteractableException,
            ):
                pass

        if time.monotonic() >= prazo:
            raise TimeoutException(f"Elemento não encontrado: {opcoes[0][1]}")
        time.sleep(0.25)


def _caixa_mensagem(driver, tempo_maximo=30):
    return WebDriverWait(driver, tempo_maximo).until(
        EC.presence_of_element_located(seletores.CAIXA_MENSAGEM)
    )


def aviso_de_numero_inexistente(texto):
    """Indica se o aviso do WhatsApp diz que o numero nao existe.

    Exige o assunto e o problema na mesma frase: um falso positivo tiraria
    da planilha um contato que existe.
    """
    sem_acentos = "".join(
        letra
        for letra in unicodedata.normalize("NFD", texto.lower())
        if not unicodedata.combining(letra)
    ).replace("’", "'")
    return any(
        assunto in sem_acentos for assunto in seletores.AVISO_ASSUNTO
    ) and any(
        problema in sem_acentos for problema in seletores.AVISO_PROBLEMA
    )


def _avisos_na_tela(driver):
    """Retorna o texto dos dialogos abertos, ignorando os que sumiram."""
    avisos = []
    for dialogo in driver.find_elements(*seletores.DIALOGOS):
        try:
            texto = " ".join(dialogo.text.split())
        except StaleElementReferenceException:
            continue
        if texto:
            avisos.append(texto)
    return avisos


def abrir_conversa(driver, telefone):
    """Abre a conversa e distingue numero inexistente de sessao encerrada."""
    log(f"Abrindo conversa: {telefone}")
    driver.get(seletores.URL_CONVERSA.format(telefone=telefone))

    def situacao(navegador):
        if navegador.find_elements(*seletores.CAIXA_MENSAGEM):
            return ("aberta", "")
        for aviso in _avisos_na_tela(navegador):
            if aviso_de_numero_inexistente(aviso):
                return ("inexistente", aviso)
        if navegador.find_elements(*seletores.TELA_LOGIN):
            return ("sem_login", "")
        return False

    try:
        resultado, aviso = WebDriverWait(
            driver,
            TEMPO_ABRIR_CONVERSA,
            poll_frequency=0.5,
            ignored_exceptions=(StaleElementReferenceException,),
        ).until(situacao)
    except TimeoutException:
        # Sem aviso reconhecido nao ha prova de que o numero nao existe.
        raise TimeoutException(
            f"A conversa não abriu em {TEMPO_ABRIR_CONVERSA}s. "
            f"Avisos na tela: {_avisos_na_tela(driver)}"
        ) from None

    if resultado == "inexistente":
        raise NumeroInvalido(f"{telefone}: {aviso}")
    if resultado == "sem_login":
        raise SessaoPerdida("O WhatsApp Web saiu da conta (tela de QR Code).")

    log("Conversa aberta.")


def _aceita_foto_e_video(accept):
    tipos = [tipo.strip().lower() for tipo in accept.split(",")]
    return (
        any(tipo.startswith("image/") for tipo in tipos)
        and any(tipo.startswith("video/") for tipo in tipos)
    )


def _aguardar_input_de_midia(driver, tempo_maximo):
    """Espera o campo de fotos e videos existir, e nao um campo qualquer.

    Retorna (campo ou None, valores de accept vistos), para diagnostico.
    """
    vistos = []

    def procurar(navegador):
        nonlocal vistos
        campos = navegador.find_elements(*seletores.INPUT_ARQUIVO)
        vistos = [campo.get_attribute("accept") or "" for campo in campos]
        candidatos = [
            campo
            for campo, accept in zip(campos, vistos)
            if _aceita_foto_e_video(accept)
        ]
        return candidatos[-1] if candidatos else False

    try:
        campo = WebDriverWait(
            driver,
            tempo_maximo,
            poll_frequency=0.25,
            ignored_exceptions=(StaleElementReferenceException,),
        ).until(procurar)
        return campo, vistos
    except TimeoutException:
        return None, vistos


def _impedir_janela_de_arquivos(driver):
    """Evita que o clique em 'Fotos e videos' abra o seletor do Windows."""
    try:
        driver.execute_cdp_cmd(
            "Page.setInterceptFileChooserDialog",
            {"enabled": True},
        )
    except Exception as erro:
        log(f"AVISO: não consegui bloquear a janela de arquivos: {erro}")


def anexar_midia(driver, caminho_upload):
    """Seleciona a imagem ou o video e deixa a pre-visualizacao aberta."""
    _clicar(driver, seletores.BOTAO_ANEXAR, TEMPO_MENU_ANEXO)
    log("Menu de anexo aberto.")
    _impedir_janela_de_arquivos(driver)

    for tentativa in range(5):
        campo, vistos = _aguardar_input_de_midia(driver, TEMPO_INPUT_SEM_CLIQUE)
        if campo is None:
            _clicar(driver, seletores.ITEM_FOTOS_VIDEOS, TEMPO_MENU_ANEXO)
            log("Cliquei em Fotos e vídeos.")
            campo, vistos = _aguardar_input_de_midia(
                driver,
                TEMPO_INPUT_DE_MIDIA,
            )

        if campo is None:
            raise TimeoutException(
                "Campo de Fotos e Vídeos não apareceu em "
                f"{TEMPO_INPUT_DE_MIDIA}s. Campos encontrados (accept): {vistos}"
            )

        try:
            campo.send_keys(str(caminho_upload))
            break
        except StaleElementReferenceException:
            if tentativa == 4:
                raise
            time.sleep(0.3)

    log("Arquivo selecionado.")

    # Video demora mais para gerar a pre-visualizacao do que imagem.
    WebDriverWait(driver, TEMPO_PREVIA_MIDIA, poll_frequency=0.25).until(
        lambda navegador: any(
            navegador.find_elements(*seletor)
            for seletor in seletores.BOTAO_ENVIAR_MIDIA
        )
    )
    log("Pré-visualização aberta.")


def _ultima_enviada(driver):
    return driver.execute_script(seletores.SCRIPT_ULTIMA_ENVIADA)


def _aguardar_confirmacao(driver, anterior, tempo_maximo):
    """Espera uma nova mensagem enviada sem o icone de relogio.

    Retorna False em vez de falhar: a mensagem ja pode ter saido, e tratar
    a falta de confirmacao como erro faria o contato receber em dobro.
    """
    def confirmada(navegador):
        atual = _ultima_enviada(navegador)
        return bool(atual) and not atual["pendente"] and (
            not anterior
            or (atual["id"], atual["total"])
            != (anterior["id"], anterior["total"])
        )

    try:
        WebDriverWait(driver, tempo_maximo, poll_frequency=0.5).until(confirmada)
        return True
    except Exception:
        return False


def enviar_midia(driver):
    """Confirma a midia ja anexada, sem legenda; o texto vai depois."""
    anterior = _ultima_enviada(driver)
    _clicar(driver, seletores.BOTAO_ENVIAR_MIDIA, TEMPO_PREVIA_MIDIA)
    log("Mídia enviada.")

    if not _aguardar_confirmacao(driver, anterior, TEMPO_CONFIRMAR_MIDIA):
        log("AVISO: não vi a confirmação da mídia na conversa.")


def _texto_restante_na_caixa(driver, tempo_maximo):
    """Retorna o texto que continuou na caixa; vazio se nao ha o que apontar."""
    restante = ""
    prazo = time.monotonic() + tempo_maximo
    try:
        while time.monotonic() < prazo:
            caixas = driver.find_elements(*seletores.CAIXA_MENSAGEM)
            if caixas:
                restante = driver.execute_script(
                    "return arguments[0].textContent",
                    caixas[0],
                ) or ""
                if not restante.strip():
                    return ""
            time.sleep(0.25)
    except Exception:
        return ""
    return restante.strip()


def escrever_texto(driver, texto):
    """Digita o texto sem envia-lo, descartando rascunho de tentativa anterior."""
    caixa = _caixa_mensagem(driver)
    caixa.click()
    time.sleep(0.3)
    caixa.send_keys(Keys.CONTROL, "a")
    caixa.send_keys(Keys.DELETE)

    linhas = texto.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for indice, linha in enumerate(linhas):
        if linha:
            caixa.send_keys(linha)
        if indice < len(linhas) - 1:
            caixa.send_keys(Keys.SHIFT, Keys.ENTER)

    log("Texto escrito na caixa de mensagem.")


def enviar_texto(driver, texto):
    """Escreve e envia o texto; retorna True se a conversa confirmou o envio."""
    escrever_texto(driver, texto)
    anterior = _ultima_enviada(driver)
    _caixa_mensagem(driver).send_keys(Keys.ENTER)

    # So e erro certo se o texto continuou na caixa: nesse caso nada foi enviado.
    if _texto_restante_na_caixa(driver, TEMPO_CAIXA_ESVAZIAR):
        raise RuntimeError("O texto continuou na caixa depois do ENTER.")

    confirmado = _aguardar_confirmacao(driver, anterior, TEMPO_CONFIRMAR_TEXTO)
    if confirmado:
        log("Texto enviado e confirmado na conversa.")
    else:
        log("AVISO: texto saiu da caixa, mas não vi a confirmação na conversa.")
    return confirmado
