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

# O runtime pertence ao backend e nao deve misturar-se com dados editaveis.
RUNTIME = PROGRAMA_DIR / "runtime"

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
# (veja scripts/copiar_perfil.py). Isso evita qualquer conflito de
# lock com janelas normais do Chrome abertas em outros perfis.
USER_DATA = str(RUNTIME / "chrome_automacao")

PROFILE = "Default"

# ==========================================
# TEMPOS
# ==========================================

TEMPO_ESPERA = 30

TEMPO_ENTRE_MENSAGENS_MIN = 10

TEMPO_ENTRE_MENSAGENS_MAX = 20

MENSAGENS_POR_LOTE = 20

PAUSA_ENTRE_LOTES_SEGUNDOS = 10 * 60

MAX_TENTATIVAS = 3  # tentativas de envio
