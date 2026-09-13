"""TerminalView: os widgets da janela e as duas modalidades de exibicao.

Quatro widgets, de cima para baixo:

    entrada   CTkEntry     sempre visivel; UNICO input de texto de uma linha
    ajuda     CTkTextbox   barra de dica; pack/pack_forget sob demanda
    out       CTkTextbox   leitura, state="disabled"   \\  XOR: so um empacotado
    edit      CTkTextbox   edicao de markdown cru      /

Na versao anterior um unico widget acumulava output, viewer e editor ao mesmo
tempo. Disso vinham tres problemas: o usuario conseguia digitar por cima da
listagem; as tags de markdown continuavam ativas quando o widget virava editor;
e, como o foco ia para o mesmo widget que recebia o Enter, foi preciso um hack
de sentinelas ('CTRL_S' injetado no campo de entrada) que truncava qualquer
nota terminada nessa palavra.
"""

import customtkinter as ctk

from .markdown_render import configurar_tags, render_markdown
from .theme import cores_interface, cores_markdown, cores_tokens

LARGURA_COLUNAS = 78


class TerminalView:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.tema = config['theme']

        self.cores_md = cores_markdown(self.tema)
        self.cores_tk = cores_tokens(self.tema)
        self.cores_ui = cores_interface(self.tema)

        self._criar_fontes()
        self._criar_widgets()
        self.modo_leitura()

    # --- construcao --------------------------------------------------------

    def _criar_fontes(self):
        fontes = self.config['fonts']

        def fonte(tamanho):
            try:
                return ctk.CTkFont(family=fontes['family'], size=tamanho)
            except Exception:
                return ctk.CTkFont(family=fontes['fallback'], size=tamanho)

        self.fonte_input = fonte(fontes['input_size'])
        self.fonte_output = fonte(fontes['output_size'])
        self.fonte_help = fonte(fontes['help_size'])

    def _criar_widgets(self):
        self.entrada = ctk.CTkEntry(self.root, width=800, font=self.fonte_input)
        self.entrada.pack(pady=10, fill="x", padx=10)

        self.ajuda = ctk.CTkTextbox(
            self.root,
            width=800,
            height=self.config['interface']['help_area_height'],
            font=self.fonte_help,
            fg_color=self.cores_ui['help_bg'],
            text_color=self.cores_ui['help_fg'],
        )
        # sem pack aqui: a barra so aparece quando ha dica

        self.out = ctk.CTkTextbox(self.root, width=800, height=500,
                                  font=self.fonte_output)
        self.edit = ctk.CTkTextbox(self.root, width=800, height=500,
                                   font=self.fonte_output, undo=True)

        self._configurar_tags_ui()
        configurar_tags(self.out, self.cores_md)

    def _configurar_tags_ui(self):
        c = self.cores_ui
        self.out.tag_config('breadcrumb', foreground=c['breadcrumb'], spacing1=4, spacing3=4)
        self.out.tag_config('separador', foreground=c['separador'])
        self.out.tag_config('numero', foreground=c['numero'])
        self.out.tag_config('pasta', foreground=c['pasta'])
        self.out.tag_config('nota', foreground=c['nota'])
        self.out.tag_config('contador', foreground=c['contador'])
        self.out.tag_config('dica', foreground=c['dica'], spacing1=4)
        self.out.tag_config('flash', foreground=c['flash'], spacing1=4)
        self.out.tag_config('erro', foreground=c['erro'], spacing1=4)
        self.out.tag_config('vazio', foreground=c['vazio'], spacing1=6, spacing3=6)

    # --- modos -------------------------------------------------------------

    def modo_leitura(self):
        """Mostra `out`, esconde `edit`, foco no campo de entrada."""
        self.edit.pack_forget()
        if not self.out.winfo_manager():
            self.out.pack(pady=5, fill="both", expand=True, padx=10)
        self.entrada.configure(state="normal")
        self.entrada.focus_set()

    def modo_edicao(self, texto):
        """Mostra `edit` com o markdown cru, foco nele."""
        self.out.pack_forget()
        if not self.edit.winfo_manager():
            self.edit.pack(pady=5, fill="both", expand=True, padx=10)
        self.edit.configure(state="normal")
        self.edit.delete("1.0", "end")
        self.edit.insert("1.0", texto)
        self.edit.edit_reset()
        self.edit.mark_set("insert", "1.0")
        self.edit.see("1.0")
        self.edit.focus_set()

    def texto_editor(self):
        """Conteudo cru do editor, sem nenhum tratamento de sentinela."""
        return self.edit.get("1.0", "end-1c")

    # --- escrita na area de leitura ---------------------------------------

    def limpar(self):
        self._com_escrita(lambda: self.out.delete("1.0", "end"))

    def linha(self, texto="", tag=None):
        def escrever():
            if tag:
                self.out.insert("end", texto + "\n", tag)
            else:
                self.out.insert("end", texto + "\n")
        self._com_escrita(escrever)

    def trechos(self, partes):
        """Escreve uma linha composta de (texto, tag) e quebra no fim."""
        def escrever():
            for texto, tag in partes:
                if tag:
                    self.out.insert("end", texto, tag)
                else:
                    self.out.insert("end", texto)
            self.out.insert("end", "\n")
        self._com_escrita(escrever)

    def separador(self, largura=LARGURA_COLUNAS):
        self.linha("─" * largura, 'separador')

    def markdown(self, texto):
        self._com_escrita(
            lambda: render_markdown(self.out, texto, self.cores_md, self.cores_tk)
        )

    def ao_topo(self):
        self.out.see("1.0")

    def _com_escrita(self, acao):
        """`out` fica disabled; so libera durante a escrita.

        E o que impede o usuario de digitar por cima da listagem renderizada.
        """
        self.out.configure(state="normal")
        try:
            acao()
        finally:
            self.out.configure(state="disabled")

    # --- barra de ajuda ----------------------------------------------------

    def dica(self, texto):
        """Mostra a barra de ajuda; None ou vazio a esconde."""
        if not texto:
            self.ajuda.delete("1.0", "end")
            self.ajuda.pack_forget()
            return
        self.ajuda.delete("1.0", "end")
        self.ajuda.insert("1.0", texto)
        self.ajuda.pack(after=self.entrada, pady=5, fill="x", padx=10)

    # --- campo de entrada --------------------------------------------------

    def ler_entrada(self):
        return self.entrada.get().strip()

    def limpar_entrada(self):
        self.entrada.delete(0, 'end')

    def preencher_entrada(self, valor):
        """Pre-preenche o campo (renomear vem com o nome atual)."""
        self.entrada.delete(0, 'end')
        if valor:
            self.entrada.insert(0, valor)
        self.entrada.focus_set()
