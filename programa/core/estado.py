import json
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime

from config import ARQUIVO_ESTADO
from core.erros import ErroEstado
from core.logger import log

VERSAO_ESTADO = 2
TENTATIVAS_GRAVACAO = 5


@dataclass
class Progresso:
    """Andamento da campanha, identificado pelo telefone de cada contato."""

    enviados: set = field(default_factory=set)
    falhos: set = field(default_factory=set)
    invalidos: set = field(default_factory=set)
    midia_enviada: set = field(default_factory=set)
    nao_confirmados: set = field(default_factory=set)
    erros: int = 0
    ultimo_indice: int = -1
    nome: str = ""
    telefone: str = ""
    data_hora: str = ""
    retomar_apos: str | None = None
    planilha_sha256: str = ""


def _caminho_backup():
    return ARQUIVO_ESTADO.with_name(ARQUIVO_ESTADO.name + ".bak")


def _serializar(progresso):
    return {
        "versao": VERSAO_ESTADO,
        "planilha_sha256": progresso.planilha_sha256,
        "ultimo_indice": progresso.ultimo_indice,
        "nome": progresso.nome,
        "telefone": progresso.telefone,
        "erros": progresso.erros,
        "retomar_apos": progresso.retomar_apos,
        "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "enviados": sorted(progresso.enviados),
        "falhos": sorted(progresso.falhos),
        "invalidos": sorted(progresso.invalidos),
        "midia_enviada": sorted(progresso.midia_enviada),
        "nao_confirmados": sorted(progresso.nao_confirmados),
    }


def salvar_progresso(progresso):
    """Grava o progresso de forma atomica, mantendo a versao anterior em .bak."""
    temporario = ARQUIVO_ESTADO.with_name(ARQUIVO_ESTADO.name + ".tmp")
    ultimo_erro = None

    # Pastas de rede e antivirus podem bloquear o arquivo por alguns instantes.
    for tentativa in range(TENTATIVAS_GRAVACAO):
        try:
            ARQUIVO_ESTADO.parent.mkdir(parents=True, exist_ok=True)
            with open(temporario, "w", encoding="utf-8") as arquivo:
                json.dump(
                    _serializar(progresso),
                    arquivo,
                    indent=4,
                    ensure_ascii=False,
                )
                arquivo.flush()
                os.fsync(arquivo.fileno())
            if ARQUIVO_ESTADO.exists():
                shutil.copy2(ARQUIVO_ESTADO, _caminho_backup())
            os.replace(temporario, ARQUIVO_ESTADO)
            return
        except OSError as erro:
            ultimo_erro = erro
            if tentativa < TENTATIVAS_GRAVACAO - 1:
                time.sleep(1)

    raise ErroEstado(
        f"Não consegui salvar o progresso em {ARQUIVO_ESTADO}: {ultimo_erro}"
    )


def _ler_json(caminho):
    with open(caminho, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    if not isinstance(dados, dict):
        raise ValueError("o conteúdo não é um objeto JSON")
    return dados


def carregar_estado():
    """Retorna o JSON salvo ou None; nunca descarta um historico ilegivel."""
    if not ARQUIVO_ESTADO.exists():
        return None

    try:
        return _ler_json(ARQUIVO_ESTADO)
    except OSError as erro:
        raise ErroEstado(
            f"Não consegui ler {ARQUIVO_ESTADO}: {erro}. "
            "Verifique a pasta e tente novamente."
        ) from erro
    except ValueError as erro:
        log(f"estado.json está corrompido: {erro}")

    backup = _caminho_backup()
    try:
        dados = _ler_json(backup)
    except (OSError, ValueError) as erro:
        raise ErroEstado(
            f"{ARQUIVO_ESTADO} está corrompido e o backup não pôde ser usado "
            f"({erro}). Nenhum arquivo foi apagado. Mova o estado.json para "
            "outra pasta somente se quiser começar uma campanha sem histórico."
        ) from erro

    log(f"Progresso recuperado do backup: {backup}")
    return dados


def _converter_formato_antigo(dados, telefones_por_indice):
    """Traduz os indices do formato antigo para telefones da planilha atual."""
    def telefones(chave):
        return {
            telefones_por_indice[indice]
            for indice in dados.get(chave, [])
            if 0 <= indice < len(telefones_por_indice)
            and telefones_por_indice[indice]
        }

    enviados = telefones("enviados_indices")
    return Progresso(
        enviados=enviados,
        falhos=telefones("falhos_indices") - enviados,
        erros=dados.get("erros", 0),
        ultimo_indice=dados.get("ultimo_indice", -1),
        nome=dados.get("nome", ""),
        telefone=dados.get("telefone", ""),
        data_hora=dados.get("data_hora", ""),
    )


def progresso_de_dados(dados, telefones_por_indice):
    """Cria o Progresso a partir do JSON, convertendo o formato antigo."""
    if dados.get("versao") != VERSAO_ESTADO:
        copia = ARQUIVO_ESTADO.with_name(
            f"estado_formato_antigo_{datetime.now():%Y%m%d_%H%M%S}.json"
        )
        try:
            shutil.copy2(ARQUIVO_ESTADO, copia)
            log(f"Cópia do progresso no formato antigo: {copia}")
        except OSError as erro:
            log(f"AVISO: não consegui copiar o estado antigo: {erro}")
        return _converter_formato_antigo(dados, telefones_por_indice)

    return Progresso(
        enviados=set(dados.get("enviados", [])),
        falhos=set(dados.get("falhos", [])),
        invalidos=set(dados.get("invalidos", [])),
        midia_enviada=set(dados.get("midia_enviada", [])),
        nao_confirmados=set(dados.get("nao_confirmados", [])),
        erros=dados.get("erros", 0),
        ultimo_indice=dados.get("ultimo_indice", -1),
        nome=dados.get("nome", ""),
        telefone=dados.get("telefone", ""),
        data_hora=dados.get("data_hora", ""),
        retomar_apos=dados.get("retomar_apos"),
        planilha_sha256=dados.get("planilha_sha256", ""),
    )


def arquivar_progresso():
    """Guarda o progresso encerrado em vez de apaga-lo."""
    if not ARQUIVO_ESTADO.exists():
        return

    destino = ARQUIVO_ESTADO.with_name(
        f"estado_arquivado_{datetime.now():%Y%m%d_%H%M%S}.json"
    )
    try:
        os.replace(ARQUIVO_ESTADO, destino)
        _caminho_backup().unlink(missing_ok=True)
        log(f"Progresso anterior arquivado em: {destino}")
    except OSError as erro:
        log(f"AVISO: não consegui arquivar estado.json: {erro}")
