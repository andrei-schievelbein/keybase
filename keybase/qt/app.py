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
        #: o menu de comandos comeca escondido e nao persiste entre sessoes
        self.menu_visivel = False
        self.indice = construir_indice(doc.raiz)
        self._cofre = None
        self._cofre_doc = None
        self._ultima_atividade = time.monotonic()
        #: onde a tela de configuracao le e grava; None = o padrao de paths.py
        self.caminho_config = None
        self._tela_do_flash = None
        self._copia_sensivel = None

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

    def persistir(self):
        """Grava a arvore. Reporta falha na tela, nunca explode em silencio."""
        self.reindexar()
        self._selar_pastas()
        try:
            storage.salvar(self.doc, self.caminho_dados)
        except storage.StorageError as e:
            self.flash(f"Não foi possível salvar: {e}", erro=True)
            self.doc.marcar_sujo()
            return False
        return True

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

    def flash(self, mensagem, erro=False):
        """Mensagem one-shot, consumida no proximo render.

        Aparece NO LUGAR do caminho ('~ / ...') e some sozinha depois de
        interface.tempo_aviso_ms da configuracao, quando o caminho volta - sem
        bloco proprio na tela.
        Truncada porque pode conter o nome de um item, que o usuario controla
        e pode ser bem longo.
        """
        from .layout import truncar
        self._flash = truncar(mensagem, self.view.colunas() - 4)
        self._flash_erro = erro

    def consumir_flash(self):
        msg, erro = self._flash, self._flash_erro
        self._flash = None
        self._flash_erro = False
        if msg:
            self._tela_do_flash = self.atual  # rerender agenda a volta do caminho
        return msg, erro

    def duracao_flash_ms(self):
        """Lida a cada aviso: mudar na configuracao vale ja no proximo."""
        from ..config import DEFAULT_CONFIG
        padrao = DEFAULT_CONFIG['interface']['flash_ms']
        return self.config.get('interface', {}).get('flash_ms', padrao)

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

        tela = self.stack[-1]
        self.view.modo_senha(tela.ENTRADA_SENHA)
        # mesma flag que governa o desenho e o '?'/Ctrl+0: o botao acompanha
        self.view.habilitar_ajuda(tela.MOSTRA_MENU)
        if tela.usa_editor():
            self.view.dica(tela.help_text())
            tela.render()
        else:
            self.view.modo_leitura()
            self.view.limpar()
            # antes de render(): o menu e o primeiro bloco da area de leitura
            tela.desenhar_menu()
            tela.render()
            self.view.ao_topo()
            self.view.dica(tela.help_text())
            if self._tela_do_flash is tela:
                self.janela.agendar_fim_do_flash(self.duracao_flash_ms(), self._fim_do_flash)

    # --- eventos -----------------------------------------------------------

    def submit(self):
        comando = self.view.ler_entrada()
        self.view.limpar_entrada()
        self.registrar_atividade()
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

    def duplicar(self, no, pai):
        """Copia um item na mesma pasta, como 'Nome (cópia)'."""
        def aplicar():
            copia = tree.copia_profunda(no)
            copia.nome = tree.nome_de_copia(pai, no.nome)
            if self.cofre is not None and self.cofre.destravado:
                cripto.selar_copia(self.cofre, copia)
            tree.adicionar(pai, copia)
            self.persistir()
            self.flash(f"{no.nome!r} duplicado como {copia.nome!r}.")
            self.rerender()

        if cripto.precisa_do_cofre(no):
            self.exigir_cofre(aplicar)  # destravar tambem abre a pasta cifrada
        else:
            aplicar()

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
