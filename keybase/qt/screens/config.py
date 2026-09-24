"""ConfigScreen: o keybase_config.toml aberto no proprio editor, como uma nota.

Herda o editor inteiro - Ctrl+S, Esc para a barra e de novo para cancelar,
'?', '??', a pergunta antes de descartar. Muda so o que e diferente de uma
nota: de onde vem o texto, o cabecalho, e o que Ctrl+S faz.

Ctrl+S VALIDA antes de gravar. Com erro, nada e gravado e o editor fica
aberto com o erro em vermelho no cabecalho: sair gravando um arquivo que o
proximo inicio nao consegue ler seria trocar um erro visivel por um escondido.
"""

from ... import config as mod_config
from .. import atalhos
from ..painel_nota import EDITAR
from .editor import EditorScreen

NOME_ARQUIVO = "keybase_config.toml"


class ConfigScreen(EditorScreen):
    TEXTO_PURO = True  # '# comentario' do TOML nao e titulo de Markdown

    def __init__(self, app, caminho=None):
        super().__init__(app, file_id=None)
        self.caminho = caminho
        self.erro = None
        self.aviso = None

    def on_enter(self):
        self.descartada = False
        if not self._carregado:
            texto = mod_config.ler_texto_config(self.caminho)
            texto, novas = mod_config.completar_texto(texto)
            self.texto_original = texto
            if novas:
                self.aviso = (f"Opções novas incluídas: {', '.join(novas)}. "
                              f"Ctrl+S grava no arquivo.")

    def _ativo(self):
        return True

    def _rotulo_descarte(self):
        return f"Arquivo: {NOME_ARQUIVO}"

    def _modo_inicial(self):
        return EDITAR  # preview de TOML nao diz nada

    # --- cabecalho e menu ------------------------------------------------

    def _atualizar_barra(self):
        view = self.app.view
        view.cabecalho_edicao(["CONFIGURAÇÃO"], "CONFIGURAÇÃO",
                              f"Editando: {NOME_ARQUIVO}", erro=self.erro,
                              aviso=self.aviso)
        view.dica(self.help_text())

    def _menu_atalhos(self):
        """Sem os atalhos de modo: aqui so existe o modo editar."""
        r = atalhos.rotulo
        esquerda = [
            (r(atalhos.SALVAR), "Validar, salvar e aplicar"),
            (r(atalhos.CANCELAR), "Ir para a barra"),
        ]
        direita = [
            (r(atalhos.AJUDA_DINAMICA), "Esconder atalhos (ou ?)"),
            ("??", "Ajuda completa"),
        ]
        largura_tecla = max(len(tecla) for tecla, _ in esquerda + direita)

        def celula(par):
            return f"{par[0]:>{largura_tecla}} - {par[1]}"

        coluna = max(len(celula(p)) for p in esquerda) + 4
        return [(celula(e).ljust(coluna) + celula(d)).rstrip()
                for e, d in zip(esquerda, direita)]

    def on_modo(self, modo):
        """Ctrl+1/2/3 inertes: so ha o modo editar."""

    def on_ciclar_modo(self):
        """Ctrl+E inerte, pelo mesmo motivo."""

    # --- salvar -------------------------------------------------------------

    def on_save(self):
        texto = self.app.view.texto_editor()
        usuario, erros = mod_config.validar_texto(texto)
        if erros:
            self.erro = erros[0] if len(erros) == 1 else (
                f"{erros[0]}  (+{len(erros) - 1} erro{'s' if len(erros) > 2 else ''})")
            self._atualizar_barra()
            return

        try:
            mod_config.salvar_texto_config(texto, self.caminho)
        except OSError as e:
            self.erro = f"Não foi possível gravar {NOME_ARQUIVO}: {e}"
            self._atualizar_barra()
            return

        self.erro = None
        self.aviso = None
        self.texto_original = texto
        mudou = self.app.aplicar_config(usuario)
        aviso = "Configuração salva."
        if 'fonts' in mudou:
            aviso += " Fontes mudam ao reabrir o KeyBase."
        if 'dados' in mudou:
            aviso += " A pasta de dados muda ao reabrir o KeyBase."
        self.app.flash(aviso)
        self.app.pop()
