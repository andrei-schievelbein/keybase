"""Bootstrap: monta a janela, carrega os dados e entra no event loop."""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import paths, storage
from .config import carregar_config
from .model import ID_RAIZ
from .qt.app import App
from .qt.estilo import aplicar_tema
from .qt.janela import JanelaPrincipal
from .qt.screens.browser import BrowserScreen
from .qt.screens.recovery import RecoveryScreen


def _icone():
    try:
        caminho = paths.recurso('keybase.ico')
        if caminho.exists():
            # O Qt le .ico em todas as plataformas, diferente do iconbitmap do
            # Tk, que so funcionava no Windows.
            return QIcon(str(caminho))
    except Exception as e:
        print(f"Aviso: não foi possível carregar o ícone: {e}")
    return None


def main():
    config = carregar_config()

    qapp = QApplication(sys.argv)
    qapp.setApplicationName("KeyBase")
    aplicar_tema(qapp, config['theme'])

    icone = _icone()
    if icone is not None:
        qapp.setWindowIcon(icone)

    janela = JanelaPrincipal(config)
    if icone is not None:
        janela.setWindowIcon(icone)

    caminho = paths.arquivo_dados()

    erro_carga = None
    try:
        doc = storage.carregar(caminho)
    except storage.StorageError as e:
        # Modo recuperacao: documento vazio e somente leitura, para que nenhum
        # save posterior possa sobrescrever o arquivo que nao pudemos ler.
        erro_carga = e
        doc = storage.Documento.novo()
        doc.somente_leitura = True

    app = App(janela, janela.view, doc, caminho, config)
    janela.ligar(app)

    if erro_carga is not None:
        app.stack = [RecoveryScreen(app, erro_carga, caminho)]
    else:
        app.stack = [BrowserScreen(app, ID_RAIZ)]
        if doc.avisos:
            app.flash("Arquivo reparado: " + "; ".join(doc.avisos))

    janela.aplicar_geometria(config['geometry'])
    janela.show()          # antes do rerender: colunas() so e valida depois
    app.rerender()

    QTimer.singleShot(0, janela.view.focar_entrada)
    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()
