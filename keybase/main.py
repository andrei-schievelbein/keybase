"""Bootstrap: monta a janela, carrega os dados e entra no mainloop."""

import customtkinter as ctk

from . import paths, storage
from .config import aplicar_tema, carregar_config, salvar_config
from .model import ID_RAIZ
from .ui.app import App
from .ui.screens.browser import BrowserScreen
from .ui.screens.recovery import RecoveryScreen
from .ui.view import TerminalView


def _carregar_icone(root):
    try:
        icone = paths.recurso('keybase.ico')
        if icone.exists():
            root.iconbitmap(str(icone))
    except Exception as e:
        print(f"Aviso: não foi possível carregar o ícone: {e}")


def main():
    config = carregar_config()
    aplicar_tema(config['theme'])

    root = ctk.CTk()
    root.title("KeyBase")
    _carregar_icone(root)
    root.geometry(config['geometry'])

    view = TerminalView(root, config)
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

    app = App(root, view, doc, caminho, config)

    if erro_carga is not None:
        app.stack = [RecoveryScreen(app, erro_carga, caminho)]
    else:
        app.stack = [BrowserScreen(app, ID_RAIZ)]
        if doc.avisos:
            app.flash("Arquivo reparado: " + "; ".join(doc.avisos))

    view.entrada.bind("<Return>", app.submit)
    root.bind("<Control-s>", app.save)
    root.bind("<Control-S>", app.save)
    root.bind("<Escape>", app.cancel)
    root.protocol("WM_DELETE_WINDOW", app.ao_fechar)

    app.rerender()
    root.after(100, view.entrada.focus_set)
    root.mainloop()


if __name__ == "__main__":
    main()
