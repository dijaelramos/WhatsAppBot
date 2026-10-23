from pathlib import Path
import sys

# ==========================================
# PASTA RAIZ
# ==========================================

# Durante o desenvolvimento, o backend pode estar na raiz atual ou dentro
# de programa/. Os arquivos alteraveis ficam sempre na pasta dados/ vizinha.
if getattr(sys, "frozen", False):
	PROGRAMA_DIR = Path(sys.executable).resolve().parent
else:
	PROGRAMA_DIR = Path(__file__).resolve().parent

if (PROGRAMA_DIR.parent / "dados").is_dir():
	BASE_DIR = PROGRAMA_DIR.parent
else:
	BASE_DIR = PROGRAMA_DIR

# ==========================================
# DADOS (entrada: planilha, mensagem, imagem)
# ==========================================

DADOS = BASE_DIR / "dados"

ARQUIVO_EXCEL = DADOS / "contatos.xlsx"

ARQUIVO_MENSAGEM = DADOS / "mensagem.txt"

ARQUIVO_IMAGEM = DADOS / "imagem.png"

ARQUIVO_VIDEO = DADOS / "video.mp4"

# ==========================================
# RUNTIME (tudo que é gerado pela execução)
# ==========================================

# Dados de execucao ficam na pasta-base, ao lado de dados/.
RUNTIME = BASE_DIR / "runtime"

LOGS = RUNTIME / "logs"

SCREENSHOTS = RUNTIME / "screenshots"

ARQUIVO_ESTADO = RUNTIME / "estado.json"

# ==========================================
# CHROME
# ==========================================

# O Chrome pode estar instalado em locais diferentes em cada computador.
_CHROME_CANDIDATOS = [
	Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
	Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
	Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
]
CHROME_BINARY = next(
	(str(caminho) for caminho in _CHROME_CANDIDATOS if caminho.exists()),
	str(_CHROME_CANDIDATOS[0]),
)

# IMPORTANTE: essa pasta é totalmente isolada do Chrome que você usa
# no dia a dia. Foi criada copiando o Profile 9 uma única vez
# (veja scripts/copiar_perfil.py). O perfil fica no disco local porque o
# Chrome pode falhar ao iniciar quando o user-data-dir está em uma rede.
LEGACY_USER_DATA = PROGRAMA_DIR / "runtime" / "chrome_automacao"
USER_DATA = str(
	Path.home() / "AppData" / "Local" / "WhatsAppBot" / "chrome_automacao"
)

PROFILE = "Default"

# ==========================================
# TEMPOS
# ==========================================

TEMPO_ESPERA = 60 # Tempo de espera para o WhatsApp Web carregar (em segundos).

TEMPO_ENTRE_MENSAGENS_MIN = 600 # Intervalo mínimo fixo em segundos entre mensagens.

TEMPO_ENTRE_MENSAGENS_MAX = 600 # Intervalo máximo fixo em segundos entre mensagens.

MENSAGENS_POR_LOTE = 50 # Envia mensagens em lotes, depois pausa.

PAUSA_ENTRE_LOTES_SEGUNDOS = 8 * 60 * 60 # Pausa de oito horas entre lotes.

HORA_INICIO_PAUSA_NOTURNA = 0
HORA_FIM_PAUSA_NOTURNA = 6
