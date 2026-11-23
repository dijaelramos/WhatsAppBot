import tempfile
import unittest
from pathlib import Path
from unittest import mock


class TesteIsolado(unittest.TestCase):
    """Redireciona estado e log para uma pasta temporaria em cada teste."""

    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.pasta = Path(pasta.name)
        self.arquivo_estado = self.pasta / "estado.json"

        for alvo, valor in (
            ("core.estado.ARQUIVO_ESTADO", self.arquivo_estado),
            ("core.logger.ARQUIVO_LOG", self.pasta / "log.txt"),
            ("core.inexistentes.ARQUIVO_INEXISTENTES", self.pasta / "inexistentes.txt"),
            ("core.destinatarios.ARQUIVO_DESCADASTRO", self.pasta / "descadastro.txt"),
            ("builtins.print", lambda *a, **k: None),
        ):
            patcher = mock.patch(alvo, valor)
            patcher.start()
            self.addCleanup(patcher.stop)
