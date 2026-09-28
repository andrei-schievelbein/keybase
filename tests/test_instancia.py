"""Uma instancia so (socket local) e o alternar do atalho global."""

import os
import shutil
import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_qt import BaseUI, _app_qt  # noqa: E402

try:
    from keybase.qt import instancia
except Exception as e:  # pragma: no cover
    instancia = None
    _erro = e


def processar(ms=200):
    """Roda o event loop um pouco: o servidor atende no loop do Qt."""
    fim = time.monotonic() + ms / 1000
    while time.monotonic() < fim:
        _app_qt().processEvents()
        time.sleep(0.01)


@unittest.skipUnless(instancia is not None, "PySide6 indisponivel")
class TestInstancia(unittest.TestCase):
    def setUp(self):
        _app_qt()
        # caminho curto: socket Unix tem limite de ~104 caracteres
        self.dir = Path(tempfile.mkdtemp(prefix='kb', dir='/tmp'))
        self.caminho = self.dir / 'i.sock'
        self.servidor = None

    def tearDown(self):
        if self.servidor is not None:
            self.servidor.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_sem_ninguem_ouvindo(self):
        self.assertFalse(instancia.avisar_instancia_aberta(self.caminho))

    def test_avisa_a_aberta_e_ela_alterna(self):
        chamadas = []
        self.servidor = instancia.ouvir(self.caminho, lambda: chamadas.append(1))
        self.assertIsNotNone(self.servidor)
        # o connect fecha no sistema (backlog); a leitura, no event loop
        self.assertTrue(instancia.avisar_instancia_aberta(self.caminho))
        processar()
        self.assertEqual(chamadas, [1])

    def test_o_script_fala_direto_com_o_socket(self):
        """O abrir-keybase.sh manda 'alternar' pelo nc -U, sem Qt no meio."""
        chamadas = []
        self.servidor = instancia.ouvir(self.caminho, lambda: chamadas.append(1))
        cliente = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cliente.connect(str(self.caminho))
        cliente.sendall(b'alternar\n')
        cliente.close()
        processar()
        self.assertEqual(chamadas, [1])

    def test_socket_velho_nao_impede_de_ouvir(self):
        # o arquivo de um KeyBase que caiu: existe, mas ninguem ouve
        velho = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        velho.bind(str(self.caminho))
        velho.close()
        self.assertTrue(self.caminho.exists())
        self.assertFalse(instancia.avisar_instancia_aberta(self.caminho))
        self.servidor = instancia.ouvir(self.caminho, lambda: None)
        self.assertIsNotNone(self.servidor)

    def test_mensagem_desconhecida_e_ignorada(self):
        chamadas = []
        self.servidor = instancia.ouvir(self.caminho, lambda: chamadas.append(1))
        cliente = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cliente.connect(str(self.caminho))
        cliente.sendall(b'apagar tudo\n')
        cliente.close()
        processar()
        self.assertEqual(chamadas, [])


class TestAlternarVisibilidade(BaseUI):
    """Na frente, esconde (Cmd+H); atras, traz para a frente."""

    def estado(self, ativo):
        from PySide6.QtCore import Qt
        valor = (Qt.ApplicationState.ApplicationActive if ativo
                 else Qt.ApplicationState.ApplicationInactive)
        return mock.patch('keybase.qt.janela.QGuiApplication.applicationState',
                          return_value=valor)

    def test_na_frente_esconde(self):
        with self.estado(True), \
                mock.patch('keybase.qt.macos.esconder_app', return_value=True) as esconder, \
                mock.patch('keybase.qt.macos.ativar_app') as ativar:
            self.janela.alternar_visibilidade()
        esconder.assert_called_once()
        ativar.assert_not_called()

    def test_atras_traz_para_a_frente(self):
        with self.estado(False), \
                mock.patch('keybase.qt.macos.esconder_app') as esconder, \
                mock.patch('keybase.qt.macos.ativar_app') as ativar:
            self.janela.alternar_visibilidade()
        ativar.assert_called_once()
        esconder.assert_not_called()
        self.assertTrue(self.janela.isVisible())

    def test_so_mostrar_nunca_esconde(self):
        with self.estado(True), \
                mock.patch('keybase.qt.macos.esconder_app') as esconder, \
                mock.patch('keybase.qt.macos.ativar_app') as ativar:
            self.janela.alternar_visibilidade(so_mostrar=True)
        esconder.assert_not_called()
        ativar.assert_called_once()

    def test_sem_macos_minimiza(self):
        with self.estado(True), \
                mock.patch('keybase.qt.macos.esconder_app', return_value=False):
            self.janela.alternar_visibilidade()
        _app_qt().processEvents()
        self.assertTrue(self.janela.isMinimized())


if __name__ == '__main__':
    unittest.main()
