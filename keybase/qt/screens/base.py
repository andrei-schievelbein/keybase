"""Classe base das telas.

Cada tela junta estado, renderizacao e tratamento de input. Foi o que permitiu
eliminar as seis variaveis globais e os quatro `global` espalhados pelo
despachante de 905 linhas da versao anterior.

O parsing de comando fica aqui, resolvido uma vez so - e por isso que `D3` e
`D` funcionam pelos mesmos caminhos sem codigo duplicado em cada tela.
"""

import re

from ... import selecao

# Comando e uma letra, com alvo opcional colado ou separado: 'D', 'D3', 'D 3'.
# Qualquer outra coisa cai no filtro, entao o padrao NAO pode aceitar texto
# solto depois da letra - senao 'd ados' viraria o comando D em vez de filtro.
PADRAO_COMANDO = re.compile(r'^([A-Za-z?])\s*(\d+)?$')
PALAVRAS_SAIR = ('sair', 'exit', 'quit')
#: letra + lista com virgula ou hifen: 'C1,2,5', 'D1-3,7' (so numero e 'D3')
PADRAO_LOTE = re.compile(r'^([A-Za-z])\s*(\d[\d\s]*[,\-][\d\s,\-]*)$')


class Screen:
    #: letra -> nome do metodo que a trata
    COMANDOS = {}
    #: letra -> rotulo curto exibido no rodape
    ROTULOS = {}
    #: False nas telas que nao desenham o menu (prompts, ajuda, recuperacao,
    #: editor). Uma flag so, consumida pelo desenho E pelo '?'/Ctrl+0: e ela que
    #: garante que o atalho seja inerte exatamente onde o menu nao aparece, em
    #: vez de alternar em silencio um menu que esta fora da tela.
    MOSTRA_MENU = True
    #: True mascara o campo de entrada (prompt de senha). Lido a cada render,
    #: entao nenhuma tela precisa lembrar de desligar a mascara ao sair.
    ENTRADA_SENHA = False

    def __init__(self, app):
        self.app = app

    # --- ciclo de vida -----------------------------------------------------

    def on_enter(self):
        """Recarrega o que a tela precisa. Chamada antes de todo render."""

    def render(self):
        raise NotImplementedError

    def help_text(self):
        """Texto da barra de dica; None a esconde."""
        return None

    def usa_editor(self):
        return False

    # --- input -------------------------------------------------------------

    def handle_input(self, texto):
        texto = (texto or "").strip()

        if texto == "":
            return self.on_back()

        if texto.lower() in PALAVRAS_SAIR:
            return self.app.sair()

        # '?' e '??' sao tratados aqui, e nao por COMANDOS, porque
        # PADRAO_COMANDO casa uma LETRA so - '??' nunca chegaria ao despacho.
        if texto == '??':
            return self.cmd_ajuda_completa()

        if texto == '?':
            return self.on_ajuda()

        # '/' sozinho e comando (ir para a raiz) onde a tela o tem; '/texto'
        # continua sendo filtro, para termos que colidem com uma letra
        if texto == '/' and '/' in self.COMANDOS:
            return getattr(self, self.COMANDOS['/'])(alvo=None)

        if texto.startswith('/'):
            return self.cmd_filtro(texto[1:].strip())

        if texto.isdigit():
            return self.selecionar(int(texto) - 1)

        lote = self._lote_na_barra(texto)
        if lote is not None:
            letra, indices = lote
            if isinstance(indices, selecao.SelecaoInvalida):
                self.app.flash(str(indices), erro=True)
                self.app.rerender()
                return
            return getattr(self, self.COMANDOS[letra])(alvo=list(indices))

        match = PADRAO_COMANDO.match(texto)
        if match:
            letra, alvo = match.groups()
            letra = letra.upper()
            metodo = self.COMANDOS.get(letra)
            if metodo:
                alvo = int(alvo) - 1 if alvo else None
                return getattr(self, metodo)(alvo=alvo)

        # Nao e comando: o texto filtra o nivel visivel. Cada tela decide o que
        # "filtrar" significa - a de busca global, por exemplo, refaz a busca.
        return self.cmd_filtro(texto)

    def entrada_invalida(self, texto):
        self.app.flash("Comando não reconhecido. Digite ? para ver os comandos "
                       "ou ?? para a ajuda.", erro=True)
        self.app.rerender()

    def selecionar(self, indice):
        """Trata um numero digitado. Telas sem lista ignoram."""
        self.entrada_invalida(str(indice + 1))

    def cmd_filtro(self, termo):
        """Texto livre (ou /termo). Telas sem nada a filtrar avisam.

        E aqui que a recursao para: o fallback de handle_input chama cmd_filtro,
        e quem nao sobrescreve cai neste aviso em vez de voltar ao parsing.
        """
        self.entrada_invalida(termo)

    # --- acoes padrao ------------------------------------------------------

    def on_back(self):
        self.app.pop()

    def on_save(self):
        """Ctrl+S. No-op fora do editor."""

    def on_cancel(self):
        """Esc. Com texto na barra, so apaga o texto; sem, equivale a voltar.

        Nas telas com menu: quem digitou um comando pela metade (C, sem o
        ENTER) desiste dele com ESC, sem ser tirado da tela.
        """
        if self.MOSTRA_MENU and self.app.view.ler_entrada():
            self.app.view.limpar_entrada()
            self.app.rerender()
            return
        self.on_back()

    def on_modo(self, modo):
        """Ctrl+1/2/3. No-op: so a EditorScreen implementa.

        E por ser no-op aqui que os atalhos de modo sao inertes fora da edicao,
        sem nenhum `if` espalhado pela janela.
        """

    def on_ciclar_modo(self):
        """Ctrl+E. Mesma logica do on_modo."""

    def on_seta(self, delta):
        """Seta na barra. No-op: so as telas com destaque implementam."""

    def on_tecla_de_lista(self, nome):
        """'cima', 'baixo', 'espaco' ou 'enter' com o foco na area de leitura.

        Devolve True se tratou. Por padrao nao trata: a area rola como sempre.
        """
        return False

    def on_ajuda(self):
        """'?' na barra ou Ctrl+0: mostra/esconde o menu de comandos."""
        if not self.MOSTRA_MENU:
            return
        self.app.menu_visivel = not self.app.menu_visivel
        self.app.rerender()

    def cmd_favoritos(self, alvo=None):
        """L: favoritos e notas abertas recentemente."""
        from .favoritos import FavoritosScreen
        self.app.push(FavoritosScreen(self.app))

    def cmd_config(self, alvo=None):
        """O (Opcoes): a configuracao aberta no editor, como uma nota."""
        from .config import ConfigScreen
        self.app.push(ConfigScreen(self.app, self.app.caminho_config))

    def cmd_ajuda_completa(self):
        """'??' na barra: a referencia completa."""
        from .help import HelpScreen
        self.app.push(HelpScreen(self.app))

    # --- menu de comandos --------------------------------------------------

    def comandos_disponiveis(self):
        """Letras ativas agora. Sobrescreva para esconder o que nao se aplica."""
        return set(self.COMANDOS)

    #: pares (letra, rotulo) acrescentados ao fim do menu
    EXTRAS = (("??", "Ajuda completa"), ("sair", "Encerrar"))

    #: o comando da barra com que o menu foi desenhado pela ultima vez (ver
    #: ao_digitar): so repinta quando ele muda, nao a cada tecla
    _comando_desenhado = None

    def comando_na_barra(self, texto):
        """(letra, alvo) se o texto na barra e um comando desta tela, ou None.

        Mesmo parsing de handle_input, para o menu nunca prometer o que o
        ENTER nao faria. Letra fora de comandos_disponiveis nao conta: o menu
        completo, que ja a esconde, continua valendo.
        """
        texto = (texto or "").strip()
        if texto == '/':
            return ('/', None) if '/' in self.comandos_disponiveis() else None
        lote = self._lote_na_barra(texto)
        if lote is not None:
            letra, indices = lote
            # a excecao nao compara por valor: o menu so precisa saber que e invalida
            return letra, (indices if isinstance(indices, tuple) else 'invalida')
        match = PADRAO_COMANDO.match(texto)
        if not match:
            return None
        letra, alvo = match.groups()
        letra = letra.upper()
        if letra not in self.COMANDOS or letra not in self.comandos_disponiveis():
            return None
        return letra, (int(alvo) - 1 if alvo else None)

    def menu_do_comando(self, letra, alvo):
        """Pares (tecla, rotulo) do menu enquanto `letra` esta na barra.

        Sem alvo (comandos como O): ENTER executa, ESC desiste. Comandos sobre
        um item (ACOES_NO_ITEM): com C na barra, so o que serve dentro do C -
        o numero, a lista, o ENTER que pergunta qual e o ESC. Com C3, o item
        ja nomeado; com C1,2, a contagem.
        """
        desistir = ("ESC", "Desistir do comando")
        if letra not in self.ACOES_NO_ITEM:
            return [("ENTER", self.ROTULOS.get(letra, "Executar")), desistir]

        acao = self.ACOES_NO_ITEM[letra]
        if alvo == 'invalida':
            return [("ENTER", "Números fora da lista ou incompletos"), desistir]
        if isinstance(alvo, tuple):
            if len(alvo) > 1:
                return [("ENTER", acao.format(f"{len(alvo)} itens")), desistir]
            alvo = alvo[0]
        if alvo is not None:
            if alvo >= len(self.itens):
                return [("ENTER", f"Não há item {alvo + 1} na lista"), desistir]
            return [("ENTER", self.acao_no_item(letra, alvo)), desistir]

        pares = [(f"{letra} + nº", acao.format("o item nº"))]
        if letra in self.COMANDOS_EM_LOTE:
            pares.append((f"{letra} + 1,2,5 / 1-4", acao.format("vários itens")))
        return pares + [("ENTER", "Escolher na lista (um, vários ou M para marcar)"
                         if letra in self.COMANDOS_EM_LOTE
                         else "Escolher o item pelo número"), desistir]

    def acao_no_item(self, letra, indice):
        """'Copiar 'Nota' para outra pasta': o que o ENTER faz com o item."""
        no = self.itens[indice]
        nome = no.nome + ('/' if getattr(no, 'filhos', None) is not None else '')
        return self.ACOES_NO_ITEM[letra].format(repr(nome))

    # --- comandos sobre itens da lista ---------------------------------------

    #: a lista exibida, numerada a partir de 1 (as telas de lista a preenchem)
    itens = ()
    #: comandos que agem sobre um item: o que o menu diz com a letra na barra,
    #: '{}' e o item ("o item 3", "'Receitas/'", "3 itens")
    ACOES_NO_ITEM = {}
    #: os que aceitam varios itens: 'C1,2,5', 'D1-4', ou M na pergunta
    COMANDOS_EM_LOTE = ()

    def _lote_na_barra(self, texto):
        """(letra, indices) ou (letra, SelecaoInvalida) para 'C1,2,5'; ou None."""
        match = PADRAO_LOTE.match((texto or "").strip())
        if not match:
            return None
        letra = match.group(1).upper()
        if letra not in self.COMANDOS_EM_LOTE or letra not in self.comandos_disponiveis():
            return None
        try:
            return letra, tuple(selecao.interpretar(match.group(2), len(self.itens)))
        except selecao.SelecaoInvalida as e:
            return letra, e

    def contexto_do_prompt(self):
        """Linha de cima das perguntas "qual item?" (o browser poe o caminho)."""
        return ""

    def _item(self, indice):
        """Resolve um numero contra a lista EXIBIDA."""
        if indice is None or not (0 <= indice < len(self.itens)):
            self.app.flash("Número fora da lista.", erro=True)
            self.app.rerender()
            return None
        return self.itens[indice]

    def _com_alvo(self, alvo, pergunta, acao, varios=None, verbo=None,
                  por_indice=False, rotulos=None):
        """Aceita `D3` (alvo direto) e `D` (pergunta o numero).

        Com `varios` (comandos em lote), tambem uma lista: 'C1,2,5' na barra ja
        vem como lista de indices; na pergunta valem '1,2,5', '1-4' e M, que
        abre a selecao com setas e espaco. Um item so vai sempre para `acao`.

        por_indice=True entrega posicoes em vez de nos: quando o mesmo no
        aparece duas vezes na lista (favorito e recente) e o que muda e a
        posicao. `rotulos` troca a linha de cada item na pergunta e na selecao.
        """
        from .prompt import PromptScreen

        def valor(i):
            return i if por_indice else itens[i]

        def entregar(indices):
            if len(indices) == 1 or varios is None:
                acao(valor(indices[0]))
            else:
                varios([valor(i) for i in indices])

        itens = list(self.itens)
        if isinstance(alvo, list):
            entregar(alvo)   # ja validados na barra
            return
        if alvo is not None:
            if self._item(alvo) is not None:
                acao(valor(alvo))
            return

        if not itens:
            self.app.flash("Não há itens nesta lista.", erro=True)
            self.app.rerender()
            return

        contexto = self.contexto_do_prompt()
        mostrar = dict(itens=itens) if rotulos is None \
            else dict(opcoes=list(enumerate(rotulos, start=1)))

        if varios is None:
            def validar(texto):
                # outra letra aqui nao troca de comando nem cancela: o prompt
                # fica aberto ate vir um numero da lista, ENTER vazio ou ESC
                if texto.isdigit() and 1 <= int(texto) <= len(itens):
                    return None
                return f"Digite o número do item, de 1 a {len(itens)}. ESC cancela."

            self.app.push(PromptScreen(
                self.app, pergunta, lambda texto: acao(valor(int(texto) - 1)),
                validar=validar, contexto=contexto, **mostrar,
            ))
            return

        def validar_lista(texto):
            try:
                selecao.interpretar(texto, len(itens))
            except selecao.SelecaoInvalida as e:
                return str(e)
            return None

        def marcar():
            from .selecao import SelecaoScreen
            self.app.push(SelecaoScreen(self.app, itens, verbo, entregar,
                                        contexto=contexto, rotulos=rotulos))

        self.app.push(PromptScreen(
            self.app, pergunta,
            lambda texto: entregar(selecao.interpretar(texto, len(itens))),
            validar=validar_lista, contexto=contexto, **mostrar,
            menu=[("nº", "Um item"), ("1,2,5 / 1-4", "Vários itens"),
                  ("M", "Seleção múltipla (setas e espaço)"), ("ESC", "Cancelar")],
            atalhos={'M': marcar},
        ))

    def ao_digitar(self, texto):
        """Cada tecla na barra. Devolve True se a tela precisa ser repintada:
        o menu troca para as opcoes do comando digitado (e volta ao apagar)."""
        if not (self.MOSTRA_MENU and self.app.menu_visivel) or self.usa_editor():
            return False
        return self.comando_na_barra(texto) != self._comando_desenhado

    def desenhar_menu(self):
        """Menu de comandos: PRIMEIRO bloco da area de leitura, logo abaixo da
        barra de pesquisa. Escondido por padrao - '?' ou Ctrl+0 o alterna.

        Com um comando digitado na barra (C, C3, O...), antes do ENTER, mostra
        so o que cabe dentro dele: o resto do menu nao se aplica ali, e
        escolher outra letra so trocaria de comando.

        Nao emite a barra de baixo: quem fecha o bloco e a barra de abertura da
        propria tela, que de outro modo apareceria duplicada.
        """
        self._comando_desenhado = None
        if not (self.MOSTRA_MENU and self.app.menu_visivel):
            return

        from ..layout import montar_menu, montar_menu_fixo
        view = self.app.view
        comando = self.comando_na_barra(view.ler_entrada())
        if comando is not None:
            self._comando_desenhado = comando
            # uma opcao por linha: sao duas ou tres, e os rotulos citam o item
            linhas = montar_menu_fixo(self.menu_do_comando(*comando), view.colunas(),
                                      colunas=1)
        else:
            linhas = montar_menu(self.COMANDOS, self.ROTULOS,
                                 self.comandos_disponiveis(),
                                 largura=view.colunas(),
                                 extras=self.EXTRAS)
        if not linhas:
            return

        view.barra()
        for linha in linhas:
            view.linha(linha, 'dica')
