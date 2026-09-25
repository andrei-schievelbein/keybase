"""HelpScreen: referencia de comandos."""

from .. import atalhos
from .base import Screen

SECOES = [
    ("Navegação", [
        ("1 2 3 …", "abrir o item pelo número da lista"),
        ("V", "voltar um nível (ou limpar o filtro)"),
        ("M", "ir direto para a raiz"),
        ("Enter vazio", "o mesmo que V"),
    ]),
    ("Criar e editar", [
        ("P", "criar uma pasta na pasta atual"),
        ("N", "criar uma nota na pasta atual"),
        ("E  ou  E3", "editar o conteúdo de uma nota"),
        ("R  ou  R3", "renomear um item"),
        ("D  ou  D3", "apagar um item"),
        ("X  ou  X3", "mover um item para outra pasta"),
        ("Z  ou  Z3", "duplicar um item (\"Nome (cópia)\")"),
        ("Y  ou  Y3", "copiar um item para outra pasta (o original fica)"),
        ("Y na nota", "área de transferência: Y2 copia o 2º bloco de código"),
        ("U", "desfazer a última ação (apagar, mover, renomear, duplicar, decifrar)"),
        ("W  ou  W3", "exportar a pasta (ou a pasta 3) como arquivos .md"),
        ("F  ou  F3", "marcar ou desmarcar um favorito"),
        ("L", "favoritos e notas abertas recentemente"),
        ("[[Nota]]", "numa nota, vira link; [[Pasta/Nota|texto]] também vale"),
        ("H na nota", "histórico: versões dos backups; R restaura (U desfaz)"),
        ("Modelos/", "notas dessa pasta da raiz viram modelos ao criar com N"),
    ]),
    ("Buscar", [
        ("texto", "filtrar a pasta atual pelo nome - basta digitar e dar Enter"),
        ("/texto", "o mesmo, para termos que colidem com um comando (/b, /c)"),
        ("B", "buscar em toda a base (nome, descrição e conteúdo)"),
        ("setas", "nos resultados, escolhem um item; ENTER abre o escolhido"),
        ("V", "limpa o filtro e volta a listar tudo"),
    ]),
    ("Notas e pastas cifradas", [
        ("K  ou  K3", "cifrar ou decifrar uma nota (pede a senha mestra)"),
        ("K  numa pasta", "1 cifra as notas dela, 2 liga 'novas cifradas',"),
        ("", "3 cifra a pasta inteira (nomes incluídos)"),
        ("P", "ao criar uma pasta, s = notas novas nascem cifradas"),
        ("[novas cifradas]", "pasta cujas notas novas já nascem cifradas"),
        ("[cifrada]", "nota ou pasta inteira protegida pela senha"),
        ("A", "no viewer: digitar a senha de uma nota trancada"),
        ("T", "tranca os itens cifrados; se trancados, pede a senha e destranca"),
        ("S", "trocar a senha mestra"),
    ]),
    ("No editor de notas", [
        (atalhos.rotulo(atalhos.SALVAR), "salvar e voltar"),
        (atalhos.rotulo(atalhos.CANCELAR), "vai para a barra; na barra, cancela a edição"),
        (atalhos.rotulo(atalhos.MODO_EDITAR), "só o editor"),
        (atalhos.rotulo(atalhos.MODO_PREVIEW), "só o preview (do texto não salvo)"),
        (atalhos.rotulo(atalhos.MODO_DIVIDIDO), "tela dividida: editor e preview"),
        (atalhos.rotulo(atalhos.MODO_CICLAR), "alterna entre os três modos"),
        ("?", "na barra de cima: mostra ou esconde os atalhos de edição"),
        ("??", "na barra de cima: esta ajuda (o texto não salvo é mantido)"),
        ("```python", "abre um bloco de código com destaque de sintaxe"),
    ]),
    ("Configuração", [
        ("C", "abre keybase_config.toml no editor, como uma nota"),
        (atalhos.rotulo(atalhos.SALVAR), "valida, salva e aplica (fontes só ao reabrir)"),
        ("tempo_aviso_ms", "quanto tempo um aviso fica no lugar do caminho"),
        ("tempo_aviso_longo_ms", "o mesmo, para avisos com algo para ler; 0 = fica até o ENTER"),
        ("", "com erro, nada é gravado: o erro aparece em vermelho no topo"),
    ]),
    ("Outros", [
        ("?", "mostra ou esconde o menu de comandos"),
        (atalhos.rotulo(atalhos.AJUDA_DINAMICA), "o mesmo que ?"),
        ("??", "esta ajuda completa"),
        ("sair", "encerrar (a janela também salva ao fechar)"),
    ]),
]


class HelpScreen(Screen):
    COMANDOS = {'V': 'cmd_voltar'}
    ROTULOS = {'V': 'Voltar'}
    # Esta tela ja lista tudo: nao desenha o menu, e o '?'/Ctrl+0 fica inerte.
    MOSTRA_MENU = False

    def render(self):
        view = self.app.view
        view.cabecalho("AJUDA - COMANDOS DO KEYBASE")

        for titulo, linhas in SECOES:
            view.linha(" " + titulo.upper(), 'pasta')
            for comando, descricao in linhas:
                view.trechos([
                    (f" {comando:>13} - ", 'flash'),
                    (descricao, 'nota'),
                ])
            view.linha()

        view.barra()
        view.linha(" Uma pasta pode conter outras pastas e notas, sem limite de "
                   "profundidade.", 'dica')
        view.linha(" Notas são escritas em Markdown.", 'dica')
        view.barra()
        view.linha(" V ou ENTER para voltar", 'dica')
        view.barra()

    def selecionar(self, indice):
        self.app.pop()

    def cmd_voltar(self, alvo=None):
        self.app.pop()

    def cmd_ajuda_completa(self):
        """Evita empilhar uma segunda HelpScreen, identica, sobre esta - o 'V'
        de volta precisaria ser apertado duas vezes sem nada explicar por que."""
