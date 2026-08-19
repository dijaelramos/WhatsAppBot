from pathlib import Path

# ==========================================
# PASTA RAIZ
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

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

RUNTIME = BASE_DIR / "runtime"

LOGS = RUNTIME / "logs"

SCREENSHOTS = RUNTIME / "screenshots"

ARQUIVO_ESTADO = RUNTIME / "estado.json"

# ==========================================
# CHROME
# ==========================================

CHROME_BINARY = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

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

MAX_TENTATIVAS = 3  # tentativas de envio
