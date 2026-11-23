from dataclasses import dataclass, field

from config import ARQUIVO_DESCADASTRO
from core.logger import log
from core.mensagem import (
    personalizar_mensagem,
    valores_das_variaveis,
    variaveis_vazias,
)
from core.telefone import normalizar_telefone

_CABECALHO_DESCADASTRO = (
    "# Um telefone por linha. Quem estiver aqui nunca recebe mensagens.\n"
    "# Linhas iniciadas com # são ignoradas.\n"
)


@dataclass(frozen=True)
class Destinatario:
    indice: int
    nome: str
    telefone: str
    texto: str


@dataclass
class Selecao:
    """Resultado da triagem da planilha; as listas guardam a posicao do contato."""

    destinatarios: list = field(default_factory=list)
    invalidos: list = field(default_factory=list)
    duplicados: list = field(default_factory=list)
    descadastrados: list = field(default_factory=list)
    incompletos: list = field(default_factory=list)
    inexistentes: list = field(default_factory=list)


def carregar_telefones(arquivo, cabecalho):
    """Le uma lista de telefones, criando o arquivo se ele nao existir."""
    if not arquivo.exists():
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(cabecalho, encoding="utf-8")
        return set()

    telefones = set()
    for numero_linha, linha in enumerate(
        arquivo.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        linha = linha.split("#", 1)[0].strip()
        if not linha:
            continue
        telefone = normalizar_telefone(linha, True)
        if telefone:
            telefones.add(telefone)
        else:
            log(f"AVISO: {arquivo.name}, linha {numero_linha}: telefone inválido.")
    return telefones


def carregar_descadastro(arquivo=None):
    """Le a lista de quem pediu para nao receber mensagens."""
    return carregar_telefones(
        arquivo or ARQUIVO_DESCADASTRO,
        _CABECALHO_DESCADASTRO,
    )


def telefones_por_indice(contatos, coluna_contato, acrescentar_codigo_brasil):
    """Normaliza a coluna de telefone mantendo a posicao de cada contato."""
    return [
        normalizar_telefone(
            list(contato.values())[coluna_contato - 1],
            acrescentar_codigo_brasil,
        )
        for contato in contatos
    ]


def montar_destinatarios(
    contatos,
    mensagem,
    coluna_contato,
    acrescentar_codigo_brasil,
    quantidade_variaveis,
    descadastro,
    inexistentes=frozenset(),
):
    """Separa quem pode receber a campanha de quem precisa ficar de fora."""
    selecao = Selecao()
    telefones_vistos = set()
    telefones = telefones_por_indice(
        contatos,
        coluna_contato,
        acrescentar_codigo_brasil,
    )

    for indice, (contato, telefone) in enumerate(zip(contatos, telefones)):
        numero = indice + 1
        if telefone is None:
            selecao.invalidos.append(numero)
        elif telefone in inexistentes:
            selecao.inexistentes.append(numero)
        elif telefone in descadastro:
            selecao.descadastrados.append(numero)
        elif telefone in telefones_vistos:
            selecao.duplicados.append(numero)
        elif variaveis_vazias(
            mensagem,
            contato,
            coluna_contato,
            quantidade_variaveis,
        ):
            selecao.incompletos.append(numero)
        else:
            telefones_vistos.add(telefone)
            valores = valores_das_variaveis(contato, coluna_contato, 1)
            selecao.destinatarios.append(
                Destinatario(
                    indice=indice,
                    nome=(valores[0] if valores else "") or "(sem nome)",
                    telefone=telefone,
                    texto=personalizar_mensagem(
                        mensagem,
                        contato,
                        quantidade_variaveis,
                        coluna_contato,
                    ),
                )
            )

    return selecao
