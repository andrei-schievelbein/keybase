"""Historico de uma nota (H no viewer): as versoes guardadas nos backups.

HistoricoScreen lista as versoes, uma por linha; VersaoScreen mostra uma,
so para leitura, e R a restaura como o conteudo atual. Restaurar entra no
desfazer (U), como qualquer outra acao que troca o que ja existia.
"""

from ... import cripto, historico, tree
from ...model import File
from ..layout import LARGURA_NUMERO, truncar
from .base import Screen


class HistoricoScreen(Screen):
    COMANDOS = {'V': 'cmd_voltar'}
    ROTULOS = {'V': 'Voltar'}

    def __init__(self, app, file_id):
        super().__init__(app)
        self.file_id = file_id
        self.file = None
        self.versoes = []
        self.descartada = False
        self._lidas = False

    def on_enter(self):
        no = self.app.no(self.file_id)
        if no is None or not isinstance(no, File) or no.conteudo is None:
            self.descartada = True
            return
        self.file = no
        if not self._lidas:  # ler os backups a cada repintura seria desperdicio
            self.versoes = historico.versoes(self.app.caminho_dados, no.id,
                                             self.app.cofre, atual=no.conteudo)
            self._lidas = True

    def render(self):
        view = self.app.view
        largura = view.colunas()
        msg, erro = self.app.consumir_flash()
        view.cabecalho(msg if msg else truncar(f"HISTÓRICO - {self.file.nome}", largura - 2),
                       ('erro' if erro else 'flash') if msg else 'breadcrumb')
        if not self.versoes:
            view.linha(" Nenhuma versão diferente da atual nos backups.", 'vazio')
            view.linha(" O KeyBase guarda o backup anterior e um snapshot por dia "
                       "(últimos 7).", 'dica')
        for i, versao in enumerate(self.versoes, start=1):
            plural = "linha" if versao.n_linhas == 1 else "linhas"
            prefixo = f"{i:>{LARGURA_NUMERO}} - "
            view.trechos([(prefixo, 'numero'),
                          (truncar(f"{versao.rotulo} · {versao.n_linhas} {plural}",
                                   largura - len(prefixo)), 'nota')])
        view.barra()
        if self.versoes:
            view.linha(" Número abre a versão · V ou ENTER volta", 'dica')
            view.barra()

    def selecionar(self, indice):
        if not (0 <= indice < len(self.versoes)):
            self.app.flash("Número fora da lista.", erro=True)
            self.app.rerender()
            return
        self.app.push(VersaoScreen(self.app, self.file_id, self.versoes[indice]))

    def cmd_voltar(self, alvo=None):
        self.app.pop()


class VersaoScreen(Screen):
    COMANDOS = {'R': 'cmd_restaurar', 'V': 'cmd_voltar'}
    ROTULOS = {'R': 'Restaurar esta versão', 'V': 'Voltar'}

    def __init__(self, app, file_id, versao):
        super().__init__(app)
        self.file_id = file_id
        self.versao = versao
        self.file = None
        self.descartada = False

    def on_enter(self):
        no = self.app.no(self.file_id)
        self.descartada = no is None or no.conteudo is None
        self.file = no

    def render(self):
        view = self.app.view
        largura = view.colunas()
        msg, erro = self.app.consumir_flash()
        view.cabecalho(msg if msg else truncar(f"{self.file.nome} - {self.versao.rotulo}",
                                               largura - 2),
                       ('erro' if erro else 'flash') if msg else 'breadcrumb')
        if self.versao.conteudo.strip():
            view.markdown(self.versao.conteudo)
        else:
            view.linha(" (vazia nesta versão)", 'vazio')
        view.barra()
        view.linha(" Só leitura · R restaura esta versão · V ou ENTER volta", 'dica')
        view.barra()

    def cmd_restaurar(self, alvo=None):
        nota, texto = self.file, self.versao.conteudo
        self.app.registrar_desfazer(f"restaurar a versão de {nota.nome!r}")
        if nota.cifrado:
            cripto.selar(self.app.cofre, nota, texto)
        else:
            tree.definir_conteudo(nota, texto)
        self.app.persistir()
        self.app.pop(2)  # a versao e a lista: volta ao viewer da nota
        self.app.flash(f"Versão restaurada ({self.versao.rotulo}). U desfaz.")
        self.app.rerender()

    def cmd_voltar(self, alvo=None):
        self.app.pop()
