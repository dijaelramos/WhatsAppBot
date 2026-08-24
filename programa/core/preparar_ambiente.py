import os
import shutil
import subprocess
import importlib.util
import sys
from pathlib import Path

from config import USER_DATA, PROFILE


def verificar_dependencias(chrome_binary):
    """Verifica o ambiente antes de carregar os modulos externos do bot."""
    print("Verificando o ambiente necessario para executar o WhatsAppBot...")

    if getattr(sys, "frozen", False):
        print("Python e bibliotecas: incorporados ao executavel.")
        dependencias_faltantes = []
    else:
        dependencias = {
            "pandas": "pandas",
            "openpyxl": "openpyxl",
            "selenium": "selenium",
            "pyautogui": "pyautogui",
            "pyperclip": "pyperclip",
        }
        dependencias_faltantes = [
            pacote
            for modulo, pacote in dependencias.items()
            if importlib.util.find_spec(modulo) is None
        ]

    if dependencias_faltantes:
        print("Os seguintes programas/bibliotecas nao estao instalados:")
        for pacote in dependencias_faltantes:
            print(f"- {pacote}")
        print("Eles sao necessarios para executar o WhatsAppBot.")
        resposta = input("Deseja instalar automaticamente? (SIM/NAO): ").strip().upper()

        if resposta not in {"SIM", "S"}:
            print("Instalacao cancelada. O programa sera encerrado.")
            return False

        print("Iniciando a instalacao das dependencias...")
        resultado = subprocess.run(
            [sys.executable, "-m", "pip", "install", *dependencias_faltantes]
        )
        if resultado.returncode != 0:
            print("A instalacao falhou. Corrija o ambiente e tente novamente.")
            return False

        print("Dependencias instaladas com sucesso.")

    if not Path(chrome_binary).exists():
        print(f"Chrome nao encontrado em: {chrome_binary}")
        print("Instale o Google Chrome antes de executar o WhatsAppBot.")
        return False

    print("Ambiente verificado com sucesso.")
    return True


def finalizar_chrome():
    """Encerra todas as instancias do Chrome no Windows."""
    print("Fechando Chrome...")

    subprocess.run(
        ["taskkill", "/F", "/IM", "chrome.exe", "/T"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def remover_lock():
    """Remove arquivos que impedem a abertura de um perfil ja utilizado."""
    print("Removendo arquivos de lock...")

    user_data = Path(USER_DATA)
    arquivos = [
        user_data / "SingletonLock",
        user_data / "SingletonCookie",
        user_data / "SingletonSocket",
        user_data / PROFILE / "SingletonLock",
        user_data / PROFILE / "SingletonCookie",
        user_data / PROFILE / "SingletonSocket",
        user_data / "DevToolsActivePort",
    ]

    for arquivo in arquivos:

        try:

            if arquivo.exists():
                arquivo.unlink()
                print(f"Removido: {arquivo.name}")

        except Exception as e:

            print(f"Não foi possível remover {arquivo.name}: {e}")


def limpar_cache_selenium():
    """Remove o cache local do Selenium para forcar uma descoberta limpa."""
    print("Limpando cache do Selenium...")

    cache = Path.home() / ".cache" / "selenium"

    if cache.exists():

        try:

            shutil.rmtree(cache)
            print("Cache removido.")

        except Exception as e:

            print(e)


def atualizar_selenium():
    """Atualiza o pacote Selenium usado pelo bot."""
    # No executavel, o Selenium ja esta incorporado e nao existe pip externo.
    if getattr(sys, "frozen", False):
        print("Selenium incorporado ao executavel; nenhuma atualizacao necessaria.")
        return

    print("Atualizando Selenium...")

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-U", "selenium"]
    )


def preparar():
    """Executa a preparacao completa antes de abrir o navegador."""
    finalizar_chrome()

    remover_lock()

    limpar_cache_selenium()

    atualizar_selenium()

    print("Ambiente preparado.")


if __name__ == "__main__":
    preparar()
