"""RecoveryScreen: o app nao conseguiu ler o arquivo de dados.

Nada e sobrescrito. O usuario ve o erro, o caminho do arquivo e as opcoes de
restauracao. Na versao anterior um JSON invalido virava uma base vazia em
silencio, e o primeiro save apagava os dados de verdade.
"""

from ... import storage
from .base import Screen


class RecoveryScreen(Screen):
    # Modo somente leitura: nenhum comando do menu se aplica aqui.
    MOSTRA_MENU = False

    def __init__(self, app, erro, caminho):
        super().__init__(app)
        self.erro = erro
        self.caminho = caminho
        self.opcoes = []

    def on_enter(self):
        self.opcoes = storage.backups_disponiveis(self.caminho)

    def render(self):
        view = self.app.view
        view.cabecalho("NÃO FOI POSSÍVEL LER SEUS DADOS", 'erro')
        view.linha(" " + str(self.erro), 'erro')
        view.linha(f" Arquivo: {self.caminho}", 'contador')
        view.barra()
        view.linha(" Nada foi alterado. O app está em modo somente leitura,", 'dica')
        view.linha(" então seus dados continuam no disco exatamente como estão.", 'dica')
        view.barra()

        for i, (rotulo, _) in enumerate(self.opcoes, start=1):
            view.trechos([(f"{i:>2} - ", 'numero'), (f"Restaurar {rotulo}", 'nota')])

        if not self.opcoes:
            view.linha(" Não há backups disponíveis para restaurar.", 'vazio')
            view.linha(" Você pode corrigir o arquivo à mão num editor de texto", 'dica')
            view.linha(" e reabrir o KeyBase.", 'dica')

        view.barra()
        view.linha(" Digite 'sair' para encerrar sem alterar nada.", 'dica')
        view.barra()

    def selecionar(self, indice):
        if not (0 <= indice < len(self.opcoes)):
            self.app.flash("Número fora da lista.", erro=True)
            self.app.rerender()
            return

        rotulo, origem = self.opcoes[indice]
        try:
            storage.restaurar(origem, self.caminho)
            doc = storage.carregar(self.caminho)
        except (storage.StorageError, OSError) as e:
            self.app.flash(f"Falha ao restaurar: {e}", erro=True)
            self.app.rerender()
            return

        self.app.doc = doc
        self.app.reindexar()
        self.app.flash(f"{rotulo} restaurado.")
        self.app.go_root()

    def on_back(self):
        self.app.flash("Digite 'sair' para encerrar sem alterar nada.", erro=True)
        self.app.rerender()
