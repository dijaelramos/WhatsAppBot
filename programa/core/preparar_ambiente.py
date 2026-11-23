import os
import shutil
import subprocess
import importlib.util
import sys
from pathlib import Path

from config import LEGACY_USER_DATA, USER_DATA, PROFILE

ARQUIVO_REQUISITOS = Path(__file__).resolve().parents[2] / "requirements.txt"

# Encerra somente os processos do Chrome que usam o perfil da automacao e
# so termina quando eles sumirem: o perfil precisa estar livre para reabrir.
_COMANDO_FECHAR_CHROME_DO_BOT = (
    "$limite = (Get-Date).AddSeconds(30); "
    "do { "
    "$processos = @(Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
    "Where-Object { $_.CommandLine -and "
    "$_.CommandLine.Contains($env:WHATSAPPBOT_PERFIL) }); "
    "$processos | ForEach-Object { Stop-Process -Id $_.ProcessId -Force "
    "-ErrorAction SilentlyContinue }; "
    "if ($processos.Count) { Start-Sleep -Milliseconds 500 } "
    "} while ($processos.Count -and (Get-Date) -lt $limite)"
)


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
        # O requirements.txt fixa as versoes testadas com o bot.
        resultado = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(ARQUIVO_REQUISITOS)]
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
    """Encerra o Chrome da automacao, sem tocar no Chrome pessoal do usuario."""
    print("Fechando o Chrome da automação...")

    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            _COMANDO_FECHAR_CHROME_DO_BOT,
        ],
        env={**os.environ, "WHATSAPPBOT_PERFIL": str(USER_DATA)},
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


def migrar_perfil_chrome():
    """Copia o perfil antigo da pasta do programa para o disco local."""
    origem = Path(LEGACY_USER_DATA)
    destino = Path(USER_DATA)
    if destino.exists() or not origem.is_dir():
        return

    print(f"Migrando o perfil do Chrome para uma pasta local: {destino}")
    shutil.copytree(
        origem,
        destino,
        ignore=shutil.ignore_patterns(
            "Singleton*",
            "lockfile",
            "LOCK",
            "LOCK.*",
            "lock",
            "lock.*",
            "*Cache*",
            "Cache",
            "Code Cache",
            "GPUCache",
            "GrShaderCache",
            "ShaderCache",
            "component_crx_cache",
            "extensions_crx_cache",
            "Crashpad",
        ),
    )
    print("Perfil do Chrome migrado. A cópia original foi mantida.")


def preparar():
    """Executa a preparacao completa antes de abrir o navegador."""
    finalizar_chrome()

    migrar_perfil_chrome()

    remover_lock()

    print("Ambiente preparado.")


if __name__ == "__main__":
    preparar()
