class EntradaInvalida(Exception):
    """Planilha, mensagem ou midia impedem o inicio da campanha."""


class ErroEstado(Exception):
    """O progresso nao pode ser lido ou salvo; continuar geraria duplicidade."""


class NumeroInvalido(Exception):
    """O WhatsApp informou que o numero nao existe; nao adianta tentar de novo."""


class SessaoPerdida(Exception):
    """O navegador fechou ou o WhatsApp Web saiu da conta."""
