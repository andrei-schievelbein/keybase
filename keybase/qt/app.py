"""App: pilha de telas, bindings e ciclo de vida.

O despachante inteiro cabe em tres linhas porque cada tela sabe tratar o
proprio input:

    def submit(self):
        comando = self.view.ler_entrada()
        self.view.limpar_entrada()
        self.atual.handle_input(comando)

A pilha guarda TELAS, nao nos: uma pilha de nos nao expressaria "prompt sobre
browser sobre browser", e voltar precisa restaurar o browser anterior com o
filtro que ele tinha, que vive na instancia da tela.
"""

import time

from .. import cripto, storage, tree
from ..model import ID_RAIZ
from ..tree import construir_indice

SENHA_MINIMA = 6
#: quantas acoes o U consegue desfazer em sequencia
LIMITE_DESFAZER = 20
#: titulo dos prompts de senha: diz de cara do que se trata
TITULO_SENHA = "SENHA MESTRA - NOTAS E PASTAS CIFRADAS"


class App:
    def __init__(self, janela, view, doc, caminho_dados, config):
        self.janela = janela
        self.view = view
        self.doc = doc
        self.caminho_dados = caminho_dados
        self.config = config
        self.stack = []
        self._flash = None
        self._flash_erro = False
        self._flash_longo = False
        #: o menu de comandos comeca escondido e nao persiste entre sessoes
        self.menu_visivel = False
        self.indice = construir_indice(doc.raiz)
        self._cofre = None
        self._cofre_doc = None
        self._ultima_atividade = time.monotonic()
        #: onde a tela de configuracao le e grava; None = o padrao de paths.py
        self.caminho_config = None
        self._tela_do_flash = None
        self._flash_mostrado_longo = False
        #: (tela, mensagem, erro) do aviso longo que so sai com ENTER
        #: (tempo_aviso_longo_ms = 0); redesenhado a cada repinte dessa tela
        self._flash_fixo = None
        self._copia_sensivel = None
        #: [(descricao, raiz.to_dict() de antes da acao)] - ver registrar_desfazer
        self._desfazer = []
        self._acao_desfazivel = False
        #: conflito de arquivo esperando a tela de escolha; copia das mudancas
        self._conflito_pendente = False
        self._copia_conflito = None

    # --- arvore ------------------------------------------------------------

    @property
    def raiz(self):
        return self.doc.raiz

    def reindexar(self):
        self.indice = construir_indice(self.doc.raiz)

    def no(self, node_id):
        """Nó pelo id, ou None se foi removido por baixo da tela."""
        entrada = self.indice.get(node_id)
        return entrada[0] if entrada else None

    def pai_de(self, node_id):
        entrada = self.indice.get(node_id)
        return entrada[1] if entrada else None

    def caminho_de(self, node_id):
        from ..tree import caminho
        no = self.no(node_id)
        return caminho(self.indice, no) if no else []

    def garantir_doc(self):
        """Poe a nota "Keybase Doc" na raiz, so na primeira vez que o app abre.

        A marca fica no estado (keybase_estado.json): apagada, a nota nao volta.
        Se ja existe algo com esse nome na raiz (outro computador sincronizado
        criou, ou o usuario), so marca.
        """
        from .. import doc as mod_doc
        if self.config.get('doc_criada') or self.doc.somente_leitura:
            return
        if tree.nome_disponivel(self.raiz, mod_doc.NOME_DOC):
            tree.adicionar(self.raiz, tree.novo_file(mod_doc.NOME_DOC, mod_doc.CONTEUDO_DOC))
            self.persistir()
        self.config['doc_criada'] = True

    def persistir(self):
        """Grava a arvore. Reporta falha na tela, nunca explode em silencio."""
        self.reindexar()
        self._selar_pastas()
        desfazivel, self._acao_desfazivel = self._acao_desfazivel, False
        try:
            gravou = storage.salvar(self.doc, self.caminho_dados)
        except storage.ConflitoError:
            self._registrar_conflito()
            return False
        except storage.StorageError as e:
            self.flash(f"Não foi possível salvar: {e}", erro=True)
            self.doc.marcar_sujo()
            return False
        if gravou and not desfazivel:
            # algo mudou fora da pilha (edicao, cifra, criacao): desfazer agora
            # restauraria um estado velho por cima dessa mudanca, em silencio
            self._desfazer.clear()
        return True

    # --- conflito com outro computador ---------------------------------------

    def _registrar_conflito(self):
        """O arquivo mudou por fora. Guarda o daqui ao lado e agenda a escolha.

        A tela nao e empilhada aqui: persistir() e chamado no meio de fluxos
        que ainda vao dar pop (o editor, ao salvar). O proximo rerender a poe
        no topo, depois de tudo assentar.
        """
        self.doc.marcar_sujo()
        if self._copia_conflito is None:
            try:
                self._copia_conflito = storage.salvar_copia_de_conflito(
                    self.doc, self.caminho_dados)
            except (storage.StorageError, OSError):
                self._copia_conflito = None
        self._conflito_pendente = True

    def _tela_de_conflito(self):
        from .screens.prompt import PromptScreen
        copia = self._copia_conflito
        tela = PromptScreen(
            self, "O arquivo de dados foi alterado fora deste KeyBase.",
            lambda t: self._recarregar_do_disco() if t == '1' else self._gravar_por_cima(),
            validar=lambda t: None if t in ('1', '2') else "Digite 1 ou 2.",
            contexto="CONFLITO - OUTRO COMPUTADOR GRAVOU OS DADOS",
            detalhe=(f"Suas mudanças daqui estão guardadas em {copia.name}." if copia
                     else "Provavelmente outro computador, via pasta sincronizada."),
            opcoes=[(1, "Recarregar o do disco (as mudanças daqui ficam só na cópia)"),
                    (2, "Gravar o daqui por cima (o de lá fica no backup .bak)")],
        )
        tela.conflito = True
        return tela

    def _recarregar_do_disco(self):
        try:
            doc = storage.carregar(self.caminho_dados)
        except storage.StorageError as e:
            self.flash(f"Não foi possível recarregar: {e}", erro=True)
            self.rerender()
            return
        self.doc = doc  # o cofre, amarrado ao documento, recomeca trancado
        self._desfazer.clear()
        self._copia_conflito = None
        self.reindexar()
        self.flash("Recarregado do disco.")
        self.rerender()

    def _gravar_por_cima(self):
        self._selar_pastas()
        try:
            storage.salvar(self.doc, self.caminho_dados, forcar=True)
        except storage.StorageError as e:
            self.flash(f"Não foi possível gravar: {e}", erro=True)
        else:
            self._copia_conflito = None
            self.flash("Gravado por cima. A versão de lá ficou no backup.")
        self.rerender()

    # --- desfazer -----------------------------------------------------------

    def registrar_desfazer(self, descricao):
        """Chamada logo ANTES de uma acao desfazivel (apagar, mover, renomear,
        duplicar, decifrar). Guarda a arvore como estava.

        Guarda o to_dict, que numa nota ou pasta cifrada so tem o blob: a pilha
        nao junta texto claro na memoria. O proximo persistir() e o da acao.
        """
        self._selar_pastas()
        self._desfazer.append((descricao, self.raiz.to_dict()))
        del self._desfazer[:-LIMITE_DESFAZER]
        self._acao_desfazivel = True

    def cancelar_desfazer(self):
        """A acao registrada nao aconteceu (falhou): tira o registro da pilha."""
        if self._acao_desfazivel and self._desfazer:
            self._desfazer.pop()
        self._acao_desfazivel = False

    @property
    def pode_desfazer(self):
        return bool(self._desfazer)

    def desfazer(self):
        from ..model import node_from_dict
        if not self._desfazer:
            self.flash("Nada para desfazer.")
            self.rerender()
            return
        descricao, raiz = self._desfazer.pop()
        self.snapshot()
        self.doc.raiz = node_from_dict(raiz)
        if self.cofre_destravado:
            cripto.destravar_arvore(self.raiz, self.cofre)  # o blob volta aberto
        self._acao_desfazivel = True  # restaurar nao zera o resto da pilha
        self.persistir()
        self.flash(f"Desfeito: {descricao}.")
        self.rerender()

    def snapshot(self):
        """Forca backup antes de uma operacao destrutiva."""
        try:
            storage.snapshot(self.doc, self.caminho_dados)
        except OSError:
            pass

    # --- cofre -------------------------------------------------------------

    @property
    def cofre(self):
        """Cofre do documento atual, ou None se nenhuma nota foi cifrada ainda.

        Amarrado ao documento, e nao guardado de vez: a tela de recuperacao
        troca self.doc, e um cofre de outro documento destravaria a chave errada.
        """
        if self.doc.cofre is None:
            return None
        if self._cofre is None or self._cofre_doc is not self.doc:
            self._cofre = cripto.Cofre.from_dict(self.doc.cofre)
            self._cofre_doc = self.doc
        return self._cofre

    @property
    def cofre_destravado(self):
        return self.cofre is not None and self.cofre.destravado

    def _selar_pastas(self):
        """Recifra as pastas cifradas abertas que mudaram. Antes de todo save."""
        if self.cofre_destravado:
            cripto.selar_pastas(self.raiz, self.cofre)

    def pasta_protetora(self, node_id):
        """A pasta cifrada que ja protege este no (ele mesmo incluso), ou None."""
        return cripto.pasta_cifrada_na_cadeia(self.caminho_de(node_id))

    def garantir_cofre(self, acao):
        """Roda acao() com um cofre existente; na primeira vez, cria o cofre."""
        if self.cofre is None:
            self._criar_cofre(acao)
        else:
            acao()

    def exigir_cofre(self, acao):
        """Roda acao() com o cofre destravado: cria, pede a senha ou vai direto."""
        if self.cofre is None:
            self._criar_cofre(acao)
        elif self.cofre.destravado:
            acao()
        else:
            self._pedir_senha(acao)

    def _pedir_senha(self, acao):
        from .screens.prompt import PromptScreen

        def conferir(senha):
            try:
                self.cofre.destravar(senha)
            except cripto.SenhaIncorretaError:
                return "Senha incorreta."
            return None

        def destravado(_senha):
            try:
                cripto.destravar_arvore(self.raiz, self.cofre)
            except cripto.CriptoError as e:
                self.cofre.trancar()
                cripto.trancar_arvore(self.raiz)
                self.reindexar()
                self.flash(f"Não foi possível abrir os itens cifrados: {e}", erro=True)
                self.rerender()
                return
            self.reindexar()  # as pastas cifradas agora tem filhos na memoria
            self.registrar_atividade()
            acao()

        # o rodape do prompt ja diz como confirmar e cancelar: sem repetir aqui
        self.push(PromptScreen(
            self, "Digite a senha mestra:", destravado,
            validar=conferir, senha=True, contexto=TITULO_SENHA,
            detalhe="Destranca todas as notas e pastas cifradas."))

    def _criar_cofre(self, acao):
        from .screens.prompt import ConfirmScreen, PromptScreen

        def pedir_senha():
            self.push(PromptScreen(
                self, f"Crie a senha mestra (mínimo {SENHA_MINIMA} caracteres):",
                repetir, validar=validar, senha=True, contexto=TITULO_SENHA,
                detalhe="Ela protege todas as notas e pastas cifradas."))

        def validar(senha):
            if len(senha) < SENHA_MINIMA:
                return f"A senha precisa de pelo menos {SENHA_MINIMA} caracteres."
            return None

        def repetir(senha):
            def conferir(outra):
                return None if outra == senha else "As senhas não conferem."

            def criar(_outra):
                self._cofre = cripto.Cofre.criar(senha)
                self._cofre_doc = self.doc
                self.doc.cofre = self._cofre.to_dict()
                self.registrar_atividade()
                acao()

            self.push(PromptScreen(self, "Repita a senha mestra:", criar,
                                   validar=conferir, senha=True, contexto=TITULO_SENHA,
                                   detalhe="Para confirmar que foi digitada certo."))

        self.push(ConfirmScreen(
            self, "Criar a senha mestra das notas e pastas cifradas?", pedir_senha,
            detalhe="Não existe recuperação: sem a senha, as notas cifradas "
                    "ficam ilegíveis para sempre."))

    def trocar_senha(self):
        """S: senha atual -> nova -> repetir. So o envelope da chave muda."""
        from .screens.prompt import PromptScreen
        if self.cofre is None:
            self.flash("Ainda não há senha mestra. Use K para cifrar uma nota ou pasta.")
            self.rerender()
            return

        def conferir_atual(senha):
            return None if self.cofre.conferir(senha) else "Senha incorreta."

        def pedir_nova(atual):
            def validar(nova):
                if len(nova) < SENHA_MINIMA:
                    return f"A senha precisa de pelo menos {SENHA_MINIMA} caracteres."
                if nova == atual:
                    return "A senha nova é igual à atual."
                return None

            def repetir(nova):
                def aplicar(_outra):
                    self.cofre.trocar_senha(atual, nova)
                    self.doc.cofre = self.cofre.to_dict()
                    if self.persistir():
                        self.flash("Senha mestra trocada.")
                    self.rerender()

                self.push(PromptScreen(
                    self, "Repita a senha nova:", aplicar, senha=True,
                    contexto=TITULO_SENHA,
                    validar=lambda outra: None if outra == nova
                    else "As senhas não conferem."))

            self.push(PromptScreen(
                self, f"Senha nova (mínimo {SENHA_MINIMA} caracteres):", repetir,
                validar=validar, senha=True, contexto=TITULO_SENHA,
                detalhe="Os backups antigos continuam abrindo com a senha antiga."))

        self.push(PromptScreen(self, "Senha atual:", pedir_nova, validar=conferir_atual,
                               senha=True, contexto=TITULO_SENHA,
                               detalhe="Para trocar a senha mestra."))

    def trancar(self, automatico=False):
        """Tranca o cofre e esquece o texto claro. False se nao pode agora."""
        if not self.cofre_destravado:
            return False
        if any(tela.usa_editor() for tela in self.stack):
            # texto nao salvo e sagrado: tranca quando sair do editor (inclusive
            # com a ajuda completa aberta por cima dele)
            return False
        # sela e fecha as pastas com o cofre ainda aberto, grava, e so entao
        # esquece a chave: o blob gravado e a unica copia do que estava dentro
        cripto.trancar_arvore(self.raiz, self.cofre)
        self.persistir()
        self.cofre.trancar()
        self.flash("Itens cifrados trancados por inatividade." if automatico
                   else "Itens cifrados trancados.")
        self.rerender()
        return True

    def alternar_tranca(self):
        """T: tranca se esta aberto; se esta trancado, pede a senha e destranca."""
        if self.cofre is None:
            self.flash("Ainda não há nada cifrado. Use K para cifrar uma nota ou pasta.")
            self.rerender()
        elif self.cofre.destravado:
            if not self.trancar():
                self.flash("Saia do editor antes de trancar.", erro=True)
                self.rerender()
        else:
            def destrancado():
                self.flash("Itens cifrados destrancados.")
                self.rerender()
            self._pedir_senha(destrancado)

    def registrar_atividade(self):
        self._ultima_atividade = time.monotonic()

    def verificar_auto_trancar(self, agora=None):
        """Chamada por um timer da janela. Tranca apos N minutos sem uso."""
        if not self.cofre_destravado:
            return False
        minutos = self.config.get('cofre', {}).get('auto_lock_min', 10)
        if not isinstance(minutos, (int, float)) or minutos <= 0:
            return False
        agora = time.monotonic() if agora is None else agora
        if agora - self._ultima_atividade < minutos * 60:
            return False
        return self.trancar(automatico=True)

    def cifrar_notas(self, notas):
        """Cifra as notas (cofre ja destravado), grava e oferece sanear backups."""
        for nota in notas:
            cripto.cifrar_nota(self.cofre, nota)
        self.persistir()
        if len(notas) == 1:
            self.flash(f"Nota {notas[0].nome!r} cifrada.")
        else:
            self.flash(f"{len(notas)} notas cifradas.")
        self.oferecer_saneamento([nota.id for nota in notas])

    def cifrar_pasta_inteira(self, pasta):
        """Cifra nomes, sub-pastas e notas de uma pasta (cofre ja destravado)."""
        cripto.cifrar_pasta(self.cofre, pasta)
        self.persistir()
        self.flash(f"Pasta {pasta.nome!r} cifrada inteira.")
        self.oferecer_saneamento([pasta.id])

    def decifrar_pasta(self, pasta):
        """Volta uma pasta cifrada (aberta) a ser comum."""
        self.registrar_desfazer(f"decifrar a pasta {pasta.nome!r}")
        cripto.decifrar_pasta(pasta)
        self.persistir()
        self.flash(f"Pasta {pasta.nome!r} decifrada.")
        self.rerender()

    def oferecer_saneamento(self, ids):
        """Os backups ainda tem essas notas em claro: pergunta se cifra as copias."""
        from .screens.prompt import ConfirmScreen
        try:
            sujos = storage.backups_com_texto_claro(self.caminho_dados, ids)
        except OSError:
            sujos = []
        if not sujos:
            self.rerender()
            return

        def sanear():
            try:
                n = storage.sanear_backups(self.caminho_dados, self.cofre, ids)
            except (storage.StorageError, OSError) as e:
                self.flash(f"Não foi possível regravar os backups: {e}", erro=True)
            else:
                self.flash(f"{n} backup{'s' if n != 1 else ''} regravado"
                           f"{'s' if n != 1 else ''} com o conteúdo cifrado.")
            self.rerender()

        from ..model import Folder
        if len(ids) != 1:
            alvo = "destas notas"
        else:
            alvo = "desta pasta" if isinstance(self.no(ids[0]), Folder) else "desta nota"
        self.push(ConfirmScreen(
            self, f"Cifrar também as cópias de backup {alvo}?",
            sanear,
            detalhe="O histórico é preservado: as cópias só passam a exigir a senha."))

    # --- pilha -------------------------------------------------------------

    @property
    def atual(self):
        return self.stack[-1] if self.stack else None

    def push(self, tela):
        self.stack.append(tela)
        self.rerender()

    def pop(self, n=1):
        for _ in range(n):
            if len(self.stack) > 1:
                self.stack.pop()
        self.rerender()

    def replace(self, tela):
        if self.stack:
            self.stack.pop()
        self.stack.append(tela)
        self.rerender()

    def reset(self, telas):
        self.stack = list(telas)
        self.rerender()

    def go_root(self):
        from .screens.browser import BrowserScreen
        self.reset([BrowserScreen(self, ID_RAIZ)])

    # --- render ------------------------------------------------------------

    def flash(self, mensagem, erro=False, longo=False):
        """Mensagem one-shot, consumida no proximo render.

        Aparece NO LUGAR do caminho ('~ / ...') e some sozinha depois de
        interface.tempo_aviso_ms da configuracao, quando o caminho volta - sem
        bloco proprio na tela.
        Truncada porque pode conter o nome de um item, que o usuario controla
        e pode ser bem longo.

        `longo`: aviso com algo para ler com calma (um endereco, uma instrucao).
        Fica interface.tempo_aviso_longo_ms e pode quebrar em ate 3 linhas.
        """
        from .layout import truncar
        linhas = 3 if longo else 1
        self._flash = truncar(mensagem, linhas * (self.view.colunas() - 4))
        self._flash_erro = erro
        self._flash_longo = longo

    def consumir_flash(self):
        msg, erro = self._flash, self._flash_erro
        self._flash = None
        self._flash_erro = False
        if msg:
            self._tela_do_flash = self.atual  # rerender agenda a volta do caminho
            self._flash_mostrado_longo = self._flash_longo
        self._flash_longo = False
        return msg, erro

    def duracao_flash_ms(self, longo=False):
        """Lida a cada aviso: mudar na configuracao vale ja no proximo."""
        from ..config import DEFAULT_CONFIG
        chave = 'flash_longo_ms' if longo else 'flash_ms'
        padrao = DEFAULT_CONFIG['interface'][chave]
        return self.config.get('interface', {}).get(chave, padrao)

    def _fim_do_flash(self):
        """O tempo do aviso acabou: repinta para o caminho voltar."""
        tela, self._tela_do_flash = self._tela_do_flash, None
        # so se a tela que mostrou o aviso ainda e a do topo, e sem editor
        # (um rerender nao pode passar perto de texto nao salvo)
        if tela is None or tela is not self.atual or tela.usa_editor():
            return
        if self._flash is not None:
            return  # outro aviso ja esta a caminho, com o proprio tempo
        rolagem = self.view.posicao_rolagem()
        self.rerender()
        self.view.rolar_para(rolagem)  # o caminho volta sem perder o lugar na lista

    def rerender(self):
        """Descarta telas cujo no sumiu, recarrega e repinta a do topo."""
        while self.stack:
            tela = self.stack[-1]
            tela.on_enter()
            if getattr(tela, 'descartada', False) and len(self.stack) > 1:
                self.stack.pop()
                continue
            break

        if not self.stack:
            self.go_root()
            return

        if self._conflito_pendente and not getattr(self.stack[-1], 'conflito', False):
            self._conflito_pendente = False
            self.stack.append(self._tela_de_conflito())

        tela = self.stack[-1]
        self.view.modo_senha(tela.ENTRADA_SENHA)
        # mesma flag que governa o desenho e o '?'/Ctrl+0: o botao acompanha
        self.view.habilitar_ajuda(tela.MOSTRA_MENU)
        fixo, self._flash_fixo = self._flash_fixo, None
        if fixo and fixo[0] is tela and self._flash is None:
            # repinte da mesma tela (reajuste da janela, filtro...): o aviso volta
            _, self._flash, self._flash_erro = fixo
            self._flash_longo = True
        if tela.usa_editor():
            self.view.dica(tela.help_text())
            tela.render()
        else:
            self.view.modo_leitura()
            self.view.limpar()
            pendente = self._flash, self._flash_erro
            # antes de render(): o menu e o primeiro bloco da area de leitura
            tela.desenhar_menu()
            tela.render()
            self.view.ao_topo()
            self.view.dica(tela.help_text())
            if self._tela_do_flash is tela:
                duracao = self.duracao_flash_ms(self._flash_mostrado_longo)
                if duracao:
                    self.janela.agendar_fim_do_flash(duracao, self._fim_do_flash)
                elif pendente[0] is not None and self._flash is None:
                    # tempo 0 (so o longo aceita): fica ate o ENTER, ver submit
                    self.janela.cancelar_fim_do_flash()
                    self._tela_do_flash = None
                    self._flash_fixo = (tela,) + pendente

    # --- eventos -----------------------------------------------------------

    def submit(self):
        comando = self.view.ler_entrada()
        self.view.limpar_entrada()
        self.registrar_atividade()
        if not comando.strip() and self._flash_fixo is not None \
                and self._flash_fixo[0] is self.atual:
            # ENTER vazio so tira o aviso fixo: nao volta nem abre nada
            self._flash_fixo = None
            rolagem = self.view.posicao_rolagem()
            self.rerender()
            self.view.rolar_para(rolagem)
            return
        if self.atual:
            self.atual.handle_input(comando)

    def save(self):
        """Ctrl+S vai direto ao metodo da tela ativa.

        Substitui o hack de injetar a sentinela 'CTRL_S' no campo de entrada,
        que truncava qualquer nota terminada nessa palavra.
        """
        self.registrar_atividade()
        if self.atual:
            self.atual.on_save()

    def ao_digitar(self, texto):
        """Cada tecla na barra (textEdited: so o usuario, nunca o clear do app).

        A tela decide se o texto muda a lista (filtro ao vivo do browser); a
        barra fica como esta, com o cursor no lugar.
        """
        reagir = getattr(self.atual, 'ao_digitar', None)
        if reagir is not None and reagir(texto):
            self.rerender()

    def cancel(self):
        if self.atual:
            self.atual.on_cancel()

    def modo(self, qual):
        """Ctrl+1/2/3. No-op na classe base, entao e inerte fora do editor."""
        if self.atual:
            self.atual.on_modo(qual)

    def ciclar_modo(self):
        """Ctrl+E. Mesma logica do modo()."""
        if self.atual:
            self.atual.on_ciclar_modo()

    def _copiar_para(self, no, destino, nome, descricao):
        """Poe uma copia de `no` em `destino`, com o nome dado. Desfazivel.

        Destino sob uma pasta cifrada: a copia fica sob a protecao dela (o que
        era cifrado por si volta a ser comum). Fora de uma: o que era cifrado e
        recifrado com os ids novos. Quem chama garantiu o cofre aberto quando
        ha algo cifrado (cripto.precisa_do_cofre).
        """
        copia = tree.copia_profunda(no)
        copia.nome = nome
        self.registrar_desfazer(descricao)
        if self.pasta_protetora(destino.id) is not None:
            cripto.absorver_em_pasta_cifrada(self.cofre, copia)
        elif self.cofre_destravado:
            cripto.selar_copia(self.cofre, copia)
        tree.adicionar(destino, copia)
        self.persistir()
        return copia

    def _com_cofre_se_preciso(self, no, acao):
        if cripto.precisa_do_cofre(no):
            self.exigir_cofre(acao)  # destravar tambem abre a pasta cifrada
        else:
            acao()

    def duplicar(self, no, pai):
        """Z: copia na mesma pasta, como 'Nome (cópia)'."""
        def aplicar():
            copia = self._copiar_para(no, pai, tree.nome_de_copia(pai, no.nome),
                                      f"duplicar {no.nome!r}")
            self.flash(f"{no.nome!r} duplicado como {copia.nome!r}.")
            self.rerender()

        self._com_cofre_se_preciso(no, aplicar)

    def copiar_para(self, no, destino, depois=None):
        """Y na lista: copia para outra pasta, mantendo o original.

        Mesmo nome se estiver livre no destino; senao, 'Nome (cópia)'.
        """
        from .layout import montar_breadcrumb

        def aplicar():
            nome = (no.nome if tree.nome_disponivel(destino, no.nome)
                    else tree.nome_de_copia(destino, no.nome))
            copia = self._copiar_para(no, destino, nome, f"copiar {no.nome!r}")
            if depois is not None:
                depois()
            caminho = montar_breadcrumb(self.caminho_de(destino.id))
            extra = f" como {copia.nome!r}" if copia.nome != no.nome else ""
            self.flash(f"{no.nome!r} copiado para {caminho}{extra}.")
            self.rerender()

        self._com_cofre_se_preciso(no, aplicar)

    # --- favoritos, recentes e abrir por referencia -------------------------

    LIMITE_RECENTES = 10

    def recentes(self):
        return list(self.config.get('recentes', []))

    def registrar_recente(self, node_id):
        lista = [i for i in self.config.get('recentes', []) if i != node_id]
        self.config['recentes'] = ([node_id] + lista)[:self.LIMITE_RECENTES]

    def alternar_favorito(self, no):
        no.favorito = not no.favorito
        self.persistir()
        self.flash(f"{no.nome!r} marcado como favorito." if no.favorito
                   else f"{no.nome!r} saiu dos favoritos.")
        self.rerender()

    def abrir_no(self, no):
        """Abre um no de qualquer lugar (favoritos, links), com a pilha do
        caminho real por baixo - voltar percorre a arvore de verdade."""
        from ..model import File
        from .screens.browser import BrowserScreen
        from .screens.viewer import ViewerScreen
        cadeia = self.caminho_de(no.id)
        pilha = [BrowserScreen(self, a.id) for a in cadeia[:-1]]
        pilha.append(ViewerScreen(self, no.id) if isinstance(no, File)
                     else BrowserScreen(self, no.id))
        if isinstance(no, File) and no.conteudo is None:
            self.exigir_cofre(lambda: self.reset(pilha))
        else:
            self.reset(pilha)

    def abrir_link(self, url):
        """Clique num link do viewer: [[nota]] navega; http(s) abre no navegador."""
        from urllib.parse import unquote

        from .. import links
        from .render.pipeline import ESQUEMA_LINK
        from .screens.prompt import PromptScreen

        if url.startswith(('http://', 'https://')):
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl(url))
            return
        if not url.startswith(ESQUEMA_LINK):
            return
        alvo = unquote(url[len(ESQUEMA_LINK):])
        notas = links.resolver(self.raiz, alvo)
        if not notas:
            self.flash(f"Link quebrado: [[{alvo}]] não aponta para nenhuma nota.", erro=True)
            self.rerender()
            return
        if len(notas) == 1:
            self.abrir_no(notas[0])
            return

        def caminho(nota):
            return tree.breadcrumb(self.caminho_de(nota.id), " / ")

        self.push(PromptScreen(
            self, f"Há {len(notas)} notas chamadas {alvo!r}. Qual abrir?",
            lambda t: self.abrir_no(notas[int(t) - 1]),
            validar=lambda t: None if t.isdigit() and 1 <= int(t) <= len(notas)
            else f"Digite um número de 1 a {len(notas)}.",
            opcoes=[(i, caminho(n)) for i, n in enumerate(notas, start=1)],
        ))

    # --- exportar -----------------------------------------------------------

    #: onde a exportacao cria a pasta; None = Downloads (ou a pasta do usuario)
    pasta_exportacao = None

    def _onde_exportar(self):
        from pathlib import Path
        if self.pasta_exportacao is not None:
            return Path(self.pasta_exportacao)
        downloads = Path.home() / 'Downloads'
        return downloads if downloads.is_dir() else Path.home()

    def exportar(self, pasta):
        """W: a pasta (ou a raiz) como arquivos .md. Pergunta sobre os cifrados."""
        from .screens.prompt import ConfirmScreen, PromptScreen

        def executar(incluir):
            from .. import exportar as mod_exportar
            destino = mod_exportar.pasta_de_saida(self._onde_exportar())
            try:
                r = mod_exportar.exportar(pasta, destino, incluir_cifrados=incluir)
            except OSError as e:
                self.flash(f"Não foi possível exportar: {e}", erro=True)
                self.rerender()
                return
            onde = f"{r.pasta.parent.name}/{r.pasta.name}"
            puladas = f", {len(r.pulados)} cifradas puladas" if r.pulados else ""
            aviso = f"{r.notas} notas exportadas{puladas}: {onde}"
            self.flash(aviso, longo=True)
            self.rerender()

        def em_claro():
            self.exigir_cofre(lambda: executar(True))

        if self.pasta_protetora(pasta.id) is not None:
            # tudo aqui e cifrado: pular seria exportar nada
            self.push(ConfirmScreen(
                self, "Exportar EM CLARO o conteúdo da pasta cifrada?", em_claro,
                detalhe="Os arquivos .md não têm proteção nenhuma."))
            return
        if not (pasta.trancada or cripto.tem_cifra(pasta)):
            executar(False)
            return
        self.push(PromptScreen(
            self, "Há itens cifrados aqui. O que fazer com eles?",
            lambda t: executar(False) if t == '1' else em_claro(),
            validar=lambda t: None if t in ('1', '2') else "Digite 1 ou 2.",
            opcoes=[(1, "Pular os cifrados"),
                    (2, "Incluir em claro (pede a senha; os .md não têm proteção)")],
        ))

    # --- copiar -------------------------------------------------------------

    def item_sensivel(self, no):
        """Cifrado por si ou por uma pasta cifrada acima: copia com limpeza."""
        return bool(getattr(no, 'cifrado', False) or self.pasta_protetora(no.id))

    def copiar(self, texto, descricao, sensivel=False):
        """Copia para a area de transferencia e avisa. Sensivel = limpa depois.

        A limpeza so apaga se a area ainda tiver o que foi copiado: se o
        usuario copiou outra coisa no meio tempo, ela e dele.
        """
        self.view.copiar(texto)
        self._copia_sensivel = texto if sensivel else None
        segundos = self.config.get('cofre', {}).get('clip_seg', 20)
        aviso = f"Copiado: {descricao}."
        if sensivel and segundos:
            aviso = f"Copiado: {descricao} (limpa em {segundos} s)."
            self.janela.agendar_limpeza_copia(segundos * 1000, self.limpar_copia_sensivel)
        self.flash(aviso)
        self.rerender()

    def limpar_copia_sensivel(self):
        if self._copia_sensivel is not None and self.view.texto_copiado() == self._copia_sensivel:
            self.view.limpar_copia()
        self._copia_sensivel = None

    def aplicar_config(self, usuario):
        """Aplica na hora o que a configuracao salva mudou. Devolve o que mudou.

        Tema, altura da ajuda e auto-trancar valem ja (o auto-trancar e lido a
        cada checagem). Fontes so ao reabrir: recriar e remedir a fonte de todo
        widget com a janela aberta nao compensa.
        """
        from ..config import aplicar_no_config
        mudou = aplicar_no_config(self.config, usuario)
        if 'theme' in mudou:
            self.janela.aplicar_tema(self.config['theme'])
        if 'interface' in mudou:
            self.view.ajuda.setMinimumHeight(self.config['interface']['help_area_height'])
        return mudou

    def seta(self, delta):
        """Seta para cima/baixo na barra. So as telas de lista respondem."""
        if self.atual:
            self.atual.on_seta(delta)

    def alternar_menu(self):
        """Ctrl+0. Mesma logica do modo(): inerte onde a tela nao implementa."""
        if self.atual:
            self.atual.on_ajuda()

    def sair(self):
        from ..config import salvar_estado
        try:
            self._selar_pastas()
        except cripto.CriptoError:
            pass  # salvar_se_sujo nunca levanta; o arquivo fica como estava
        storage.salvar_se_sujo(self.doc, self.caminho_dados)
        self.limpar_copia_sensivel()  # nada cifrado fica na area ao fechar
        salvar_estado(self.config, self.janela.geometria_texto())
        self.janela.encerrar()

    def ao_fechar(self):
        self.sair()
