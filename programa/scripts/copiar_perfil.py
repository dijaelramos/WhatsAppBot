import shutil
from pathlib import Path

ORIGEM = (
    Path.home() / "AppData" / "Local" / "Google" / "Chrome"
    / "User Data" / "Profile 9"
)

# Perfil isolado em disco local: o Chrome pode falhar em user-data-dir de rede.
DESTINO_USER_DATA = (
    Path.home() / "AppData" / "Local" / "WhatsAppBot" / "chrome_automacao"
)
DESTINO_PROFILE = DESTINO_USER_DATA / "Default"


def copiar():
    """Copia uma vez o perfil do Chrome para uso exclusivo do bot."""
    # Evita apagar uma sessao que ja pode conter o login do WhatsApp.
    if DESTINO_PROFILE.exists():
        print(f"Já existe uma cópia em {DESTINO_PROFILE}. Nada a fazer.")
        print("Se quiser refazer do zero, apague essa pasta manualmente e rode de novo.")
        return

    print(f"Copiando de:\n  {ORIGEM}\npara:\n  {DESTINO_PROFILE}")
    print("Isso pode levar alguns minutos dependendo do tamanho do perfil...")

    DESTINO_USER_DATA.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        ORIGEM,
        DESTINO_PROFILE,
        ignore=shutil.ignore_patterns(
            "Singleton*",
        ),
    )

    print("Cópia concluída.")
    print(f"\nAtualize o config.py:")
    print(f'USER_DATA = r"{DESTINO_USER_DATA}"')
    print(f'PROFILE = "Default"')


if __name__ == "__main__":
    copiar()
