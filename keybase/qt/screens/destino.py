"""DestinoScreen: escolher a pasta para onde mover (M) ou copiar (C) um item.

Uma tela so, que navega por dentro: o numero entra numa sub-pasta, Enter
vazio sobe, / vai a raiz e C confirma (move ou copia) para a pasta mostrada.
O menu aqui e FIXO, sempre visivel, no visual do menu dinamico: sao poucos
comandos e nenhum deles e obvio sem ver. Empilhar uma tela
por nivel, como o browser faz, obrigaria o cancelamento a desempilhar N telas.

So pastas aparecem, e nunca os proprios itens movidos: entrar num deles seria
o unico jeito de pedir um ciclo, e tree.mover recusaria de qualquer forma.

Recebe um item ou varios (selecao multipla): o lote e movido ou copiado de uma
vez, com um registro so de desfazer. No mover, nome ja usado no destino nao
trava o lote: a tela pergunta o que fazer com os conflitantes.
"""

from ... import cripto, selecao, tree
from ...model import Folder
from ..layout import linha_item, montar_breadcrumb, truncar
from .base import Screen
from .prompt import ConfirmScreen, PromptScreen


class DestinoScreen(Screen):
    COMANDOS = {'C': 'cmd_confirmar', '/': 'cmd_raiz', 'V': 'cmd_voltar'}
    MOSTRA_MENU = False  # o menu e fixo (desenhar_menu): '?' e o botao nao o escondem

    def __init__(self, app, no_ids, pasta_id, copiar=False):
        super().__init__(app)
        #: copiar = mover sem tirar da origem (C na lista)
        self.copiar = copiar
        #: um id ou varios, na ordem da lista de origem
        self.no_ids = [no_ids] if isinstance(no_ids, str) else list(no_ids)
        self.pasta_id = pasta_id
        self.nos = []
        self.pasta = None
        self.itens = []
        self.descartada = False

    @property
    def no(self):
        """O primeiro item (o unico, quando nao e lote)."""
        return self.nos[0] if self.nos else None

    def on_enter(self):
        # um item que sumiu por baixo sai do lote; lote vazio descarta a tela
        self.nos = [no for no in (self.app.no(i) for i in self.no_ids) if no is not None]
        if not self.nos:
            self.descartada = True
            return
        pasta = self.app.no(self.pasta_id)
        # a pasta mostrada sumiu ou trancou (T, inatividade): volta para a raiz
        if pasta is None or not isinstance(pasta, Folder) or pasta.trancada:
            pasta = self.app.raiz
            self.pasta_id = pasta.id
        self.pasta = pasta
        movidos = {no.id for no in self.nos}
        self.itens = [f for f in tree.filhos_ordenados(pasta)
                      if isinstance(f, Folder) and f.id not in movidos]

    def _o_que(self):
        """"'Nota'" ou "3 itens", para os titulos e avisos."""
        return repr(self.no.nome) if len(self.nos) == 1 else f"{len(self.nos)} itens"

    def desenhar_menu(self):
        from ..layout import montar_menu_fixo
        view = self.app.view
        verbo = "Copiar" if self.copiar else "Mover"
        pares = [("C", f"{verbo} para cá"), ("ENTER", "Subir nível"),
                 ("/", "Raiz"), ("ESC", "Cancelar")]
        view.barra()
        for linha in montar_menu_fixo(pares, view.colunas()):
            view.linha(linha, 'dica')

    def render(self):
        view = self.app.view
        largura = view.colunas()
        caminho = montar_breadcrumb(self.app.caminho_de(self.pasta_id), largura - 2)

        view.barra()
        verbo = "Copiar" if self.copiar else "Mover"
        view.linha(" " + truncar(f"{verbo} {self._o_que()} para:", largura - 2), 'nota')
        msg, erro = self.app.consumir_flash()
        if msg:
            view.linha(" " + msg, 'erro' if erro else 'flash')
        else:
            view.linha(" " + caminho, 'breadcrumb')
        view.barra()
        if self.itens:
            for i, pasta in enumerate(self.itens, start=1):
                view.trechos(linha_item(i, pasta, largura))
        else:
            view.linha(" Nenhuma sub-pasta aqui.", 'vazio')
        view.barra()

    # --- navegacao ---------------------------------------------------------

    def selecionar(self, indice):
        if not (0 <= indice < len(self.itens)):
            self.app.flash("Número fora da lista.", erro=True)
            self.app.rerender()
            return
        pasta = self.itens[indice]

        def entrar():
            self.pasta_id = pasta.id
            self.app.rerender()

        if pasta.trancada:
            self.app.exigir_cofre(entrar)
        else:
            entrar()

    def on_back(self):
        pai = self.app.pai_de(self.pasta_id)
        if pai is None:
            self.app.pop()  # Enter vazio na raiz: desiste
            return
        self.pasta_id = pai.id
        self.app.rerender()

    def on_cancel(self):
        self.app.pop()

    def entrada_invalida(self, texto):
        # o '?' e inerte aqui (menu fixo): o aviso aponta para o que existe
        verbo = "copiar" if self.copiar else "mover"
        self.app.flash(f"Digite o número da pasta, C para {verbo} para cá, "
                       f"/ para a raiz ou ESC para cancelar.", erro=True)
        self.app.rerender()

    def cmd_voltar(self, alvo=None):
        self.on_back()

    def cmd_raiz(self, alvo=None):
        self.pasta_id = self.app.raiz.id
        self.app.rerender()

    def cmd_confirmar(self, alvo=None):
        self.confirmar()

    # --- mover ---------------------------------------------------------------

    def confirmar(self):
        if self.copiar:
            return self._confirmar_copia()
        destino = self.pasta
        origem = self.app.pai_de(self.no.id)   # o lote sai todo da mesma pasta
        if any(tree.criaria_ciclo(no, destino) for no in self.nos):
            self.app.flash("Não dá para mover uma pasta para dentro dela mesma.", erro=True)
            self.app.rerender()
            return

        a_mover = [no for no in self.nos if self.app.pai_de(no.id) is not destino]
        if not a_mover:
            self.app.flash(f"{'Já está' if len(self.nos) == 1 else 'Já estão'} "
                           f"nesta pasta.", erro=True)
            self.app.rerender()
            return
        livres = [no for no in a_mover if tree.homonimo(destino, no.nome) is None]
        conflitos = [no for no in a_mover if no not in livres]

        protege_origem = self.app.pasta_protetora(origem.id)
        protege_destino = self.app.pasta_protetora(destino.id)

        def com_aviso_de_cifra(acao):
            """Sair de uma pasta cifrada deixa o lote em claro: confirma uma vez."""
            if protege_origem is not None and protege_destino is None:
                self.app.push(ConfirmScreen(
                    self.app, f"{self._o_que()} sai da pasta cifrada "
                              f"{protege_origem.nome!r}. Mover?",
                    acao,
                    detalhe="Fora dela, o conteúdo fica em claro no arquivo de dados."))
                return
            acao()

        if not conflitos:
            com_aviso_de_cifra(lambda: self._mover(livres, [], None))
            return
        self._perguntar_conflito(livres, conflitos, com_aviso_de_cifra)

    def _perguntar_conflito(self, livres, conflitos, com_aviso_de_cifra):
        destino = self.pasta
        nomes = ", ".join(repr(no.nome) for no in conflitos[:3])
        if len(conflitos) > 3:
            nomes += f" e mais {len(conflitos) - 3}"
        n_livres, n_conf = len(livres), len(conflitos)
        existentes = [tree.homonimo(destino, no.nome) for no in conflitos]
        fortes = [e for e in existentes if tree.precisa_confirmacao_forte(e)]

        if n_livres:
            so_livres = f"Mover só {'o' if n_livres == 1 else 'os'} {n_livres} sem conflito"
        else:
            so_livres = "Não mover (nada é movido)"
        detalhe = f"Em conflito: {nomes}. ESC cancela: nada é movido."
        if fortes:
            detalhe += (" Substituir apaga " + "; ".join(tree.resumo_delecao(e) for e in fortes)
                        + " (um backup é gravado antes).")

        def escolher(texto):
            if texto == '1':
                if livres:
                    com_aviso_de_cifra(lambda: self._mover(livres, [], None,
                                                           deixados=n_conf))
                else:
                    self.app.flash("Nada foi movido.")
                    self.app.rerender()
            else:
                modo = 'substituir' if texto == '2' else 'renomear'
                com_aviso_de_cifra(lambda: self._mover(livres, conflitos, modo))

        if n_livres + n_conf == 1:
            pergunta = f"Já existe um item chamado {conflitos[0].nome!r} nesta pasta."
            so_livres = "Não mover"
        else:
            pergunta = (f"{n_livres} {'item pode' if n_livres == 1 else 'itens podem'} ser "
                        f"{'movido' if n_livres == 1 else 'movidos'}, {n_conf} em conflito "
                        f"(mesmo nome no destino).")

        self.app.push(PromptScreen(
            self.app, pergunta, escolher,
            validar=lambda t: None if t in ('1', '2', '3') else "Digite 1, 2 ou 3.",
            opcoes=[(1, so_livres),
                    (2, "Substituir: apagar o de mesmo nome no destino" if n_conf == 1
                        else "Substituir: apagar os de mesmo nome no destino"),
                    (3, f"Mover {'o conflitante' if n_conf == 1 else 'os conflitantes'} com outro nome "
                        f"({tree.nome_de_copia(destino, conflitos[0].nome)!r})")],
            detalhe=detalhe,
            contexto=montar_breadcrumb(self.app.caminho_de(destino.id)),
        ))

    def _mover(self, livres, conflitos, modo, deixados=0):
        """Aplica o lote de uma vez: um snapshot e um registro de desfazer.

        modo: None (so os livres), 'substituir' (apaga o homonimo do destino)
        ou 'renomear' (o conflitante chega como 'Nome (cópia)').
        """
        destino = self.pasta
        movidos = livres + conflitos
        origem = self.app.pai_de(movidos[0].id)
        protege_destino = self.app.pasta_protetora(destino.id)
        caminho = montar_breadcrumb(self.app.caminho_de(destino.id))

        self.app.snapshot()
        self.app.registrar_desfazer(selecao.descricao_lote("mover", movidos))
        substituidos = 0
        for no in conflitos:
            existente = tree.homonimo(destino, no.nome)
            if modo == 'substituir' and existente is not None:
                tree.remover(destino, existente)
                substituidos += 1
            elif existente is not None:
                tree.renomear(no, tree.nome_de_copia(destino, no.nome))
        for no in movidos:
            if protege_destino is not None:
                cripto.absorver_em_pasta_cifrada(self.app.cofre, no)
            tree.mover(no, origem, destino)
        self.app.persistir()

        if self.app.atual is self:
            self.app.pop()
        if len(movidos) == 1 and not deixados:
            msg = f"{movidos[0].nome!r} movido para {caminho}."
        else:
            msg = f"{len(movidos)} {'item movido' if len(movidos) == 1 else 'itens movidos'} para {caminho}"
            extras = []
            if substituidos:
                extras.append(f"{substituidos} substituído{'s' if substituidos != 1 else ''}")
            if modo == 'renomear' and conflitos:
                extras.append(f"{len(conflitos)} com outro nome")
            if deixados:
                extras.append(f"{deixados} {'ficou' if deixados == 1 else 'ficaram'} "
                              f"por conflito")
            msg += (" (" + ", ".join(extras) + ")." if extras else ".")
        self.app.flash(msg)
        self.app.rerender()

    # --- copiar --------------------------------------------------------------

    def _confirmar_copia(self):
        destino = self.pasta
        protegidos = [no for no in self.nos if self.app.pasta_protetora(no.id) is not None]
        protege_destino = self.app.pasta_protetora(destino.id)

        def fechar():
            if self.app.atual is self:
                self.app.pop()

        def aplicar():
            self.app.copiar_varios(self.nos, destino, depois=fechar)

        if protegidos and protege_destino is None:
            # a copia fora da pasta cifrada fica em claro no arquivo
            protege_origem = self.app.pasta_protetora(protegidos[0].id)
            self.app.push(ConfirmScreen(
                self.app, f"A cópia de {self._o_que()} fica fora da pasta cifrada "
                          f"{protege_origem.nome!r}. Copiar?",
                aplicar,
                detalhe="Fora dela, o conteúdo da cópia fica em claro no arquivo de dados."))
            return
        aplicar()
