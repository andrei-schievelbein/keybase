"""Telas de entrada de uma linha: prompt e confirmacao.

Sao genericas e parametrizadas por callback. E essa escolha que impede a
triplicacao de voltar: os ~15 estados de prompt da versao anterior
(adicionar_nome, cadastrar_nota_desc, editar_snippet_num, ...) e os 9 estados
encadeados de delete colapsam nestas duas classes.

Regra dura: o CTkEntry so trata uma linha. Todo conteudo multilinha vai para o
editor. Na versao anterior notas e snippets eram cadastrados por este campo, o
que destruia qualquer conteudo com quebra de linha.
"""

from ..layout import truncar
from .base import Screen

CONFIRMACAO_FORTE = "DELETAR"


class PromptScreen(Screen):
    # A barra aqui e campo de nome, nao de comando: nada de menu, e o Ctrl+0
    # fica inerte em vez de alternar em silencio o menu da tela de baixo.
    MOSTRA_MENU = False

    def __init__(self, app, pergunta, on_submit, valor_inicial="",
                 validar=None, permitir_vazio=False, contexto="", senha=False,
                 detalhe="", itens=None, opcoes=None):
        super().__init__(app)
        #: escolhas numeradas [(numero, rotulo)], uma por linha no formato
        #: 'N - Rotulo' do resto do app - nunca espremidas numa linha so
        self.opcoes = opcoes or []
        #: nos listados sob a pergunta, numerados como na tela de baixo - quem
        #: pergunta "qual item?" nao obriga a voltar para descobrir o numero
        self.itens = itens or []
        self.ENTRADA_SENHA = senha
        self.detalhe = detalhe
        self.pergunta = pergunta
        self.on_submit = on_submit
        self.valor_inicial = valor_inicial
        self.validar = validar
        self.permitir_vazio = permitir_vazio
        self.contexto = contexto
        self._erro = None
        self._preenchido = False

    def on_enter(self):
        pass

    def render(self):
        view = self.app.view
        largura = view.colunas()
        if self.contexto:
            view.cabecalho(truncar(self.contexto, largura - 2))
        else:
            view.barra()
        view.linha(" " + truncar(self.pergunta, largura - 2), 'nota')
        if self.detalhe:
            view.linha(" " + truncar(self.detalhe, largura - 2), 'dica')
        if self._erro:
            view.linha(" " + truncar(self._erro, largura - 2), 'erro')
        view.barra()
        if self.opcoes:
            for numero, rotulo in self.opcoes:
                view.trechos([(f"{numero:>2} - ", 'numero'),
                              (truncar(rotulo, largura - 5), 'nota')])
            view.barra()
        if self.itens:
            from ..layout import linha_item
            for i, no in enumerate(self.itens, start=1):
                view.trechos(linha_item(i, no, largura))
            view.barra()
        view.linha(" ENTER confirma - ESC cancela", 'dica')
        view.barra()

        if not self._preenchido and self.valor_inicial:
            # Renomear ja vem com o nome atual no campo: editar e melhor que
            # redigitar, que era o que a versao anterior pedia.
            view.preencher_entrada(self.valor_inicial)
            self._preenchido = True

    def help_text(self):
        return None

    def handle_input(self, texto):
        texto = (texto or "").strip()

        if not texto and not self.permitir_vazio:
            self.app.pop()  # Enter vazio cancela
            return

        if self.validar:
            erro = self.validar(texto)
            if erro:
                self._erro = erro
                # mantem o que foi digitado, para corrigir em vez de recomecar -
                # menos senha: senha errada se redigita do zero
                if not self.ENTRADA_SENHA:
                    self.valor_inicial = texto
                    self._preenchido = False
                self.app.rerender()
                return

        self.app.pop()
        self.on_submit(texto)

    def on_back(self):
        self.app.pop()


class ConfirmScreen(Screen):
    """Confirmacao s/n, ou digitar DELETAR quando a acao apaga uma subarvore."""

    MOSTRA_MENU = False

    def __init__(self, app, pergunta, on_yes, detalhe="", forte=False):
        super().__init__(app)
        self.pergunta = pergunta
        self.on_yes = on_yes
        self.detalhe = detalhe
        self.forte = forte
        self._erro = None

    def on_enter(self):
        pass

    def render(self):
        view = self.app.view
        largura = view.colunas()
        view.barra()
        view.linha(" " + truncar(self.pergunta, largura - 2),
                   'erro' if self.forte else 'nota')
        if self.detalhe:
            view.linha(" " + truncar(self.detalhe, largura - 2), 'dica')
        if self._erro:
            view.linha(" " + truncar(self._erro, largura - 2), 'erro')
        view.barra()
        if self.forte:
            view.linha(f" Digite {CONFIRMACAO_FORTE} para confirmar - ESC cancela", 'dica')
        else:
            view.linha(" S confirma - qualquer outra tecla cancela", 'dica')
        view.barra()

    def handle_input(self, texto):
        texto = (texto or "").strip()

        if self.forte:
            if texto == CONFIRMACAO_FORTE:
                self.app.pop()
                self.on_yes()
            elif not texto:
                self.app.pop()
            else:
                self._erro = f"Digite exatamente {CONFIRMACAO_FORTE} para confirmar."
                self.app.rerender()
            return

        if texto.upper() == 'S':
            self.app.pop()
            self.on_yes()
        else:
            self.app.pop()

    def on_back(self):
        self.app.pop()
