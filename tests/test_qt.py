"""Testes da UI Qt dirigindo o app de verdade, sem interacao manual.

Rodam headless com QT_QPA_PLATFORM=offscreen, inclusive em CI - melhor que a
suite Tk anterior, que se auto-pulava quando nao havia display.

A QApplication e singleton de processo e NUNCA e destruida: criar e destruir
uma por teste e fonte conhecida de segfault.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# ANTES de qualquer import de PySide6: o plugin de plataforma e escolhido na
# criacao da QApplication e a variavel e lida nesse momento.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PySide6.QtWidgets import QApplication
    _qt_erro = None
except Exception as e:  # pragma: no cover
    QApplication = None
    _qt_erro = e

from keybase import storage, tree
from keybase.config import DEFAULT_CONFIG
from keybase.model import ID_RAIZ

_QAPP = None


def _app_qt():
    global _QAPP
    _QAPP = QApplication.instance() or QApplication([])
    return _QAPP


@unittest.skipUnless(QApplication is not None, f"PySide6 indisponivel ({_qt_erro})")
class BaseUI(unittest.TestCase):
    def setUp(self):
        from keybase.qt.app import App
        from keybase.qt.janela import JanelaPrincipal
        from keybase.qt.screens.browser import BrowserScreen

        _app_qt()
        self.dir = Path(tempfile.mkdtemp())
        self.arquivo = self.dir / 'keybase_data.json'

        config = {k: (dict(v) if isinstance(v, dict) else v)
                  for k, v in DEFAULT_CONFIG.items()}
        config['theme'] = 'light'
        config['geometry'] = '800x600'
        self.config = config

        self.janela = JanelaPrincipal(config)
        self.view = self.janela.view
        self.janela.resize(800, 600)
        self.janela.show()   # offscreen: show() resolve a geometria de verdade
        # WindowShortcut so dispara com a janela ATIVA, e no offscreen ela nao
        # e ativada sozinha - sem isto os testes de tecla dariam falso negativo
        self.janela.activateWindow()
        _app_qt().processEvents()

        doc = storage.Documento.novo()
        self.app = App(self.janela, self.view, doc, self.arquivo, config)
        # a tela de configuracao nunca pode tocar o arquivo real do usuario
        self.arquivo_config = self.dir / 'keybase_config.toml'
        self.app.caminho_config = self.arquivo_config
        self.janela.ligar(self.app)
        self.app.stack = [BrowserScreen(self.app, ID_RAIZ)]
        self.app.rerender()

    def tearDown(self):
        try:
            self.janela._encerrando = True   # nao dispara ao_fechar no close
            self.janela.close()
            self.janela.deleteLater()
            _app_qt().processEvents()        # NUNCA qapp.quit()
        except Exception:
            pass
        shutil.rmtree(self.dir, ignore_errors=True)

    # --- helpers -----------------------------------------------------------

    def digitar(self, comando):
        """Simula digitar no campo de entrada e apertar Enter."""
        self.view.entrada.setText(comando)
        self.app.submit()

    def tela(self):
        return self.view.out.toPlainText()

    def nome_tela(self):
        return type(self.app.atual).__name__

    def assertNaTela(self, trecho):
        """Procura na tela ignorando caixa e acento (o estilo do texto muda)."""
        from keybase.tree import normalizar
        self.assertIn(normalizar(trecho), normalizar(self.tela()))

    def assertLinhaComFim(self, trecho, fim):
        """Alguma linha contem `trecho` e TERMINA com `fim`: o formato das
        marcas alinhadas a direita."""
        linhas = [l.strip() for l in self.tela().splitlines()]
        self.assertTrue(any(trecho in l and l.endswith(fim) for l in linhas),
                        f"nenhuma linha {trecho!r} ... {fim!r} em:\n{self.tela()}")

    def assertNaoNaTela(self, trecho):
        from keybase.tree import normalizar
        self.assertNotIn(normalizar(trecho), normalizar(self.tela()))

    def editor(self):
        return self.view.painel.editor

    def digitar_no_editor(self, texto):
        self.editor().setPlainText(texto)

    def anexar_no_editor(self, texto):
        """Insere no FIM: definir_texto deixa o cursor no inicio."""
        from PySide6.QtGui import QTextCursor
        editor = self.editor()
        editor.moveCursor(QTextCursor.MoveOperation.End)
        editor.insertPlainText(texto)

    def esc_no_editor(self):
        """Esc no texto so leva o cursor para a barra; o segundo cancela."""
        self.app.cancel()
        self.assertFalse(self.view.foco_na_edicao())
        self.app.cancel()

    def criar_pasta(self, nome, cifrada=False):
        self.digitar('P')
        self.digitar(nome)
        self.digitar('s' if cifrada else '')   # "nascem cifradas?" - padrao nao

    def criar_nota(self, nome, conteudo=""):
        self.digitar('N')
        self.digitar(nome)          # cai no editor
        if self.nome_tela() == 'PromptScreen':
            self.digitar('1')       # sem pasta de modelos: "1 - Em branco"
        if conteudo:
            self.digitar_no_editor(conteudo)
        self.app.save()             # Ctrl+S
        self.digitar('')            # sai do viewer

class TestNavegacao(BaseUI):
    def test_raiz_comeca_vazia(self):
        self.assertNaTela("pasta vazia")
        self.assertIn("~", self.tela())

    def test_criar_e_entrar_em_pasta(self):
        self.criar_pasta("Vscode")
        self.assertIn("Vscode/", self.tela())
        self.digitar('1')
        self.assertIn("~ / Vscode", self.tela())

    def test_tres_niveis_e_breadcrumb(self):
        self.criar_pasta("Vscode")
        self.digitar('1')
        self.criar_pasta("Navegação")
        self.digitar('1')
        self.criar_pasta("Básico")
        self.app._fim_do_flash()   # o aviso "criada" sai, o caminho volta
        self.assertIn("~ / Vscode / Navegação", self.tela())
        self.digitar('1')
        self.assertIn("~ / Vscode / Navegação / Básico", self.tela())

    def test_voltar_sobe_um_nivel(self):
        self.criar_pasta("A")
        self.digitar('1')
        self.criar_pasta("B")
        self.digitar('1')
        self.digitar('V')
        self.assertIn("~ / A", self.tela())
        self.digitar('V')
        self.assertIn("~", self.tela())

    def test_voltar_na_raiz_nao_sai_do_app(self):
        for _ in range(3):
            self.digitar('V')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertIn("já está na raiz", self.tela())

    def test_comando_M_volta_para_a_raiz(self):
        self.criar_pasta("A")
        self.digitar('1')
        self.criar_pasta("B")
        self.digitar('1')
        self.digitar('M')
        self.assertEqual(len(self.app.stack), 1)

    def test_numero_fora_da_lista(self):
        self.criar_pasta("A")
        self.digitar('9')
        self.assertIn("fora da lista", self.tela())

    def test_pastas_antes_de_notas(self):
        self.criar_nota("aaa nota")
        self.criar_pasta("zzz pasta")
        tela = self.tela()
        self.assertLess(tela.index("zzz pasta"), tela.index("aaa nota"))

    def linha_de(self, nome):
        """A linha da listagem que contém esse nome."""
        for linha in self.tela().splitlines():
            if nome in linha:
                return linha.rstrip()
        self.fail(f"{nome!r} não está na tela:\n{self.tela()}")

    def test_contador_separa_notas_diretas_do_total(self):
        """[a]:[b] = notas soltas aqui : notas em toda a hierarquia."""
        self.criar_pasta("Pai")
        self.digitar('1')
        self.criar_nota("solta")          # 1 nota direta em Pai
        self.criar_pasta("Sub")
        self.digitar('1')                 # pastas vêm antes das notas: 1 = Sub/
        self.criar_nota("funda")          # 1 nota no nível de baixo
        self.digitar('V'); self.digitar('V')
        self.assertIn("[1]:[2]", self.linha_de("Pai/"))

    def test_contador_ignora_pastas(self):
        """Pasta só com sub-pastas não tem nota nenhuma: [0]:[0]."""
        self.criar_pasta("Pai")
        self.digitar('1')
        self.criar_pasta("F1")
        self.criar_pasta("F2")
        self.digitar('V')
        self.assertIn("[0]:[0]", self.linha_de("Pai/"))

    def test_contador_repete_quando_nao_ha_sub_pasta(self):
        self.criar_pasta("Pai")
        self.digitar('1')
        self.criar_nota("a"); self.criar_nota("b")
        self.digitar('V')
        self.assertIn("[2]:[2]", self.linha_de("Pai/"))

    def test_pasta_vazia_nao_tem_contador(self):
        self.criar_pasta("Vazia")
        self.assertNotIn("[", self.linha_de("Vazia/"))

    def test_contador_tem_o_mesmo_formato_nos_niveis_de_baixo(self):
        """linha_item é a única função que desenha pasta, então todo nível usa
        o mesmo formato — e a soma recursiva atravessa os níveis."""
        self.criar_pasta("Pai")
        self.digitar('1')
        self.criar_pasta("Sub")
        self.digitar('1')
        self.criar_pasta("Neto")
        self.digitar('1')
        self.criar_nota("funda")          # a única nota, três níveis abaixo
        self.digitar('V')                 # volta para dentro de Sub
        self.assertIn("[1]:[1]", self.linha_de("Neto/"))
        self.digitar('V')                 # volta para dentro de Pai
        self.assertIn("[0]:[1]", self.linha_de("Sub/"))

    def test_tela_se_recupera_de_no_removido(self):
        self.criar_pasta("Some")
        self.digitar('1')
        # remove por baixo, como se outro ponto da pilha tivesse apagado
        alvo = self.app.raiz.filhos[0]
        tree.remover(self.app.raiz, alvo)
        self.app.reindexar()
        self.app.rerender()
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertFalse(self.app.atual.descartada)


class TestCriacao(BaseUI):
    def test_nota_cai_direto_no_editor(self):
        self.digitar('N')
        self.digitar('Minha nota')
        self.digitar('1')   # Em branco
        self.assertEqual(self.nome_tela(), 'EditorScreen')
        self.assertTrue(self.app.atual.usa_editor())

    def test_nome_duplicado_e_recusado_sem_perder_o_digitado(self):
        self.criar_pasta("Igual")
        self.digitar('P')
        self.digitar('igual')  # mesma coisa ignorando caixa
        self.assertEqual(self.nome_tela(), 'PromptScreen')
        self.assertIn("Já existe", self.tela())
        self.assertEqual(self.view.entrada.text(), 'igual')

    def test_nome_vazio_cancela(self):
        self.digitar('P')
        self.digitar('')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertEqual(self.app.raiz.filhos, [])

    def test_persistencia_em_disco(self):
        self.criar_pasta("Vscode")
        self.assertTrue(self.arquivo.exists())
        recarregado = storage.carregar(self.arquivo)
        self.assertEqual(recarregado.raiz.filhos[0].nome, "Vscode")


class TestEdicao(BaseUI):
    def test_salvar_conteudo(self):
        self.criar_nota("Nota", "# Titulo\n\ncorpo")
        recarregado = storage.carregar(self.arquivo)
        self.assertEqual(recarregado.raiz.filhos[0].conteudo, "# Titulo\n\ncorpo")

    def test_nota_terminada_em_CTRL_S_sobrevive(self):
        """O bug da versao anterior: a sentinela era removida do texto."""
        conteudo = "instrucoes aqui\n\nCTRL_S"
        self.criar_nota("Atalho", conteudo)
        recarregado = storage.carregar(self.arquivo)
        self.assertEqual(recarregado.raiz.filhos[0].conteudo, conteudo)
        self.assertTrue(recarregado.raiz.filhos[0].conteudo.endswith("CTRL_S"))

    def test_esc_com_alteracao_pede_confirmacao(self):
        self.criar_nota("Nota", "original")
        self.digitar('1')            # viewer
        self.digitar('E')            # editor
        self.anexar_no_editor(' alterado')
        self.esc_no_editor()            # Esc
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')
        self.assertIn("Descartar", self.tela())

    def test_esc_descartando_preserva_o_original(self):
        self.criar_nota("Nota", "original")
        self.digitar('1')
        self.digitar('E')
        self.anexar_no_editor(' alterado')
        self.esc_no_editor()
        self.digitar('S')            # sim, descartar
        recarregado = storage.carregar(self.arquivo)
        self.assertEqual(recarregado.raiz.filhos[0].conteudo, "original")
        # descartar volta ao viewer, nao ao browser: a ConfirmScreen ja se
        # desempilha sozinha, entao o editor pode remover apenas a si mesmo
        self.assertEqual(self.nome_tela(), 'ViewerScreen')

    def test_editar_de_novo_depois_de_descartar(self):
        self.criar_nota("Nota", "original")
        self.digitar('1')
        self.digitar('E')
        self.anexar_no_editor(' descartado')
        self.esc_no_editor()
        self.digitar('S')
        # a segunda edição tem de funcionar normalmente
        self.digitar('E')
        self.assertEqual(self.nome_tela(), 'EditorScreen')
        self.anexar_no_editor(' salvo')
        self.app.save()
        self.assertEqual(storage.carregar(self.arquivo).raiz.filhos[0].conteudo,
                         "original salvo")

    def test_esc_sem_alteracao_sai_direto(self):
        self.criar_nota("Nota", "original")
        self.digitar('1')
        self.digitar('E')
        self.esc_no_editor()
        self.assertEqual(self.nome_tela(), 'ViewerScreen')

    def test_viewer_renderiza_markdown(self):
        self.criar_nota("Nota", "# Titulo\n\n```python\nx = 42\n```")
        self.digitar('1')
        tela = self.tela()
        self.assertIn("Titulo", tela)
        self.assertIn("x = 42", tela)
        self.assertNotIn("```", tela)  # o fence foi consumido

    def test_editor_mostra_markdown_cru(self):
        self.criar_nota("Nota", "# Titulo\n\n```python\nx = 42\n```")
        self.digitar('1')
        self.digitar('E')
        self.assertIn("```python", self.view.texto_editor())

    def test_editar_direto_do_browser_com_alvo(self):
        self.criar_nota("Nota", "x")
        self.digitar('E1')
        self.assertEqual(self.nome_tela(), 'EditorScreen')
        # sair do editor cai no viewer, nao no browser
        self.esc_no_editor()
        self.assertEqual(self.nome_tela(), 'ViewerScreen')

    def test_editar_pasta_e_recusado(self):
        self.criar_pasta("Pasta")
        self.digitar('E1')
        self.assertIn("conteúdo de uma nota", self.tela())


class TestRenomearDeletar(BaseUI):
    def test_renomear_vem_pre_preenchido(self):
        self.criar_pasta("Antigo")
        self.digitar('R1')
        self.assertEqual(self.view.entrada.text(), 'Antigo')

    def test_renomear_aplica(self):
        self.criar_pasta("Antigo")
        self.digitar('R1')
        self.digitar('Novo')
        self.assertIn("Novo/", self.tela())
        self.assertEqual(storage.carregar(self.arquivo).raiz.filhos[0].nome, "Novo")

    def test_deletar_nota_pede_confirmacao_simples(self):
        self.criar_nota("Nota")
        self.digitar('D1')
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')
        self.assertFalse(self.app.atual.forte)
        self.digitar('S')
        self.assertEqual(self.app.raiz.filhos, [])

    def test_deletar_pasta_cheia_exige_palavra(self):
        self.criar_pasta("Cheia")
        self.digitar('1')
        self.criar_nota("Dentro")
        self.criar_pasta("Sub")
        self.digitar('V')
        self.digitar('D1')
        self.assertTrue(self.app.atual.forte)
        self.assertIn("1 pasta, 1 nota", self.tela())

        self.digitar('S')  # 'S' nao basta aqui
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')
        self.assertEqual(len(self.app.raiz.filhos), 1)

        self.digitar('DELETAR')
        self.assertEqual(self.app.raiz.filhos, [])

    def test_deletar_gera_backup(self):
        self.criar_pasta("A")
        self.criar_pasta("B")
        self.digitar('D1')
        self.digitar('S')
        self.assertTrue(storage.caminho_backup(self.arquivo).exists())

    def test_deletar_sem_alvo_pergunta_o_numero(self):
        self.criar_pasta("A")
        self.digitar('D')
        self.assertEqual(self.nome_tela(), 'PromptScreen')
        self.digitar('1')
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')

    def test_confirmacao_nao_aceita_outra_tecla(self):
        self.criar_nota("Nota")
        self.digitar('D1')
        self.digitar('N')
        self.assertEqual(len(self.app.raiz.filhos), 1)

    def test_deletar_do_viewer_sai_do_viewer(self):
        self.criar_nota("Nota")
        self.digitar('1')
        self.digitar('D')
        self.digitar('S')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertEqual(self.app.raiz.filhos, [])


class TestBusca(BaseUI):
    def montar(self):
        self.criar_pasta("Vscode")
        self.digitar('1')
        self.criar_pasta("Navegação")
        self.digitar('1')
        self.criar_nota("Ctrl + P", "Abre o seletor rápido de arquivos.")
        self.digitar('M')

    def test_buscar_em_profundidade_e_pular(self):
        self.montar()
        self.digitar('B')
        self.digitar('ctrl')
        self.assertEqual(self.nome_tela(), 'SearchResultsScreen')
        self.assertIn("Vscode / Navegação", self.tela())

        self.digitar('1')
        self.assertEqual(self.nome_tela(), 'ViewerScreen')
        self.assertIn("~ / Vscode / Navegação / Ctrl + P", self.tela())

    def test_voltar_de_um_hit_cai_nos_resultados(self):
        self.montar()
        self.digitar('B')
        self.digitar('ctrl')
        self.digitar('1')
        self.digitar('V')
        self.assertEqual(self.nome_tela(), 'SearchResultsScreen')

    def test_voltar_dos_resultados_percorre_a_arvore(self):
        self.montar()
        self.digitar('B')
        self.digitar('ctrl')
        self.digitar('1')
        self.digitar('V')   # resultados
        self.digitar('V')   # Navegação
        self.assertIn("~ / Vscode / Navegação", self.tela())

    def test_busca_por_conteudo_mostra_trecho(self):
        self.montar()
        self.digitar('B')
        self.digitar('seletor')
        self.assertIn("[nota]", self.tela())
        self.assertIn("seletor", self.tela())

    def test_busca_sem_acento_acha_com_acento(self):
        self.montar()
        self.digitar('B')
        self.digitar('navegacao')
        self.assertIn("[pasta]", self.tela())

    def test_termo_curto_e_recusado(self):
        self.montar()
        self.digitar('B')
        self.digitar('a')
        self.assertIn("pelo menos", self.tela())

    def test_filtro_local_nao_sai_da_pasta(self):
        self.criar_pasta("QuerySets")
        self.criar_pasta("Outra")
        self.digitar('/query')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertIn('filtro:', self.tela())
        self.assertIn("QuerySets/", self.tela())
        self.assertNotIn("Outra/", self.tela())
        self.assertIn("1 de 2 itens", self.tela())

    def test_voltar_limpa_o_filtro(self):
        self.criar_pasta("QuerySets")
        self.criar_pasta("Outra")
        self.digitar('/query')
        self.digitar('V')
        self.assertNotIn('filtro:', self.tela())
        self.assertIn("Outra/", self.tela())

    def test_numero_com_filtro_indexa_a_lista_filtrada(self):
        """A invariante de numeracao: o numero indexa o que esta na tela."""
        self.criar_pasta("AAA")
        self.criar_pasta("ZZZ alvo")
        self.digitar('/alvo')
        self.digitar('1')
        self.assertIn("~ / ZZZ alvo", self.tela())

    # --- texto livre filtra o nível visível --------------------------------

    def test_texto_livre_filtra_sem_precisar_de_barra(self):
        """O caso do pedido: 'num' + Enter deixa só Numpy, e 1 entra nela."""
        self.criar_pasta("Numpy")
        self.criar_pasta("Pandas")
        self.digitar('num')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertIn("Numpy/", self.tela())
        self.assertNotIn("Pandas/", self.tela())
        self.assertIn("1 de 2 itens", self.tela())
        self.digitar('1')
        self.assertIn("~ / Numpy", self.tela())

    def test_texto_livre_filtra_em_qualquer_nivel(self):
        self.criar_pasta("Vscode")
        self.digitar('1')
        self.criar_pasta("Atalhos")
        self.digitar('1')
        self.criar_nota("Ctrl + P")
        self.criar_nota("Alt + Tab")
        self.digitar('ctrl')
        self.assertIn("~ / Vscode / Atalhos", self.tela())   # não saiu do lugar
        self.assertIn("Ctrl + P", self.tela())
        self.assertNotIn("Alt + Tab", self.tela())

    def test_filtro_sem_resultado_aplica_e_o_V_destrava(self):
        self.criar_pasta("Numpy")
        self.criar_pasta("Pandas")
        self.digitar('zzz')
        self.assertIn("0 de 2 itens", self.tela())
        self.assertIn("Nenhum item corresponde", self.tela())
        self.digitar('V')
        self.assertNotIn('filtro:', self.tela())
        self.assertIn("Numpy/", self.tela())

    def test_letra_de_comando_continua_comando(self):
        """Texto livre não pode engolir os comandos de uma letra."""
        self.criar_pasta("Cursor")
        self.digitar('P')
        self.assertEqual(self.nome_tela(), 'PromptScreen')
        self.assertIn("Nome da nova pasta", self.tela())

    def test_barra_filtra_termo_que_colide_com_comando(self):
        """A escotilha: /c filtra por 'c' em vez de criar pasta."""
        self.criar_pasta("Cursor")
        self.criar_pasta("Numpy")
        self.digitar('/c')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertIn("Cursor/", self.tela())
        self.assertNotIn("Numpy/", self.tela())

    def test_letra_com_texto_filtra_em_vez_de_virar_comando(self):
        """'d ados' casava com o comando D pelo grupo 'resto', que era morto."""
        self.criar_pasta("d ados")
        self.criar_pasta("Numpy")
        self.digitar('d ados')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertIn('filtro:', self.tela())
        self.assertIn("d ados/", self.tela())
        self.assertNotIn("Numpy/", self.tela())

    def test_letra_com_numero_continua_comando_com_alvo(self):
        """D3 e 'D 3' seguem valendo: só o texto solto virou filtro."""
        self.criar_pasta("AAA")
        self.digitar('D 1')
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')

    def test_busca_global_nao_muda(self):
        self.criar_pasta("Numpy")
        self.digitar('B')
        self.assertEqual(self.nome_tela(), 'PromptScreen')
        self.digitar('numpy')
        self.assertEqual(self.nome_tela(), 'SearchResultsScreen')

    def test_texto_livre_na_tela_de_resultados_refaz_a_busca(self):
        self.criar_pasta("Numpy")
        self.criar_pasta("Pandas")
        self.digitar('B'); self.digitar('numpy')
        self.assertIn('Busca: "numpy"', self.tela())
        self.digitar('pandas')
        self.assertEqual(self.nome_tela(), 'SearchResultsScreen')
        self.assertIn('Busca: "pandas"', self.tela())


class TestAjudaERodape(BaseUI):
    def test_ajuda_completa_abre_com_dois_pontos_de_interrogacao(self):
        self.digitar('??')
        self.assertEqual(self.nome_tela(), 'HelpScreen')
        self.assertNaTela("comandos do KeyBase")
        self.digitar('V')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')

    def test_menu_comeca_escondido(self):
        self.assertNaoNaTela("P - Nova pasta")

    def test_interrogacao_alterna_o_menu(self):
        self.digitar('?')
        self.assertNaTela("P - Nova pasta")
        self.digitar('?')
        self.assertNaoNaTela("P - Nova pasta")

    def test_menu_vem_antes_do_breadcrumb(self):
        """O menu e o PRIMEIRO bloco da area de leitura, nao mais o ultimo."""
        self.digitar('?')
        tela = self.tela()
        self.assertLess(tela.index("P - Nova pasta"), tela.index("~"))

    def test_menu_mostra_ajuda_completa_e_nao_o_antigo_rotulo(self):
        self.digitar('?')
        self.assertNaTela("?? - Ajuda completa")
        self.assertNaoNaTela("? - Ajuda\n")

    def test_menu_continua_ligado_ao_navegar(self):
        """A visibilidade e do app, nao da instancia de tela."""
        self.criar_pasta("A")
        self.digitar('?')
        self.digitar('1')
        self.assertNaTela("P - Nova pasta")

    def test_interrogacao_num_prompt_e_texto_literal(self):
        """PromptScreen trata o input cru: da para nomear uma pasta '?'."""
        self.digitar('P')
        self.assertEqual(self.nome_tela(), 'PromptScreen')
        self.digitar('?')
        self.digitar('')   # "nascem cifradas?" - padrao nao
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertNaTela("?")
        self.assertIsNotNone(next((n for n in self.app.atual.itens
                                   if n.nome == '?'), None))

    def test_ajuda_completa_nao_empilha_sobre_si_mesma(self):
        self.digitar('??')
        altura = len(self.app.stack)
        self.digitar('??')
        self.assertEqual(len(self.app.stack), altura)
        self.assertEqual(self.nome_tela(), 'HelpScreen')

    def test_ajuda_completa_lista_os_dois_comandos(self):
        from keybase.qt import atalhos
        self.digitar('??')
        self.assertNaTela("esta ajuda completa")
        self.assertNaTela("mostra ou esconde o menu")
        self.assertIn(atalhos.rotulo(atalhos.AJUDA_DINAMICA), self.tela())

    # --- Ctrl+0 ------------------------------------------------------------

    def test_ctrl_zero_alterna_o_menu(self):
        self.app.alternar_menu()
        self.assertNaTela("P - Nova pasta")
        self.app.alternar_menu()
        self.assertNaoNaTela("P - Nova pasta")

    def test_ctrl_zero_dispara_pela_tecla(self):
        """Prova a fiacao, nao so a chamada direta a app.alternar_menu()."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        modificador = (Qt.KeyboardModifier.MetaModifier
                       if sys.platform == 'darwin'
                       else Qt.KeyboardModifier.ControlModifier)
        alvo = _app_qt().focusWidget() or self.janela
        QTest.keyClick(alvo, Qt.Key.Key_0, modificador)
        _app_qt().processEvents()
        self.assertNaTela("P - Nova pasta")

    def test_ctrl_zero_e_inerte_onde_o_menu_nao_aparece(self):
        """A regra: o atalho só age onde o menu é desenhado. Sem isso, o Ctrl+0
        num prompt alternava em silêncio o menu da tela de baixo."""
        self.digitar('P')
        self.assertEqual(self.nome_tela(), 'PromptScreen')
        self.app.alternar_menu()
        self.assertFalse(self.app.menu_visivel)
        self.digitar('')                      # cancela o prompt
        self.assertNaoNaTela("P - Nova pasta")

    def test_ctrl_zero_e_inerte_na_confirmacao(self):
        self.criar_pasta("A")
        self.digitar('D1')
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')
        self.app.alternar_menu()
        self.assertFalse(self.app.menu_visivel)

    def test_ctrl_zero_e_inerte_na_ajuda_completa(self):
        self.digitar('??')
        self.app.alternar_menu()
        self.assertFalse(self.app.menu_visivel)

    def test_telas_sem_menu_declaram_a_flag(self):
        """Uma flag só governa o desenho E o atalho: não podem divergir."""
        from keybase.qt.screens.browser import BrowserScreen
        from keybase.qt.screens.editor import EditorScreen
        from keybase.qt.screens.help import HelpScreen
        from keybase.qt.screens.prompt import ConfirmScreen, PromptScreen
        from keybase.qt.screens.recovery import RecoveryScreen
        from keybase.qt.screens.search import SearchResultsScreen
        from keybase.qt.screens.viewer import ViewerScreen

        for classe in (PromptScreen, ConfirmScreen, HelpScreen, RecoveryScreen):
            self.assertFalse(classe.MOSTRA_MENU, classe.__name__)
        # o editor tem menu - o de atalhos de edicao, na barra de dica
        for classe in (BrowserScreen, ViewerScreen, SearchResultsScreen, EditorScreen):
            self.assertTrue(classe.MOSTRA_MENU, classe.__name__)

    def test_ctrl_zero_no_editor_nao_mexe_no_texto(self):
        self.criar_nota("Nota", "original")
        self.digitar('1'); self.digitar('E')
        self.anexar_no_editor(" alterado")
        self.app.alternar_menu()
        self.assertEqual(self.nome_tela(), 'EditorScreen')
        self.assertIn("original alterado", self.editor().toPlainText())

    # --- botao -------------------------------------------------------------

    def test_botao_de_ajuda_nao_rouba_o_foco_da_barra(self):
        from PySide6.QtCore import Qt
        self.assertEqual(self.view.botao_ajuda.focusPolicy(),
                         Qt.FocusPolicy.NoFocus)

    def test_botao_de_ajuda_e_quadrado(self):
        largura = self.view.botao_ajuda.width()
        self.assertEqual(largura, self.view.botao_ajuda.height())
        self.assertGreaterEqual(largura, 24)

    def clicar_ajuda(self):
        """Clique de verdade no botão, para provar a fiação e não só o verbo."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        QTest.mouseClick(self.view.botao_ajuda, Qt.MouseButton.LeftButton)
        _app_qt().processEvents()

    def test_clique_no_botao_alterna_o_menu(self):
        self.clicar_ajuda()
        self.assertNaTela("P - Nova pasta")
        self.clicar_ajuda()
        self.assertNaoNaTela("P - Nova pasta")

    def test_botao_e_barra_compartilham_o_mesmo_interruptor(self):
        """Clicar liga; '?' na barra desliga. Um estado só, três caminhos."""
        self.clicar_ajuda()
        self.assertTrue(self.app.menu_visivel)
        self.digitar('?')
        self.assertFalse(self.app.menu_visivel)
        self.app.alternar_menu()          # Ctrl+0
        self.assertTrue(self.app.menu_visivel)

    def test_botao_apaga_onde_o_menu_nao_existe(self):
        self.assertTrue(self.view.botao_ajuda.isEnabled())
        self.digitar('P')                 # prompt: sem menu
        self.assertEqual(self.nome_tela(), 'PromptScreen')
        self.assertFalse(self.view.botao_ajuda.isEnabled())
        self.digitar('')                  # cancela
        self.assertTrue(self.view.botao_ajuda.isEnabled())

    def test_botao_fica_ativo_no_editor(self):
        self.criar_nota("Nota", "x")
        self.digitar('1'); self.digitar('E')
        self.assertEqual(self.nome_tela(), 'EditorScreen')
        self.assertTrue(self.view.botao_ajuda.isEnabled())

    # --- menu de atalhos no editor ----------------------------------------

    def abrir_editor(self, conteudo="original"):
        self.criar_nota("Nota", conteudo)
        self.digitar('1'); self.digitar('E')
        self.assertEqual(self.nome_tela(), 'EditorScreen')

    def test_botao_no_editor_mostra_os_atalhos_de_edicao(self):
        from keybase.qt import atalhos
        self.abrir_editor()
        rotulo = atalhos.rotulo(atalhos.MODO_DIVIDIDO)
        self.assertNotIn(rotulo, self.view.ajuda.text())
        self.clicar_ajuda()
        self.assertIn(rotulo + " - Dividido", self.view.ajuda.text())
        self.clicar_ajuda()
        self.assertNotIn(rotulo, self.view.ajuda.text())

    def test_interrogacao_na_barra_alterna_o_menu_do_editor(self):
        from keybase.qt import atalhos
        self.abrir_editor()
        self.digitar('?')
        self.assertTrue(self.app.menu_visivel)
        self.assertIn("Alternar modo", self.view.ajuda.text())
        self.digitar('?')
        self.assertFalse(self.app.menu_visivel)
        self.assertNotIn("Alternar modo", self.view.ajuda.text())
        self.assertEqual(self.nome_tela(), 'EditorScreen')
        self.assertEqual(self.editor().toPlainText(), "original")

    def test_interrogacao_no_editor_e_texto_da_nota(self):
        self.abrir_editor()
        self.anexar_no_editor(" ?")
        self.assertFalse(self.app.menu_visivel)
        self.app.save()
        self.assertEqual(self.app.raiz.filhos[0].conteudo, "original ?")

    def test_ajuda_completa_no_editor_preserva_o_texto(self):
        self.abrir_editor()
        self.anexar_no_editor(" nao salvo")
        self.digitar('??')
        self.assertEqual(self.nome_tela(), 'HelpScreen')
        self.assertNaTela("AJUDA")
        self.digitar('V')
        self.assertEqual(self.nome_tela(), 'EditorScreen')
        self.assertTrue(self.view.em_edicao())
        self.assertEqual(self.editor().toPlainText(), "original nao salvo")

    def test_rodape_so_mostra_comando_implementado(self):
        """Rodape e despacho saem do mesmo dict, entao nao podem divergir."""
        from keybase.qt.screens.browser import BrowserScreen
        from keybase.qt.screens.search import SearchResultsScreen
        from keybase.qt.screens.viewer import ViewerScreen

        for classe in (BrowserScreen, ViewerScreen, SearchResultsScreen):
            for letra, metodo in classe.COMANDOS.items():
                self.assertTrue(hasattr(classe, metodo),
                                f"{classe.__name__}: {letra} aponta para {metodo} inexistente")
                self.assertIn(letra, classe.ROTULOS,
                              f"{classe.__name__}: {letra} sem rótulo no rodapé")

    def test_rodape_esconde_voltar_na_raiz(self):
        self.digitar('?')   # o menu nasce escondido
        self.assertNaoNaTela("V - Voltar")
        self.criar_pasta("A")
        self.digitar('1')
        self.assertNaTela("V - Voltar")

    def test_comando_invalido_avisa_onde_nao_ha_o_que_filtrar(self):
        """No browser texto livre filtra; no viewer não há lista, então avisa."""
        self.criar_nota("Nota", "x")
        self.digitar('1')
        self.assertEqual(self.nome_tela(), 'ViewerScreen')
        self.digitar('XYZ')
        self.assertIn("não reconhecido", self.tela())

    def test_saida_e_somente_leitura(self):
        # CTkTextbox nao expoe 'state' via cget; o estado fica no widget Tk interno
        self.assertTrue(self.view.out.isReadOnly())

    def test_digitar_na_saida_nao_altera_o_conteudo(self):
        from PySide6.QtTest import QTest
        antes = self.tela()
        self.view.out.setFocus()
        QTest.keyClicks(self.view.out, 'abc')
        _app_qt().processEvents()
        self.assertEqual(self.tela(), antes)


class TestModos(BaseUI):
    def test_editor_e_saida_sao_exclusivos(self):
        """A tela dividida nunca pode vazar para o modo terminal."""
        self.assertIs(self.view.pilha.currentWidget(), self.view.out)

        self.digitar('N')
        self.digitar('Nota')
        self.digitar('1')   # Em branco
        self.assertIs(self.view.pilha.currentWidget(), self.view.painel)

        self.app.save()
        self.assertIs(self.view.pilha.currentWidget(), self.view.out)

    def test_barra_de_dica_so_aparece_no_editor_com_o_menu_aberto(self):
        self.assertFalse(self.view.ajuda.isVisibleTo(self.janela))
        self.digitar('N')
        self.digitar('Nota')
        self.digitar('1')   # Em branco
        self.assertFalse(self.view.ajuda.isVisibleTo(self.janela))
        self.digitar('?')
        self.assertTrue(self.view.ajuda.isVisibleTo(self.janela))
        from keybase.qt import atalhos
        self.assertIn(atalhos.rotulo(atalhos.SALVAR), self.view.ajuda.text())

    def test_ctrl_s_fora_do_editor_e_inocuo(self):
        self.app.save()
        self.assertEqual(self.nome_tela(), 'BrowserScreen')


class TestRecuperacao(BaseUI):
    def test_arquivo_corrompido_entra_em_modo_recuperacao(self):
        from keybase.qt.app import App
        from keybase.qt.screens.recovery import RecoveryScreen

        self.criar_pasta("A")
        self.criar_pasta("B")          # gera .bak
        corrompido = '{"schema_version": 2, "raiz": {quebr'
        self.arquivo.write_text(corrompido, encoding='utf-8')

        try:
            storage.carregar(self.arquivo)
            self.fail("deveria ter levantado")
        except storage.StorageError as e:
            doc = storage.Documento.novo()
            doc.somente_leitura = True
            app = App(self.janela, self.view, doc, self.arquivo, self.config)
            app.stack = [RecoveryScreen(app, e, self.arquivo)]
            app.rerender()

        self.assertNaTela("não foi possível ler")
        self.assertNaTela("Restaurar")
        # o arquivo corrompido continua intacto
        self.assertEqual(self.arquivo.read_text(encoding='utf-8'), corrompido)

    def test_restaurar_backup_recupera_os_dados(self):
        from keybase.qt.app import App
        from keybase.qt.screens.recovery import RecoveryScreen

        self.criar_pasta("A")
        self.criar_pasta("B")
        self.arquivo.write_text('{quebrado', encoding='utf-8')

        try:
            storage.carregar(self.arquivo)
        except storage.StorageError as e:
            doc = storage.Documento.novo()
            doc.somente_leitura = True
            app = App(self.janela, self.view, doc, self.arquivo, self.config)
            app.stack = [RecoveryScreen(app, e, self.arquivo)]
            app.rerender()
            app.atual.selecionar(0)

        self.assertTrue(storage.carregar(self.arquivo).raiz.filhos)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestFonteELayout(BaseUI):
    def test_familia_escolhida_existe_de_fato(self):
        """Pedir familia inexistente ao Qt devolve outra fonte em silencio."""
        from PySide6.QtGui import QFontDatabase
        self.assertIn(self.view.familia, set(QFontDatabase.families()))

    def test_familia_resolvida_e_a_pedida(self):
        """QFontInfo revela a substituicao silenciosa; e o bug historico."""
        from PySide6.QtGui import QFontInfo
        self.assertEqual(QFontInfo(self.view.fonte_saida).family().lower(),
                         self.view.familia.lower())

    def test_familia_escolhida_e_monoespacada(self):
        from PySide6.QtGui import QFontMetricsF
        metrica = QFontMetricsF(self.view.fonte_saida)
        larguras = {metrica.horizontalAdvance(c) for c in ('0', 'W', 'i', '=', '~')}
        self.assertEqual(len(larguras), 1,
                         f"{self.view.familia} nao e monoespacada; o alinhamento "
                         "por contagem de caracteres depende disso")

    def test_glifo_de_reticencias_existe(self):
        """Se vier de fonte substituta, o truncamento desalinha."""
        from keybase.qt import fonte
        self.assertTrue(fonte.tem_reticencias(self.view.fonte_saida))

    def test_colunas_dentro_dos_limites(self):
        from keybase.qt.view import LARGURA_MAXIMA, LARGURA_MINIMA
        self.assertGreaterEqual(self.view.colunas(), LARGURA_MINIMA)
        self.assertLessEqual(self.view.colunas(), LARGURA_MAXIMA)

    def test_barras_ocupam_a_largura_exata(self):
        largura = self.view.colunas()
        barras = [l for l in self.tela().splitlines() if l.startswith("=")]
        self.assertTrue(barras, "a tela deve ter barras de '=' delimitando blocos")
        for linha in barras:
            self.assertEqual(len(linha), largura)

    def test_menu_no_formato_letra_traco_rotulo(self):
        self.digitar('?')   # o menu nasce escondido
        self.assertNaTela("P - Nova pasta")
        self.assertNaTela("N - Nova nota")
        self.assertNaTela("sair - Encerrar")

    def test_contadores_alinhados_a_direita(self):
        """Larguras diferentes de propósito ([9]:[9] vs [1]:[1]), senão o
        alinhamento passaria de graça."""
        self.criar_pasta("Curto")
        self.digitar('1')
        for i in range(9):
            self.criar_nota(f"n{i}")
        self.digitar('V')
        self.criar_pasta("Um nome bem mais comprido que o outro")
        self.digitar('2'); self.criar_nota("unica"); self.digitar('V')

        linhas = [l.rstrip() for l in self.tela().splitlines() if l.rstrip().endswith(']')]
        self.assertEqual(len(linhas), 2)
        self.assertIn("[9]:[9]", linhas[0])
        self.assertIn("[1]:[1]", linhas[1])
        self.assertEqual(len(linhas[0]), len(linhas[1]),
                         "os contadores devem terminar na mesma coluna")

    def test_nome_longo_e_truncado_sem_estourar(self):
        largura = self.view.colunas()
        self.criar_pasta("N" * 300)
        for linha in self.tela().splitlines():
            self.assertLessEqual(len(linha.rstrip()), largura)

    def test_breadcrumb_longo_colapsa_o_meio(self):
        from keybase.qt.layout import montar_breadcrumb
        from keybase.model import nova_raiz
        cadeia = [nova_raiz()] + [tree.novo_folder("Nivel " + "x" * 20) for _ in range(6)]
        texto = montar_breadcrumb(cadeia, 60)
        self.assertLessEqual(len(texto), 60)
        self.assertIn("…", texto)
        self.assertTrue(texto.startswith("~"))


class TestModosDeEdicao(BaseUI):
    """Os tres modos e a troca entre eles - o recurso novo deste port."""

    def abrir_editor(self, conteudo="# Titulo\n\ntexto do corpo"):
        self.criar_nota("Nota", conteudo)
        self.digitar('1')     # viewer
        self.digitar('E')     # editor
        return self.view.painel

    def test_abre_no_modo_editar(self):
        painel = self.abrir_editor()
        self.assertEqual(painel.modo(), 'editar')
        self.assertTrue(painel.editor.isVisibleTo(self.janela))
        self.assertFalse(painel.preview.isVisibleTo(self.janela))

    def test_ctrl_3_divide_a_tela(self):
        painel = self.abrir_editor()
        self.app.modo('dividido')
        self.assertEqual(painel.modo(), 'dividido')
        self.assertTrue(painel.editor.isVisibleTo(self.janela))
        self.assertTrue(painel.preview.isVisibleTo(self.janela))

    def test_ctrl_2_mostra_so_o_preview(self):
        painel = self.abrir_editor()
        self.app.modo('preview')
        self.assertFalse(painel.editor.isVisibleTo(self.janela))
        self.assertTrue(painel.preview.isVisibleTo(self.janela))

    def test_ctrl_e_cicla_os_tres(self):
        painel = self.abrir_editor()
        self.assertEqual(painel.modo(), 'editar')
        self.app.ciclar_modo(); self.assertEqual(painel.modo(), 'preview')
        self.app.ciclar_modo(); self.assertEqual(painel.modo(), 'dividido')
        self.app.ciclar_modo(); self.assertEqual(painel.modo(), 'editar')

    def test_preview_renderiza_texto_NAO_salvo(self):
        """E a razao de existir do recurso."""
        painel = self.abrir_editor("original")
        self.anexar_no_editor("\n\nlinha ainda nao salva")
        self.app.modo('preview')
        painel.forcar_render()
        self.assertIn("linha ainda nao salva", painel.preview.toPlainText())
        # e o disco continua com o original
        self.assertNotIn("nao salva", storage.carregar(self.arquivo).raiz.filhos[0].conteudo)

    def test_trocar_de_modo_preserva_texto_e_cursor(self):
        painel = self.abrir_editor("linha um\nlinha dois\nlinha tres")
        cursor = painel.editor.textCursor()
        cursor.setPosition(15)
        painel.editor.setTextCursor(cursor)
        texto_antes = painel.texto()
        posicao_antes = painel.editor.textCursor().position()

        self.app.modo('dividido')
        self.app.modo('preview')
        self.app.modo('editar')

        self.assertEqual(painel.texto(), texto_antes)
        self.assertEqual(painel.editor.textCursor().position(), posicao_antes)

    def test_markdown_completo_no_preview(self):
        painel = self.abrir_editor(
            "| a | b |\n|---|---|\n| 1 | 2 |\n\n- [x] feita\n\n~~cortado~~")
        self.app.modo('preview')
        painel.forcar_render()
        html = painel.preview.document().toHtml()
        self.assertIn('<table', html)
        texto = painel.preview.toPlainText()
        self.assertIn('☑', texto)
        self.assertIn('cortado', texto)

    def test_debounce_agrupa_digitacao(self):
        painel = self.abrir_editor()
        self.app.modo('dividido')
        painel.forcar_render()
        antes = painel._renders
        for i in range(5):
            self.anexar_no_editor(f"\nlinha {i}")
        # o timer ainda nao disparou: nenhuma renderizacao intermediaria
        self.assertEqual(painel._renders, antes)
        painel.forcar_render()
        self.assertEqual(painel._renders, antes + 1)

    def test_nao_renderiza_com_preview_oculto(self):
        painel = self.abrir_editor()
        antes = painel._renders
        for i in range(5):
            self.anexar_no_editor(f"\nlinha {i}")
        self.assertEqual(painel._renders, antes)

    def test_rolagem_do_preview_sobrevive_a_rerenderizacao(self):
        """Sem isto o preview salta para o topo a cada tecla.

        Feito no modo preview, nao no dividido: no dividido a sincronia
        editor->preview mexeria na rolagem de proposito, mascarando o que este
        teste mede.
        """
        painel = self.abrir_editor("\n\n".join(f"paragrafo {i}" for i in range(200)))
        self.app.modo('preview')
        painel.forcar_render()
        _app_qt().processEvents()

        barra = painel.preview.verticalScrollBar()
        if barra.maximum() == 0:
            self.skipTest("conteudo nao gerou rolagem no ambiente offscreen")
        barra.setValue(barra.maximum() // 2)
        fracao_antes = barra.value() / barra.maximum()

        self.digitar_no_editor(
            "\n\n".join(f"paragrafo {i}" for i in range(200)) + "\n\nmais um")
        painel.forcar_render()
        _app_qt().processEvents()

        fracao_depois = barra.value() / barra.maximum() if barra.maximum() else 0
        self.assertAlmostEqual(fracao_antes, fracao_depois, delta=0.15)

    def test_sincronia_de_rolagem_no_dividido(self):
        """Rolar o editor leva o preview junto, proporcionalmente."""
        painel = self.abrir_editor("\n\n".join(f"paragrafo {i}" for i in range(200)))
        self.app.modo('dividido')
        painel.forcar_render()
        _app_qt().processEvents()

        origem = painel.editor.verticalScrollBar()
        destino = painel.preview.verticalScrollBar()
        if origem.maximum() == 0 or destino.maximum() == 0:
            self.skipTest("conteudo nao gerou rolagem no ambiente offscreen")

        destino.setValue(0)
        origem.setValue(origem.maximum())
        _app_qt().processEvents()
        self.assertGreater(destino.value(), 0)

    def test_salvar_do_modo_dividido(self):
        painel = self.abrir_editor("antes")
        self.app.modo('dividido')
        self.digitar_no_editor("depois de editar no dividido")
        self.app.save()
        self.assertEqual(storage.carregar(self.arquivo).raiz.filhos[0].conteudo,
                         "depois de editar no dividido")
        self.assertEqual(self.nome_tela(), 'ViewerScreen')

    def test_nota_terminada_em_CTRL_S_sobrevive_no_dividido(self):
        """Regressao historica, agora tambem pelo caminho do modo dividido."""
        painel = self.abrir_editor("x")
        self.app.modo('dividido')
        self.digitar_no_editor("instrucoes\n\nCTRL_S")
        self.app.save()
        self.assertEqual(storage.carregar(self.arquivo).raiz.filhos[0].conteudo,
                         "instrucoes\n\nCTRL_S")

    def test_modo_persiste_na_config(self):
        self.abrir_editor()
        self.app.modo('dividido')
        self.assertEqual(self.config['editor']['modo'], 'dividido')

    def test_modo_persiste_entre_notas(self):
        self.abrir_editor()
        self.app.modo('dividido')
        self.app.save()
        self.digitar('')          # sai do viewer
        self.criar_pasta("outra") if False else None
        self.digitar('N'); self.digitar('Segunda nota')
        self.assertEqual(self.view.modo_edicao_atual(), 'dividido')

    def test_barra_de_dica_mostra_o_modo(self):
        self.abrir_editor()
        self.assertIn('[EDITAR]', self.view.edicao_modos.text())
        self.app.modo('dividido')
        self.assertIn('[DIVIDIDO]', self.view.edicao_modos.text())
        self.assertNotIn('[EDITAR]', self.view.edicao_modos.text())

    def test_cabecalho_do_editor_tem_modos_caminho_e_divisoria(self):
        from keybase.qt.theme import cores_markdown
        self.abrir_editor()
        self.assertTrue(self.view.cabecalho_edicao_widget.isVisibleTo(self.janela))
        self.assertIn(cores_markdown(self.config['theme'])['h1'],
                      self.view.edicao_modos.text())
        self.assertIn("Editando: ~ / Nota", self.view.edicao_caminho.text())
        divisoria = self.view.edicao_divisoria
        self.assertTrue(set(divisoria.text()) == {'='})
        # acompanha a janela: a largura do rotulo segue a da area, nao o texto
        self.assertLessEqual(divisoria.width(), self.janela.width())
        self.digitar('')  # Enter vazio na barra
        self.esc_no_editor()
        self.assertFalse(self.view.cabecalho_edicao_widget.isVisibleTo(self.janela))

    def test_esc_leva_o_cursor_para_a_barra_e_enter_volta(self):
        self.abrir_editor("original")
        self.view.focar_editor()
        self.assertTrue(self.view.foco_na_edicao())
        self.app.cancel()
        self.assertEqual(self.nome_tela(), 'EditorScreen')
        self.assertIs(_app_qt().focusWidget(), self.view.entrada)
        self.digitar('')
        self.assertTrue(self.view.foco_na_edicao())
        self.assertEqual(self.editor().toPlainText(), "original")

    def test_atalhos_de_modo_sao_inertes_fora_do_editor(self):
        """No-op na classe Screen: nenhum `if` na janela."""
        self.criar_pasta("Pasta")
        antes = self.tela()
        self.app.modo('dividido')
        self.app.modo('preview')
        self.app.ciclar_modo()
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertEqual(self.tela(), antes)
        self.assertIs(self.view.pilha.currentWidget(), self.view.out)

    def test_esc_no_dividido_com_alteracao_pede_confirmacao(self):
        self.abrir_editor("original")
        self.app.modo('dividido')
        self.anexar_no_editor(" alterado")
        self.esc_no_editor()
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')


class TestEditorComportamento(BaseUI):
    def abrir(self, conteudo=""):
        self.criar_nota("Nota", conteudo or "x")
        self.digitar('1'); self.digitar('E')
        return self.view.painel.editor

    def test_tab_insere_espacos(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        editor = self.abrir("")
        editor.setPlainText("")
        editor.setFocus()
        QTest.keyClick(editor, Qt.Key.Key_Tab)
        self.assertEqual(editor.toPlainText(), "    ")

    def test_enter_continua_lista(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QTextCursor
        from PySide6.QtTest import QTest
        editor = self.abrir()
        editor.setPlainText("- primeiro")
        editor.moveCursor(QTextCursor.MoveOperation.End)
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.assertEqual(editor.toPlainText(), "- primeiro\n- ")

    def test_enter_numera_lista_ordenada(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QTextCursor
        from PySide6.QtTest import QTest
        editor = self.abrir()
        editor.setPlainText("1. um")
        editor.moveCursor(QTextCursor.MoveOperation.End)
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.assertEqual(editor.toPlainText(), "1. um\n2. ")

    def test_enter_em_lista_vazia_encerra(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QTextCursor
        from PySide6.QtTest import QTest
        editor = self.abrir()
        editor.setPlainText("- ")
        editor.moveCursor(QTextCursor.MoveOperation.End)
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.assertEqual(editor.toPlainText(), "\n")

    def test_editor_mostra_markdown_cru(self):
        editor = self.abrir("# Titulo\n\n```python\nx = 1\n```")
        self.assertIn("```python", editor.toPlainText())
        self.assertIn("# Titulo", editor.toPlainText())

    def test_texto_e_round_trip_exato(self):
        """O editor nunca altera o conteudo do usuario."""
        original = "linha\ttab\n\n  espacos  \n\nCTRL_S"
        editor = self.abrir()
        editor.setPlainText(original)
        self.assertEqual(self.view.texto_editor(), original)


class TestRegressaoLayoutDoViewer(BaseUI):
    """O insertHtml deixa o cursor DENTRO do ultimo bloco do HTML.

    Sem abrir um bloco novo antes de escrever, a barra de '=' era anexada a
    esse bloco e herdava a fonte dele - uma barra em tamanho de cabecalho,
    estourando a largura e quebrando em duas linhas.
    """

    def ver_nota(self, conteudo):
        self.criar_nota("Nota", conteudo)
        self.digitar('1')

    def test_barra_depois_do_markdown_fica_na_propria_linha(self):
        self.ver_nota("# titulo\n\n## subtitulo")
        for linha in self.tela().splitlines():
            if '=' in linha:
                self.assertEqual(linha, '=' * len(linha),
                                 f"barra misturada com texto: {linha!r}")

    def test_nenhuma_linha_estoura_a_largura(self):
        self.ver_nota("# titulo\n\n## subtitulo\n\ntexto normal")
        largura = self.view.colunas()
        for linha in self.tela().splitlines():
            self.assertLessEqual(len(linha.rstrip()), largura,
                                 f"linha maior que colunas(): {linha!r}")

    def test_barras_tem_a_largura_exata_com_markdown(self):
        self.ver_nota("# titulo\n\n## subtitulo")
        largura = self.view.colunas()
        barras = [l for l in self.tela().splitlines() if l.startswith('=')]
        self.assertGreaterEqual(len(barras), 3)
        for barra in barras:
            self.assertEqual(len(barra), largura)

    def test_cabecalho_termina_antes_do_conteudo(self):
        self.ver_nota("# titulo")
        linhas = self.tela().splitlines()
        indice = next(i for i, l in enumerate(linhas) if l.strip() == 'titulo')
        self.assertTrue(linhas[indice - 1].startswith('='))

    def test_nota_vazia_nao_quebra(self):
        self.ver_nota("")
        largura = self.view.colunas()
        for linha in self.tela().splitlines():
            self.assertLessEqual(len(linha.rstrip()), largura)


class TestAtalhosMultiplataforma(BaseUI):
    """No macOS o Qt mapeia 'Ctrl+X' para Cmd+X, e o Ctrl FISICO nao dispara.

    Por isso as duas variantes sao registradas la. Foi o que fez Ctrl+1/2/3 e
    Ctrl+E nao funcionarem no Mac.
    """

    def test_variantes_no_macos_incluem_o_ctrl_fisico(self):
        import sys as _sys

        from PySide6.QtGui import QKeySequence

        from keybase.qt import atalhos
        variantes = atalhos.variantes('Ctrl+1')
        portaveis = [v.toString(QKeySequence.SequenceFormat.PortableText)
                     for v in variantes]
        self.assertIn('Ctrl+1', portaveis)
        if _sys.platform == 'darwin':
            self.assertIn('Meta+1', portaveis,
                          "no macOS o Ctrl fisico e 'Meta' para o Qt")
        else:
            self.assertEqual(len(variantes), 1)

    def test_atalho_sem_modificador_nao_ganha_variante(self):
        from keybase.qt import atalhos
        self.assertEqual(len(atalhos.variantes('Esc')), 1)

    def test_todos_os_modos_tem_atalho_registrado(self):
        from keybase.qt import atalhos
        for seq in (atalhos.SALVAR, atalhos.CANCELAR, atalhos.MODO_EDITAR,
                    atalhos.MODO_PREVIEW, atalhos.MODO_DIVIDIDO, atalhos.MODO_CICLAR,
                    atalhos.AJUDA_DINAMICA):
            self.assertTrue(atalhos.variantes(seq))

    def test_janela_registra_as_duas_variantes(self):
        from keybase.qt import atalhos
        sequencias = (atalhos.SALVAR, atalhos.CANCELAR, atalhos.MODO_EDITAR,
                      atalhos.MODO_PREVIEW, atalhos.MODO_DIVIDIDO,
                      atalhos.MODO_CICLAR, atalhos.AJUDA_DINAMICA)
        # conta pelas proprias variantes: o Esc nao duplica no macOS
        esperado = sum(len(atalhos.variantes(s)) for s in sequencias)
        self.assertEqual(len(self.janela._registrados), esperado)

    def test_rotulo_usa_a_convencao_da_plataforma(self):
        import sys as _sys

        from keybase.qt import atalhos
        # Ctrl em todas as plataformas: no macOS o Ctrl fisico funciona
        self.assertEqual(atalhos.rotulo(atalhos.SALVAR), 'Ctrl+S')
        self.assertEqual(atalhos.rotulo(atalhos.CANCELAR), 'Esc')

    def test_barra_de_dica_mostra_o_atalho_da_plataforma(self):
        from keybase.qt import atalhos
        self.criar_nota("Nota", "x")
        self.digitar('1'); self.digitar('E')
        self.digitar('?')   # os atalhos de modo ficam no menu
        self.assertIn(atalhos.rotulo(atalhos.MODO_DIVIDIDO), self.view.ajuda.text())

    def test_atalho_de_modo_dispara_pela_tecla(self):
        """Prova a fiacao de verdade, nao so a chamada direta a app.modo()."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.criar_nota("Nota", "x")
        self.digitar('1'); self.digitar('E')
        self.assertEqual(self.view.modo_edicao_atual(), 'editar')

        modificador = (Qt.KeyboardModifier.MetaModifier
                       if sys.platform == 'darwin'
                       else Qt.KeyboardModifier.ControlModifier)
        alvo = _app_qt().focusWidget() or self.janela
        QTest.keyClick(alvo, Qt.Key.Key_3, modificador)
        _app_qt().processEvents()
        self.assertEqual(self.view.modo_edicao_atual(), 'dividido')

    def test_atalho_de_modo_dispara_tambem_pela_variante_nativa(self):
        """No macOS, Cmd+3 e Ctrl+3 fisico devem valer os dois."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.criar_nota("Nota", "x")
        self.digitar('1'); self.digitar('E')
        alvo = _app_qt().focusWidget() or self.janela

        QTest.keyClick(alvo, Qt.Key.Key_2, Qt.KeyboardModifier.ControlModifier)
        _app_qt().processEvents()
        self.assertEqual(self.view.modo_edicao_atual(), 'preview')

    def test_esc_dispara_pela_tecla(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.criar_nota("Nota", "original")
        self.digitar('1'); self.digitar('E')
        self.anexar_no_editor(" alterado")
        alvo = _app_qt().focusWidget() or self.janela
        QTest.keyClick(alvo, Qt.Key.Key_Escape)
        _app_qt().processEvents()
        self.assertEqual(self.nome_tela(), 'EditorScreen')   # foi para a barra
        QTest.keyClick(_app_qt().focusWidget(), Qt.Key.Key_Escape)
        _app_qt().processEvents()
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')


class CofreMixin:
    """Senha de teste, scrypt barato e os passos de criar senha e cifrar nota."""
    SENHA = "segredo1"

    def setUp(self):
        from keybase import cripto
        self._n_original = cripto.SCRYPT_N
        cripto.SCRYPT_N = 2 ** 10   # scrypt barato: so os testes
        super().setUp()

    def tearDown(self):
        from keybase import cripto
        cripto.SCRYPT_N = self._n_original
        super().tearDown()

    def criar_senha(self):
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')
        self.assertNaTela("Não existe recuperação")
        self.digitar('S')
        self.assertTrue(self.app.atual.ENTRADA_SENHA)
        self.digitar(self.SENHA)
        self.digitar(self.SENHA)

    def nota_cifrada(self, nome="Banco", conteudo="pin sigiloso-kappa"):
        self.criar_nota(nome, conteudo)
        self.digitar('K1')
        self.criar_senha()
        if self.nome_tela() == 'ConfirmScreen':   # oferta de sanear backups
            self.digitar('S')
        return self.app.raiz.filhos[0]


class TestNotasCifradas(CofreMixin, BaseUI):
    def test_cifrar_nota_tira_o_texto_do_arquivo_e_dos_backups(self):
        nota = self.nota_cifrada()
        self.assertTrue(nota.cifrado)
        self.assertLinhaComFim("Banco", "[cifrada]")
        self.assertNotIn("sigiloso-kappa", self.arquivo.read_text(encoding='utf-8'))
        for _, arquivo in storage.backups_disponiveis(self.arquivo):
            self.assertNotIn("sigiloso-kappa", arquivo.read_text(encoding='utf-8'))

    def test_senha_curta_e_recusada(self):
        self.criar_nota("Banco", "x")
        self.digitar('K1')
        self.digitar('S')
        self.digitar('123')
        self.assertNaTela("pelo menos")
        self.assertEqual(self.view.entrada.text(), '')   # senha nao volta ao campo

    def test_senhas_diferentes_sao_recusadas(self):
        self.criar_nota("Banco", "x")
        self.digitar('K1')
        self.digitar('S')
        self.digitar(self.SENHA)
        self.digitar('outra-senha')
        self.assertNaTela("não conferem")
        self.assertIsNone(self.app.doc.cofre)

    def test_campo_mascarado_so_no_prompt_de_senha(self):
        from PySide6.QtWidgets import QLineEdit
        self.criar_nota("Banco", "x")
        self.digitar('K1')
        self.digitar('S')
        self.assertEqual(self.view.entrada.echoMode(), QLineEdit.EchoMode.Password)
        self.digitar('')   # cancela
        self.assertEqual(self.view.entrada.echoMode(), QLineEdit.EchoMode.Normal)

    def test_trancar_e_abrir_com_senha(self):
        self.nota_cifrada()
        self.digitar('T')
        self.assertIsNone(self.app.raiz.filhos[0].conteudo)
        self.digitar('1')
        self.assertEqual(self.nome_tela(), 'PromptScreen')
        self.digitar('errada')
        self.assertNaTela("Senha incorreta")
        self.digitar(self.SENHA)
        self.assertEqual(self.nome_tela(), 'ViewerScreen')
        self.assertNaTela("pin sigiloso-kappa")

    def test_auto_trancar_por_inatividade(self):
        import time
        self.nota_cifrada()
        self.assertFalse(self.app.verificar_auto_trancar())
        self.assertTrue(self.app.verificar_auto_trancar(agora=time.monotonic() + 3600))
        self.assertFalse(self.app.cofre_destravado)
        self.assertIsNone(self.app.raiz.filhos[0].conteudo)

    def test_auto_trancar_espera_o_editor(self):
        import time
        self.nota_cifrada()
        self.digitar('E1')
        self.assertEqual(self.nome_tela(), 'EditorScreen')
        self.assertFalse(self.app.verificar_auto_trancar(agora=time.monotonic() + 3600))
        self.assertTrue(self.app.cofre_destravado)

    def test_editar_nota_cifrada_grava_cifrado(self):
        self.nota_cifrada()
        self.digitar('E1')
        self.digitar_no_editor("novo pin sigiloso-omega")
        self.app.save()
        texto = self.arquivo.read_text(encoding='utf-8')
        self.assertNotIn("sigiloso-omega", texto)
        recarregado = storage.carregar(self.arquivo)
        self.assertTrue(recarregado.raiz.filhos[0].cifrado)

    def test_viewer_trancado_pede_senha_com_A(self):
        self.nota_cifrada()
        self.digitar('1')
        self.digitar('T')
        self.assertNaTela("Nota cifrada e trancada")
        self.digitar('A')
        self.digitar(self.SENHA)
        self.assertNaTela("pin sigiloso-kappa")

    def test_decifrar_nota(self):
        self.nota_cifrada()
        self.digitar('K1')
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')
        self.digitar('S')
        self.assertFalse(self.app.raiz.filhos[0].cifrado)
        self.assertIn("sigiloso-kappa", self.arquivo.read_text(encoding='utf-8'))

    def test_pasta_criada_cifrada_faz_notas_nascerem_cifradas(self):
        self.criar_pasta("Segredos", cifrada=True)
        self.criar_senha()
        pasta = self.app.raiz.filhos[0]
        self.assertTrue(pasta.nasce_cifrada)
        self.assertLinhaComFim("Segredos/", "[novas cifradas]")
        self.digitar('1')
        self.criar_nota("Cartao", "cvv sigiloso-sigma")
        nota = pasta.filhos[0]
        self.assertTrue(nota.cifrado)
        self.assertNotIn("sigiloso-sigma", self.arquivo.read_text(encoding='utf-8'))

    def test_pasta_padrao_nao_e_cifrada(self):
        self.criar_pasta("Comum")
        self.assertFalse(self.app.raiz.filhos[0].nasce_cifrada)
        self.assertIsNone(self.app.doc.cofre)

    def test_cifrar_pasta_em_lote(self):
        self.criar_pasta("Pai")
        self.digitar('1')
        self.criar_nota("A", "aaa")
        self.criar_pasta("Sub")
        self.digitar('1')
        self.criar_nota("B", "bbb")
        self.digitar('M')
        self.digitar('K1')
        self.digitar('1')          # cifrar as notas em claro
        self.assertNaTela("Cifrar 2 notas")
        self.digitar('S')
        self.criar_senha()
        if self.nome_tela() == 'ConfirmScreen':
            self.digitar('S')
        from keybase import cripto
        self.assertEqual(len(cripto.notas_cifradas(self.app.raiz)), 2)

    def test_ligar_nasce_cifrada_em_pasta_existente(self):
        self.criar_pasta("Pai")
        self.digitar('K1')
        self.digitar('2')
        self.criar_senha()
        self.assertTrue(self.app.raiz.filhos[0].nasce_cifrada)
        self.digitar('K1')
        self.digitar('2')
        self.assertFalse(self.app.raiz.filhos[0].nasce_cifrada)

    def test_prompt_de_alvo_lista_os_itens_com_numero_e_marca(self):
        self.nota_cifrada("Banco")
        self.criar_nota("Lista", "livre")
        self.digitar('K')
        self.assertEqual(self.nome_tela(), 'PromptScreen')
        self.assertLinhaComFim("1 - Banco", "[cifrada]")
        self.assertIn("2 - Lista", self.tela())


class TestDivisaoDoDividido(BaseUI):
    def test_alca_do_dividido_desenha_a_linha_de_divisao(self):
        from keybase.qt.painel_nota import LARGURA_ALCA
        from keybase.qt.theme import cores_interface
        splitter = self.view.painel.splitter
        self.assertEqual(splitter.handleWidth(), LARGURA_ALCA)
        self.assertIn(cores_interface(self.config['theme'])['separador'],
                      splitter.styleSheet())

    def test_menu_do_editor_tem_ctrl_0_a_3_a_esquerda_e_divisoria_abaixo(self):
        self.criar_nota("Nota", "x")
        self.digitar('E1')
        self.assertFalse(self.view.ajuda_divisoria.isVisibleTo(self.janela))
        self.digitar('?')
        linhas = self.view.ajuda.text().splitlines()
        esquerdas = [linha.split(' - ')[0].strip() for linha in linhas]
        self.assertEqual(esquerdas, ['Ctrl+0', 'Ctrl+1', 'Ctrl+2', 'Ctrl+3'])
        for linha, direita in zip(linhas, ('Ctrl+S', 'Esc', 'Ctrl+E', '??')):
            self.assertIn(f"{direita} - ", linha)
        self.assertTrue(self.view.ajuda_divisoria.isVisibleTo(self.janela))
        self.digitar('?')
        self.assertFalse(self.view.ajuda_divisoria.isVisibleTo(self.janela))

    def test_opcoes_da_pasta_ficam_em_linhas_separadas(self):
        self.criar_pasta("Pai")
        self.digitar('K1')
        linhas = self.tela().splitlines()
        self.assertTrue(any(l.startswith(" 1 - Cifrar as 0 notas") for l in linhas))
        self.assertTrue(any(l.startswith(" 2 - Notas novas nascem cifradas") for l in linhas))


class TestPastaCifrada(CofreMixin, BaseUI):

    def pasta_com_nota(self):
        self.criar_pasta("Pessoal")
        self.digitar('1')
        self.criar_nota("Banco", "pin sigiloso-kappa")
        self.digitar('M')

    def cifrar_pasta_1(self):
        self.digitar('K1')
        self.assertIn(" 3 - Cifrar a pasta inteira", self.tela())
        self.digitar('3')
        self.digitar('S')
        self.criar_senha()
        if self.nome_tela() == 'ConfirmScreen':   # backups
            self.assertNaTela("desta pasta")
            self.digitar('S')

    def test_cifrar_pasta_inteira(self):
        self.pasta_com_nota()
        self.cifrar_pasta_1()
        self.assertTrue(self.app.raiz.filhos[0].cifrada)
        self.assertLinhaComFim("Pessoal/", "[cifrada]:[1]:[1]")
        texto = self.arquivo.read_text(encoding='utf-8')
        self.assertNotIn("Banco", texto)
        self.assertNotIn("sigiloso-kappa", texto)
        for _, arquivo in storage.backups_disponiveis(self.arquivo):
            self.assertNotIn("Banco", arquivo.read_text(encoding='utf-8'))

    def test_trancada_some_a_contagem_e_entrar_pede_senha(self):
        self.pasta_com_nota()
        self.cifrar_pasta_1()
        self.digitar('T')
        self.assertLinhaComFim("Pessoal/", "[cifrada]")
        self.assertNaoNaTela("[1]:[1]")
        self.digitar('1')
        self.assertTrue(self.app.atual.ENTRADA_SENHA)
        self.digitar(self.SENHA)
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertIn("Banco", self.tela())
        self.digitar('1')                     # a nota de dentro nao pede de novo
        self.assertEqual(self.nome_tela(), 'ViewerScreen')
        self.assertNaTela("sigiloso-kappa")

    def test_trancar_dentro_da_pasta_volta_para_fora(self):
        self.pasta_com_nota()
        self.cifrar_pasta_1()
        self.digitar('1')
        self.assertIn("Banco", self.tela())
        self.digitar('T')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertNaoNaTela("Banco")
        self.assertTrue(self.app.raiz.filhos[0].trancada)

    def test_mudanca_dentro_da_pasta_e_gravada_cifrada(self):
        self.pasta_com_nota()
        self.cifrar_pasta_1()
        self.digitar('1')
        self.criar_nota("Cartao", "cvv sigiloso-sigma")
        self.assertNotIn("sigiloso-sigma", self.arquivo.read_text(encoding='utf-8'))
        recarregado = storage.carregar(self.arquivo)
        from keybase import cripto
        c = cripto.Cofre.from_dict(recarregado.cofre)
        c.destravar(self.SENHA)
        cripto.destravar_arvore(recarregado.raiz, c)
        nomes = [f.nome for f in recarregado.raiz.filhos[0].filhos]
        self.assertIn("Cartao", nomes)

    def test_dentro_da_pasta_cifrada_nada_se_cifra_de_novo(self):
        self.pasta_com_nota()
        self.cifrar_pasta_1()
        self.digitar('1')
        self.digitar('K1')
        self.assertNaTela("já é protegido pela pasta cifrada")
        self.digitar('P')
        self.digitar('Sub')          # sem a pergunta "nascem cifradas?"
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertIn("Sub/", self.tela())

    def test_decifrar_pasta(self):
        self.pasta_com_nota()
        self.cifrar_pasta_1()
        self.digitar('K1')
        self.assertIn(" 1 - Decifrar a pasta", self.tela())
        self.digitar('1')
        self.digitar('S')
        self.assertFalse(self.app.raiz.filhos[0].cifrada)
        self.assertIn("Banco", self.arquivo.read_text(encoding='utf-8'))

    def test_marcas_das_duas_pastas_sao_diferentes(self):
        self.criar_pasta("Projetos", cifrada=True)
        self.criar_senha()
        self.assertLinhaComFim("Projetos/", "[novas cifradas]")
        self.digitar('1')
        self.criar_nota("A", "x")
        self.digitar('V')
        self.assertLinhaComFim("Projetos/", "[novas cifradas]:[1]:[1]")

    def test_t_trancado_pede_a_senha_e_destranca(self):
        self.pasta_com_nota()
        self.cifrar_pasta_1()
        self.digitar('T')
        self.assertFalse(self.app.cofre_destravado)
        self.digitar('T')
        self.assertTrue(self.app.atual.ENTRADA_SENHA)
        self.digitar(self.SENHA)
        self.assertTrue(self.app.cofre_destravado)
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertNaTela("destrancados")
        self.assertLinhaComFim("Pessoal/", "[cifrada]:[1]:[1]")

    def test_t_sem_nada_cifrado_avisa_e_fica_fora_do_menu(self):
        self.digitar('T')
        self.assertNaTela("Ainda não há nada cifrado")
        self.digitar('?')
        self.assertNaoNaTela("Trancar/destrancar")


class TestConfiguracao(BaseUI):
    def abrir_config(self):
        from keybase import config
        self.arquivo_config.write_text(config.modelo_toml(), encoding='utf-8')
        self.digitar('C')
        self.assertEqual(self.nome_tela(), 'ConfigScreen')

    def test_p_cria_pasta_e_c_abre_a_configuracao(self):
        self.digitar('?')
        self.assertNaTela("P - Nova pasta")
        self.assertNaTela("C - Configuração")
        self.abrir_config()
        self.assertIn('tema = "dark"', self.editor().toPlainText())
        self.assertIn("[CONFIGURAÇÃO]", self.view.edicao_modos.text())
        self.assertIn("keybase_config.toml", self.view.edicao_caminho.text())

    def test_salvar_com_erro_nao_grava_nem_sai(self):
        self.abrir_config()
        original = self.arquivo_config.read_text(encoding='utf-8')
        self.digitar_no_editor('tema = "azul"\n')
        self.app.save()
        self.assertEqual(self.nome_tela(), 'ConfigScreen')
        self.assertTrue(self.view.edicao_erro.isVisibleTo(self.janela))
        self.assertIn('tema deveria ser', self.view.edicao_erro.text())
        self.assertEqual(self.arquivo_config.read_text(encoding='utf-8'), original)

    def test_salvar_valido_grava_volta_e_troca_o_tema_na_hora(self):
        from keybase.qt.theme import cores_interface
        self.abrir_config()
        texto = self.editor().toPlainText().replace('tema = "dark"', 'tema = "light"')
        texto = texto.replace('trancar_apos_min = 10', 'trancar_apos_min = 2')
        self.config['theme'] = 'dark'
        self.janela.aplicar_tema('dark')
        self.digitar_no_editor(texto)
        self.app.save()
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertNaTela("Configuração salva.")
        self.assertEqual(self.arquivo_config.read_text(encoding='utf-8'), texto)
        self.assertEqual(self.config['theme'], 'light')
        self.assertIn(cores_interface('light')['fundo'], self.janela.styleSheet())
        self.assertEqual(self.config['cofre']['auto_lock_min'], 2)

    def test_mudar_fonte_avisa_que_vale_ao_reabrir(self):
        self.abrir_config()
        texto = self.editor().toPlainText().replace('tamanho_saida = 14',
                                                    'tamanho_saida = 16')
        self.digitar_no_editor(texto)
        self.app.save()
        self.assertNaTela("Fontes mudam ao reabrir")

    def test_comentario_nao_ganha_estilo_de_titulo(self):
        self.abrir_config()
        self.assertIsNone(self.editor().realce.document())

    def test_nota_depois_da_config_volta_a_ter_realce(self):
        self.abrir_config()
        self.digitar('')          # Enter vazio: volta ao texto
        self.esc_no_editor()      # sem alteracao: sai direto
        self.criar_nota("Nota", "# titulo")
        self.digitar('1'); self.digitar('E')
        self.assertIs(self.editor().realce.document(), self.editor().document())

    def test_atalhos_de_modo_sao_inertes_na_config(self):
        self.abrir_config()
        self.app.modo('dividido')
        self.assertEqual(self.view.modo_edicao_atual(), 'editar')
        self.digitar('?')
        self.assertNotIn("Dividido", self.view.ajuda.text())
        self.assertIn("Validar, salvar e aplicar", self.view.ajuda.text())

    def test_esc_com_alteracao_pergunta_antes_de_descartar(self):
        self.abrir_config()
        self.anexar_no_editor("\n# mudei")
        self.esc_no_editor()
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')
        self.assertNaTela("keybase_config.toml")


class TestAvisoNoLugarDoCaminho(BaseUI):
    def primeiras_linhas(self):
        return [l for l in self.tela().splitlines() if l.strip()][:3]

    def test_aviso_ocupa_a_linha_do_caminho_sem_bloco_extra(self):
        self.digitar('V')   # na raiz: "Voce ja esta na raiz..."
        linhas = self.primeiras_linhas()
        self.assertIn("Você já está na raiz", linhas[1])
        self.assertNotIn("~", linhas[1])
        self.assertTrue(set(linhas[2].strip()) == {'='})   # logo a barra: sem bloco a mais
        self.assertEqual(sum(1 for l in self.tela().splitlines() if l.startswith("==")), 3)

    def test_caminho_volta_sozinho_depois_do_tempo(self):
        from PySide6.QtTest import QTest
        self.config['interface']['flash_ms'] = 30
        self.digitar('V')
        self.assertNaTela("Você já está na raiz")
        QTest.qWait(150)
        self.assertNaoNaTela("Você já está na raiz")
        self.assertEqual(self.primeiras_linhas()[1].strip(), "~")

    def test_aviso_no_viewer_tambem_troca_o_caminho(self):
        self.criar_nota("Nota", "x")
        self.digitar('1')
        self.digitar('R')
        self.digitar('Outra')
        linhas = self.primeiras_linhas()
        self.assertIn("Renomeado", linhas[1])
        self.app._fim_do_flash()
        self.assertIn("~ / Outra", self.primeiras_linhas()[1])

    def test_fim_do_aviso_em_outra_tela_nao_repinta(self):
        self.digitar('V')
        self.digitar('P')   # prompt de nova pasta por cima
        self.view.entrada.setText("digitando")
        self.app._fim_do_flash()
        self.assertEqual(self.nome_tela(), 'PromptScreen')
        self.assertEqual(self.view.entrada.text(), "digitando")

    def test_aviso_longo_usa_o_proprio_tempo_e_nao_corta_em_uma_linha(self):
        self.config['interface']['flash_longo_ms'] = 1234
        self.assertEqual(self.app.duracao_flash_ms(longo=True), 1234)
        texto = "palavra " * 40
        self.app.flash(texto, longo=True)
        self.assertGreater(len(self.app._flash), self.view.colunas())
        self.app.flash(texto)
        self.assertLess(len(self.app._flash), self.view.colunas())

    def test_aviso_longo_com_tempo_zero_fica_ate_o_enter(self):
        from PySide6.QtTest import QTest
        self.config['interface']['flash_longo_ms'] = 0
        self.config['interface']['flash_ms'] = 30
        self.criar_nota("Nota", "x")
        self.app.flash("Aviso para ler com calma.", longo=True)
        self.app.rerender()
        QTest.qWait(150)
        self.assertNaTela("Aviso para ler com calma.")
        self.app._fim_do_flash()   # timer atrasado de um aviso anterior
        self.assertNaTela("Aviso para ler com calma.")
        self.app.rerender()        # reajuste da janela: o aviso continua
        self.assertNaTela("Aviso para ler com calma.")
        self.digitar('')           # ENTER vazio: so tira o aviso
        self.assertNaoNaTela("Aviso para ler com calma.")
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertIn("Nota", self.tela())

    def test_aviso_fixo_sai_com_um_comando_que_segue_normal(self):
        self.config['interface']['flash_longo_ms'] = 0
        self.criar_nota("Nota", "x")
        self.app.flash("Aviso fixo.", longo=True)
        self.app.rerender()
        self.digitar('1')
        self.assertEqual(self.nome_tela(), 'ViewerScreen')
        self.assertNaoNaTela("Aviso fixo.")
        self.digitar('')           # sem aviso: ENTER volta, como sempre
        self.assertEqual(self.nome_tela(), 'BrowserScreen')

    def test_aviso_curto_ignora_o_tempo_zero_do_longo(self):
        from PySide6.QtTest import QTest
        self.config['interface']['flash_longo_ms'] = 0
        self.config['interface']['flash_ms'] = 30
        self.digitar('V')
        QTest.qWait(150)
        self.assertNaoNaTela("Você já está na raiz")

    def test_tempo_zero_so_vale_para_o_aviso_longo(self):
        from keybase import config
        base = config.modelo_toml()
        _, erros = config.validar_texto(
            base.replace('tempo_aviso_longo_ms = 8000', 'tempo_aviso_longo_ms = 0'))
        self.assertEqual(erros, [])
        _, erros = config.validar_texto(
            base.replace('tempo_aviso_longo_ms = 8000', 'tempo_aviso_longo_ms = 100'))
        self.assertTrue(erros)
        _, erros = config.validar_texto(
            base.replace('tempo_aviso_ms = 2500', 'tempo_aviso_ms = 0'))
        self.assertTrue(erros)

    def test_tempo_do_aviso_vem_da_configuracao(self):
        from keybase import config
        texto = config.modelo_toml().replace('tempo_aviso_ms = 2500', 'tempo_aviso_ms = 800')
        usuario, erros = config.validar_texto(texto)
        self.assertEqual(erros, [])
        self.app.aplicar_config(usuario)
        self.assertEqual(self.app.duracao_flash_ms(), 800)


class TestKeybaseDoc(BaseUI):
    def nomes_na_raiz(self):
        return [n.nome for n in self.app.raiz.filhos]

    def test_criada_na_raiz_na_primeira_vez(self):
        self.app.garantir_doc()
        self.assertEqual(self.nomes_na_raiz(), ["Keybase Doc"])
        self.assertTrue(self.config['doc_criada'])
        self.assertTrue(self.app.raiz.filhos[0].conteudo.startswith("# Keybase Doc"))

    def test_apagada_nao_volta(self):
        self.app.garantir_doc()
        tree.remover(self.app.raiz, self.app.raiz.filhos[0])
        self.app.garantir_doc()
        self.assertEqual(self.nomes_na_raiz(), [])

    def test_nome_ja_ocupado_so_marca(self):
        self.criar_nota("keybase doc", "minha")
        self.app.garantir_doc()
        self.assertEqual(self.nomes_na_raiz(), ["keybase doc"])
        self.assertTrue(self.config['doc_criada'])

    def test_marca_sobrevive_ao_reabrir(self):
        from keybase import config
        caminho = Path(self.dir) / 'estado.json'
        self.config['doc_criada'] = True
        config.salvar_estado(self.config, '800x600', caminho)
        self.assertTrue(config._carregar_estado(caminho)['doc_criada'])

    def test_renderiza_e_os_links_entre_notas_funcionam(self):
        self.app.garantir_doc()
        self.app.rerender()   # no app, garantir_doc roda antes do primeiro render
        self.digitar('1')
        self.assertEqual(self.nome_tela(), 'ViewerScreen')
        html = self.view.out.toHtml()
        self.assertIn('href="kb:Keybase%20Doc"', html)
        self.assertNotIn("line-through", html)   # nenhum [[link]] quebrado
        for secao in ("Navegação", "Notas e pastas cifradas", "Configuração", "Dicas"):
            self.assertIn(secao, html)


class TestConfiguracaoAntiga(BaseUI):
    def test_opcoes_novas_aparecem_no_editor_mas_so_gravam_com_ctrl_s(self):
        from keybase import config
        antigo = TestConfigTextos.sem_aviso(config.modelo_toml())
        self.arquivo_config.write_text(antigo, encoding='utf-8')
        self.digitar('C')
        self.assertIn("tempo_aviso_ms = 2500", self.editor().toPlainText())
        self.assertTrue(self.view.edicao_aviso.isVisibleTo(self.janela))
        self.assertIn("interface.tempo_aviso_ms", self.view.edicao_aviso.text())
        self.assertEqual(self.arquivo_config.read_text(encoding='utf-8'), antigo)
        self.app.save()
        self.assertIn("tempo_aviso_ms = 2500",
                      self.arquivo_config.read_text(encoding='utf-8'))


class TestConfigTextos:
    @staticmethod
    def sem_aviso(texto):
        return texto.replace(
            '# Quanto tempo um aviso ("Pasta criada.", "Itens cifrados trancados.") fica no\n'
            '# lugar do caminho antes de sumir, em milissegundos (2500 = 2,5 s). Aplica na hora.\n'
            'tempo_aviso_ms = 2500\n', '')


class TestFase1(CofreMixin, BaseUI):
    NOTA = "# Comandos\n\n```sh\nls -la\n```\n\n```python\nprint('oi')\n```\n"

    def copiado(self):
        return _app_qt().clipboard().text()

    # --- copiar --------------------------------------------------------------

    def test_y_numero_copia_o_bloco(self):
        self.criar_nota("Cmd", self.NOTA)
        self.digitar('1')
        self.digitar('Y2')
        self.assertEqual(self.copiado(), "print('oi')")
        self.assertNaTela("Copiado: bloco 2")

    def test_y_sem_numero_lista_os_blocos_um_por_linha(self):
        self.criar_nota("Cmd", self.NOTA)
        self.digitar('1')
        self.digitar('Y')
        linhas = [l.strip() for l in self.tela().splitlines()]
        self.assertIn("0 - A nota inteira", linhas)
        self.assertIn("1 - sh (1 linha): ls -la", linhas)
        self.digitar('0')
        self.assertEqual(self.copiado(), self.NOTA)

    def test_y_numa_nota_sem_blocos_copia_a_nota(self):
        self.criar_nota("Simples", "so texto")
        self.digitar('1')
        self.digitar('Y')
        self.assertEqual(self.copiado(), "so texto")

    def test_y_na_lista_copia_para_outra_pasta_e_mantem_o_original(self):
        self.criar_pasta("Destino")
        self.criar_nota("Cmd", self.NOTA)
        self.digitar('Y2')
        self.assertEqual(self.nome_tela(), 'DestinoScreen')
        self.assertIn("   C - Copiar para cá", self.tela())
        self.digitar('1'); self.digitar('C')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertNaTela("copiado para ~ / Destino")
        destino = self.app.raiz.filhos[0]
        self.assertEqual([f.conteudo for f in destino.filhos], [self.NOTA])
        self.assertIn("Cmd", [f.nome for f in self.app.raiz.filhos])   # original fica
        self.assertNotEqual(destino.filhos[0].id,
                            next(f for f in self.app.raiz.filhos if f.nome == "Cmd").id)

    def test_copiar_pasta_para_outra_pasta(self):
        self.criar_pasta("A")
        self.digitar('1')
        self.criar_nota("n", "x")
        self.digitar('M')
        self.criar_pasta("B")
        self.digitar('Y1')
        self.digitar('1')    # a propria A nao aparece como destino: B e o 1
        self.digitar('C')
        b = next(f for f in self.app.raiz.filhos if f.nome == "B")
        self.assertEqual([f.nome for f in b.filhos], ["A"])
        self.assertEqual(b.filhos[0].filhos[0].conteudo, "x")

    def test_copiar_na_mesma_pasta_vira_copia(self):
        self.criar_nota("Cmd", "x")
        self.digitar('Y1'); self.digitar('C')
        self.assertEqual(sorted(f.nome for f in self.app.raiz.filhos), ["Cmd", "Cmd (cópia)"])

    def test_copiar_desfaz_com_u(self):
        self.criar_pasta("Destino")
        self.criar_nota("Cmd", "x")
        self.digitar('Y2'); self.digitar('1'); self.digitar('C')
        self.digitar('U')
        self.assertEqual(self.app.raiz.filhos[0].filhos, [])

    def test_copiar_nota_cifrada_recifra_a_copia(self):
        self.nota_cifrada("Banco", "pin sigiloso-kappa")   # K1: a nota e o item 1
        self.criar_pasta("Destino")
        self.digitar('Y2'); self.digitar('1'); self.digitar('C')
        destino = next(f for f in self.app.raiz.filhos if f.nome == "Destino")
        copia = destino.filhos[0]
        self.assertTrue(copia.cifrado)
        self.assertEqual(self.app.cofre.decifrar(copia.blob, copia.id), "pin sigiloso-kappa")
        self.assertNotIn("sigiloso-kappa", self.arquivo.read_text(encoding='utf-8'))

    def test_copiar_para_fora_da_pasta_cifrada_pede_confirmacao(self):
        self.criar_pasta("Cofre")
        self.digitar('1')
        self.criar_nota("Banco", "x")
        self.digitar('M')
        self.digitar('K1'); self.digitar('3'); self.digitar('S')
        self.criar_senha()
        if self.nome_tela() == 'ConfirmScreen':
            self.digitar('S')
        self.digitar('1')
        self.digitar('Y1'); self.digitar('M'); self.digitar('C')
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')
        self.assertNaTela("fica fora da pasta cifrada")

    def test_rotulo_na_nota_e_area_de_transferencia(self):
        self.criar_nota("Cmd", "x")
        self.digitar('1')
        self.digitar('?')
        self.assertNaTela("Y - Área de transferência")

    def test_bloco_inexistente_avisa(self):
        self.criar_nota("Cmd", self.NOTA)
        self.digitar('1')
        self.digitar('Y9')
        self.assertNaTela("A nota tem 2 blocos de código")

    def test_copia_cifrada_e_limpa_depois(self):
        from PySide6.QtTest import QTest
        self.config['cofre']['clip_seg'] = 1
        self.nota_cifrada("Banco", "pin sigiloso-kappa")
        self.digitar('1')
        self.digitar('Y')
        self.assertEqual(self.copiado(), "pin sigiloso-kappa")
        self.assertNaTela("(limpa em 1 s)")
        QTest.qWait(1300)
        self.assertEqual(self.copiado(), "")

    def test_limpeza_nao_apaga_o_que_o_usuario_copiou_depois(self):
        self.nota_cifrada("Banco", "pin sigiloso-kappa")
        self.digitar('1')
        self.digitar('Y')
        self.assertEqual(self.copiado(), "pin sigiloso-kappa")
        _app_qt().clipboard().setText("outra coisa")
        self.app.limpar_copia_sensivel()
        self.assertEqual(self.copiado(), "outra coisa")

    # --- mover ---------------------------------------------------------------

    def test_mover_para_outra_pasta(self):
        self.criar_pasta("Destino")
        self.criar_nota("Nota", "x")
        self.digitar('X2')
        self.assertEqual(self.nome_tela(), 'DestinoScreen')
        self.assertIn("   C - Mover para cá", self.tela())
        self.digitar('1')          # entra em Destino
        self.digitar('C')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertNaTela("movido para ~ / Destino")
        destino = self.app.raiz.filhos[0]
        self.assertEqual([f.nome for f in destino.filhos], ["Nota"])

    def test_pasta_movida_nao_aparece_como_destino(self):
        self.criar_pasta("A")
        self.criar_pasta("B")
        self.digitar('X1')
        self.assertNotIn(" - A/", self.tela())
        self.assertIn(" - B/", self.tela())

    def test_mover_para_a_mesma_pasta_avisa(self):
        self.criar_nota("Nota", "x")
        self.digitar('X1')
        self.digitar('C')
        self.assertNaTela("já está nesta pasta")

    def test_nome_repetido_no_destino_e_recusado(self):
        self.criar_pasta("Destino")
        self.digitar('1')
        self.criar_nota("Nota", "dentro")
        self.digitar('M')
        self.criar_nota("Nota", "fora")
        self.digitar('X2')
        self.digitar('1')
        self.digitar('C')
        self.assertNaTela("Já existe um item chamado 'Nota'")

    def test_enter_vazio_sobe_e_na_raiz_cancela(self):
        self.criar_pasta("A")
        self.digitar('1')
        self.criar_nota("Nota", "x")
        self.digitar('X1')
        self.digitar('')
        self.assertEqual(self.nome_tela(), 'DestinoScreen')
        self.assertIn(" ~\n", self.tela())
        self.digitar('')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')

    def test_mover_para_pasta_cifrada_decifra_a_nota(self):
        self.criar_pasta("Cofre")
        self.digitar('K1'); self.digitar('3'); self.digitar('S')
        self.criar_senha()
        if self.nome_tela() == 'ConfirmScreen':
            self.digitar('S')
        self.criar_nota("Banco", "pin sigiloso-kappa")
        self.digitar('K2')                      # nota cifrada por si
        if self.nome_tela() == 'ConfirmScreen':
            self.digitar('S')
        self.digitar('X2'); self.digitar('1'); self.digitar('C')
        nota = self.app.raiz.filhos[0].filhos[0]
        self.assertFalse(nota.cifrado)          # a pasta ja protege
        self.assertNotIn("sigiloso-kappa", self.arquivo.read_text(encoding='utf-8'))

    def test_sair_da_pasta_cifrada_pede_confirmacao(self):
        self.criar_pasta("Cofre")
        self.digitar('1')
        self.criar_nota("Banco", "x")
        self.digitar('M')
        self.digitar('K1'); self.digitar('3'); self.digitar('S')
        self.criar_senha()
        if self.nome_tela() == 'ConfirmScreen':
            self.digitar('S')
        self.digitar('1')
        self.digitar('X1'); self.digitar('M'); self.digitar('C')
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')
        self.assertNaTela("sai da pasta cifrada")

    # --- duplicar ------------------------------------------------------------

    def test_duplicar_nota(self):
        self.criar_nota("Nota", "x")
        self.digitar('Z1')
        nomes = sorted(f.nome for f in self.app.raiz.filhos)
        self.assertEqual(nomes, ["Nota", "Nota (cópia)"])
        self.assertNaTela("duplicado como 'Nota (cópia)'")

    def test_duplicar_nota_cifrada_trancada_pede_senha(self):
        self.nota_cifrada("Banco", "pin sigiloso-kappa")
        self.digitar('T')
        self.digitar('Z1')
        self.assertTrue(self.app.atual.ENTRADA_SENHA)
        self.digitar(self.SENHA)
        copia = next(f for f in self.app.raiz.filhos if f.nome == "Banco (cópia)")
        self.assertTrue(copia.cifrado)
        self.assertEqual(self.app.cofre.decifrar(copia.blob, copia.id), "pin sigiloso-kappa")

    # --- trocar senha --------------------------------------------------------

    def test_trocar_senha(self):
        self.nota_cifrada()
        self.digitar('S')
        self.digitar('errada')
        self.assertNaTela("Senha incorreta")
        self.digitar(self.SENHA)
        self.digitar('curta')
        self.assertNaTela("pelo menos")
        self.digitar('novinha1')
        self.digitar('novinha1')
        self.assertNaTela("Senha mestra trocada")
        from keybase import cripto
        recarregado = storage.carregar(self.arquivo)
        cofre = cripto.Cofre.from_dict(recarregado.cofre)
        cofre.destravar('novinha1')

    def test_s_sem_senha_fica_fora_do_menu(self):
        self.digitar('?')
        self.assertNaoNaTela("Trocar senha")


class TestFase2(CofreMixin, BaseUI):
    def setUp(self):
        super().setUp()
        self.app.pasta_exportacao = self.dir   # nunca exporta para o Downloads real

    # --- desfazer ------------------------------------------------------------

    def test_desfazer_apagar(self):
        self.criar_nota("Nota", "x")
        self.digitar('D1'); self.digitar('S')
        self.assertEqual(self.app.raiz.filhos, [])
        self.digitar('U')
        self.assertEqual([f.nome for f in self.app.raiz.filhos], ["Nota"])
        self.assertNaTela("Desfeito: apagar 'Nota'")
        self.assertEqual(storage.carregar(self.arquivo).raiz.filhos[0].nome, "Nota")

    def test_desfazer_em_sequencia(self):
        self.criar_nota("A", "x")
        self.digitar('R1'); self.digitar('B')
        self.digitar('Z1')
        self.digitar('U')
        self.digitar('U')
        self.assertEqual([f.nome for f in self.app.raiz.filhos], ["A"])

    def test_editar_depois_zera_o_desfazer(self):
        """Senao o U restauraria a arvore velha por cima da edicao."""
        self.criar_nota("A", "x")
        self.criar_nota("B", "y")
        self.digitar('D1'); self.digitar('S')
        self.digitar('E1')
        self.digitar_no_editor("editado")
        self.app.save()
        self.assertFalse(self.app.pode_desfazer)
        self.digitar('U')
        self.assertNaTela("Nada para desfazer")
        self.assertEqual(self.app.raiz.filhos[0].conteudo, "editado")

    def test_u_fica_fora_do_menu_sem_nada_para_desfazer(self):
        self.digitar('?')
        self.assertNaoNaTela("U - Desfazer")

    def test_desfazer_decifrar_volta_cifrada_e_aberta(self):
        self.nota_cifrada("Banco", "pin sigiloso-kappa")
        self.digitar('K1'); self.digitar('S')
        self.assertFalse(self.app.raiz.filhos[0].cifrado)
        self.digitar('U')
        nota = self.app.raiz.filhos[0]
        self.assertTrue(nota.cifrado)
        self.assertEqual(nota.conteudo, "pin sigiloso-kappa")
        self.assertNotIn("sigiloso-kappa", self.arquivo.read_text(encoding='utf-8'))

    # --- conflito ------------------------------------------------------------

    def gravar_de_fora(self):
        outro = storage.carregar(self.arquivo)
        tree.adicionar(outro.raiz, tree.novo_folder("De la"))
        storage.salvar(outro, self.arquivo)

    def test_conflito_mostra_a_escolha_e_guarda_a_copia(self):
        self.criar_pasta("Daqui")
        self.gravar_de_fora()
        self.criar_pasta("Outra daqui")
        self.assertTrue(getattr(self.app.atual, 'conflito', False))
        linhas = [l.strip() for l in self.tela().splitlines()]
        self.assertTrue(any(l.startswith("1 - Recarregar") for l in linhas))
        self.assertTrue(any(l.startswith("2 - Gravar") for l in linhas))
        self.assertEqual(len(list(self.dir.glob('keybase_data.conflito-*.json'))), 1)

    def test_conflito_recarregar(self):
        self.criar_pasta("Daqui")
        self.gravar_de_fora()
        self.criar_pasta("Outra daqui")
        self.digitar('1')
        nomes = sorted(f.nome for f in self.app.raiz.filhos)
        self.assertEqual(nomes, ["Daqui", "De la"])

    def test_conflito_gravar_por_cima(self):
        self.criar_pasta("Daqui")
        self.gravar_de_fora()
        self.criar_pasta("Outra daqui")
        self.digitar('2')
        nomes = sorted(f.nome for f in storage.carregar(self.arquivo).raiz.filhos)
        self.assertEqual(nomes, ["Daqui", "Outra daqui"])

    def test_conflito_ao_salvar_nota_nao_some_com_o_pop(self):
        self.criar_nota("Nota", "x")
        self.gravar_de_fora()
        self.digitar('E1')
        self.digitar_no_editor("mudei")
        self.app.save()
        self.assertTrue(getattr(self.app.atual, 'conflito', False))

    # --- exportar ------------------------------------------------------------

    def test_exportar_a_raiz(self):
        self.criar_pasta("Vscode")
        self.digitar('1')
        self.criar_nota("Ctrl + P", "abre")
        self.digitar('M')
        self.digitar('W')
        self.assertNaTela("1 notas exportadas")
        saidas = list(self.dir.glob('KeyBase-export-*'))
        self.assertEqual(len(saidas), 1)
        self.assertEqual((saidas[0] / 'Vscode' / 'Ctrl + P.md').read_text(encoding='utf-8'),
                         "abre")

    def test_exportar_com_cifrados_pergunta(self):
        self.nota_cifrada("Banco", "pin sigiloso-kappa")
        self.criar_nota("Livre", "x")
        self.digitar('W')
        linhas = [l.strip() for l in self.tela().splitlines()]
        self.assertIn("1 - Pular os cifrados", linhas)
        self.digitar('1')
        saida = next(self.dir.glob('KeyBase-export-*'))
        self.assertEqual(sorted(p.name for p in saida.iterdir()), ["Livre.md"])
        self.assertNaTela("1 cifradas puladas")


class TestFase3(CofreMixin, BaseUI):
    # --- favoritos e recentes -----------------------------------------------

    def test_favoritar_marca_na_lista_e_aparece_no_l(self):
        self.criar_pasta("Vscode")
        self.digitar('1')
        self.criar_nota("Ctrl + P", "abre")
        self.digitar('F1')
        self.assertLinhaComFim("Ctrl + P", "[favorito]")
        self.digitar('L')
        self.assertEqual(self.nome_tela(), 'FavoritosScreen')
        linhas = [l.strip() for l in self.tela().splitlines()]
        self.assertIn("1 - Ctrl + P", linhas)
        self.assertIn("Vscode", linhas)                  # o caminho embaixo

    def test_abrir_do_l_monta_a_pilha_do_caminho(self):
        self.criar_pasta("Vscode")
        self.digitar('1')
        self.criar_nota("Ctrl + P", "abre")
        self.digitar('F1')
        self.digitar('M')
        self.digitar('L')
        self.digitar('1')
        self.assertEqual(self.nome_tela(), 'ViewerScreen')
        self.digitar('V')
        self.assertIn("~ / Vscode", self.tela())         # voltar percorre a arvore

    def test_recentes_sao_as_notas_abertas(self):
        self.criar_nota("A", "x")
        self.criar_nota("B", "y")
        self.digitar('1')
        self.digitar('V')
        self.digitar('2')
        self.digitar('V')
        self.assertEqual([self.app.no(i).nome for i in self.app.recentes()], ["B", "A"])
        self.digitar('L')
        self.assertLess(self.tela().index("1 - B"), self.tela().index("2 - A"))

    def test_marca_de_favorito_com_cifrada(self):
        self.nota_cifrada("Banco", "x")
        self.digitar('F1')
        self.assertLinhaComFim("Banco", "[favorito]:[cifrada]")

    # --- links ---------------------------------------------------------------

    def test_clicar_no_link_abre_a_nota(self):
        self.criar_pasta("Vscode")
        self.digitar('1')
        self.criar_nota("Ctrl + P", "abre o seletor")
        self.digitar('M')
        self.criar_nota("Indice", "veja [[Vscode/Ctrl + P]]")
        self.digitar('2')
        self.app.abrir_link("kb:Vscode/Ctrl%20%2B%20P")
        self.assertEqual(self.nome_tela(), 'ViewerScreen')
        self.assertNaTela("abre o seletor")

    def test_link_ambiguo_pergunta_um_por_linha(self):
        for pasta in ("A", "B"):
            self.criar_pasta(pasta)
            self.digitar('1' if pasta == "A" else '2')
            self.criar_nota("Mesmo", pasta)
            self.digitar('M')
        self.app.abrir_link("kb:Mesmo")
        linhas = [l.strip() for l in self.tela().splitlines()]
        self.assertIn("1 - A / Mesmo", linhas)
        self.assertIn("2 - B / Mesmo", linhas)
        self.digitar('2')
        self.assertNaTela("B")

    def test_link_quebrado_avisa(self):
        self.app.abrir_link("kb:Nada")
        self.assertNaTela("Link quebrado")

    # --- setas na busca -----------------------------------------------------

    def test_setas_escolhem_e_enter_abre(self):
        self.criar_nota("Alfa", "comum")
        self.criar_nota("Beta", "comum")
        self.digitar('B')
        self.digitar('comum')
        self.app.seta(1)
        self.app.seta(1)
        self.assertEqual(self.app.atual.destaque, 1)
        self.digitar('')
        self.assertEqual(self.nome_tela(), 'ViewerScreen')
        self.assertIn("Beta", self.tela())

    def test_sem_destaque_enter_volta(self):
        self.criar_nota("Alfa", "comum")
        self.digitar('B')
        self.digitar('comum')
        self.digitar('')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')

    def test_seta_pela_tecla_na_barra(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.criar_nota("Alfa", "comum")
        self.digitar('B')
        self.digitar('comum')
        self.view.entrada.setFocus()
        QTest.keyClick(self.view.entrada, Qt.Key.Key_Down)
        _app_qt().processEvents()
        self.assertEqual(self.app.atual.destaque, 0)

    def test_busca_aproximada_na_tela(self):
        self.criar_nota("Pandas", "x")
        self.digitar('B')
        self.digitar('pnadas')
        self.assertIn("Pandas", self.tela())


class TestFase4(CofreMixin, BaseUI):
    def criar_modelo(self, nome, conteudo):
        if not any(f.nome == "Modelos" for f in self.app.raiz.filhos):
            self.criar_pasta("Modelos")
        indice = [f.nome for f in tree.filhos_ordenados(self.app.raiz)].index("Modelos") + 1
        self.digitar(str(indice))
        self.criar_nota(nome, conteudo)   # dentro da pasta de modelos: sem pergunta
        self.digitar('M')

    def test_nova_nota_oferece_os_modelos_um_por_linha(self):
        self.criar_modelo("Atalho", "# {nome}\n\nTecla:")
        self.digitar('N')
        self.digitar('Ctrl + P')
        linhas = [l.strip() for l in self.tela().splitlines()]
        self.assertIn("1 - Em branco", linhas)
        self.assertIn("2 - Atalho", linhas)
        self.digitar('2')
        self.assertEqual(self.nome_tela(), 'EditorScreen')
        self.assertEqual(self.editor().toPlainText(), "# Ctrl + P\n\nTecla:")

    def test_em_branco(self):
        self.criar_modelo("Atalho", "x")
        self.digitar('N'); self.digitar('Nova'); self.digitar('1')
        self.assertEqual(self.editor().toPlainText(), "")

    def test_pasta_de_modelos_vazia_nao_pergunta(self):
        self.criar_pasta("Modelos")
        pasta = self.app.raiz.filhos[0]
        tree.remover(pasta, pasta.filhos[0])   # tira o modelo de exemplo
        self.digitar('N'); self.digitar('Nova')
        self.assertEqual(self.nome_tela(), 'EditorScreen')

    def test_sem_pasta_de_modelos_oferece_cria_la(self):
        self.digitar('N'); self.digitar('Nova')
        linhas = [l.strip() for l in self.tela().splitlines()]
        self.assertIn("1 - Em branco", linhas)
        self.assertIn("2 - Criar a pasta de modelos", linhas)
        self.digitar('1')
        self.assertEqual(self.nome_tela(), 'EditorScreen')
        self.assertEqual(self.editor().toPlainText(), "")

    def test_criar_a_pasta_de_modelos_avisa_com_aviso_longo(self):
        self.digitar('N'); self.digitar('Nova'); self.digitar('2')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')
        self.assertEqual([f.nome for f in self.app.raiz.filhos], ["Modelos"])
        self.assertEqual([n.nome for n in self.app.raiz.filhos[0].filhos],
                         ["KeyBase Markdown"])
        self.assertNaTela("criada na raiz")
        self.assertTrue(self.app._flash_mostrado_longo)
        # a partir dai o N oferece o modelo de exemplo
        self.digitar('N'); self.digitar('Nova')
        linhas = [l.strip() for l in self.tela().splitlines()]
        self.assertIn("2 - KeyBase Markdown", linhas)
        self.digitar('2')
        texto = self.editor().toPlainText()
        self.assertTrue(texto.startswith("# Nova\n"))
        self.assertNotIn("{data}", texto)

    def test_criar_a_pasta_de_modelos_com_P_traz_o_exemplo(self):
        self.criar_pasta("modelos")   # sem caixa: ainda e a pasta de modelos
        self.assertEqual([n.nome for n in self.app.raiz.filhos[0].filhos],
                         ["KeyBase Markdown"])
        self.assertNaTela("Pasta de modelos")

    def test_pasta_modelos_fora_da_raiz_e_uma_pasta_comum(self):
        self.criar_pasta("Projetos")
        self.digitar('1')
        self.criar_pasta("Modelos")
        self.assertEqual(self.app.raiz.filhos[0].filhos[0].filhos, [])

    def test_modelo_de_exemplo_renderiza_tudo_e_o_link_para_si_funciona(self):
        self.digitar('N'); self.digitar('Nova'); self.digitar('2')
        self.digitar('1')   # abre a pasta Modelos
        self.digitar('1')   # abre o KeyBase Markdown
        self.assertEqual(self.nome_tela(), 'ViewerScreen')
        html = self.view.out.toHtml()
        for trecho in ("Tabela", "☑", "☐", "saudacao", "Nota de rodapé"):
            self.assertIn(trecho, html)
        self.assertIn('href="kb:Modelos/KeyBase%20Markdown"', html)
        self.assertIn("line-through", html)   # o link quebrado de proposito

    def test_nome_da_pasta_de_modelos_ocupado_nao_oferece(self):
        self.criar_nota("Modelos", "x")
        self.digitar('N'); self.digitar('Nova')
        self.assertEqual(self.nome_tela(), 'EditorScreen')

    def test_pasta_de_modelos_vazia_na_config_desliga(self):
        self.criar_modelo("Atalho", "x")
        self.config['notas']['modelos'] = ""
        self.digitar('N'); self.digitar('Nova')
        self.assertEqual(self.nome_tela(), 'EditorScreen')

    def test_historico_lista_e_restaura(self):
        self.criar_nota("Nota", "versao 1")
        self.digitar('1')
        self.digitar('E'); self.digitar_no_editor("versao 2"); self.app.save()
        self.digitar('E'); self.digitar_no_editor("versao 3"); self.app.save()
        self.digitar('H')
        self.assertEqual(self.nome_tela(), 'HistoricoScreen')
        linhas = [l.strip() for l in self.tela().splitlines()]
        self.assertTrue(any(l.startswith("1 - Backup anterior") for l in linhas))
        self.digitar('1')
        self.assertEqual(self.nome_tela(), 'VersaoScreen')
        self.assertNaTela("versao 2")
        self.digitar('R')
        self.assertEqual(self.nome_tela(), 'ViewerScreen')
        self.assertEqual(self.app.raiz.filhos[0].conteudo, "versao 2")
        self.digitar('U')
        self.assertEqual(self.app.raiz.filhos[0].conteudo, "versao 3")

    def test_historico_vazio_explica(self):
        self.criar_nota("Nota", "unica")
        self.digitar('1')
        self.digitar('H')
        self.assertNaTela("Nenhuma versão diferente")


class TestMenuDoDestino(BaseUI):
    def test_menu_fixo_no_visual_do_dinamico(self):
        self.criar_pasta("Destino")
        self.criar_nota("Nota", "x")
        self.digitar('X2')
        linhas = self.tela().splitlines()
        self.assertTrue(set(linhas[0]) == {'='})                 # o menu abre a tela
        self.assertTrue(linhas[1].strip().startswith("C - Mover para cá"))
        self.assertIn("M - Raiz", linhas[1])
        self.assertIn("ENTER - Subir nível", linhas[2])
        self.assertIn("ESC - Cancelar", linhas[2])
        self.app.alternar_menu()                                  # '?' nao o esconde
        self.assertIn("C - Mover para cá", self.tela())

    def test_m_vai_para_a_raiz(self):
        self.criar_pasta("A")
        self.digitar('1')
        self.criar_nota("Nota", "x")
        self.digitar('X1')
        self.digitar('M')
        self.assertIn(" ~\n", self.tela())
