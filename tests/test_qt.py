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

        doc = storage.Documento.novo()
        self.app = App(self.janela, self.view, doc, self.arquivo, config)
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

    def criar_pasta(self, nome):
        self.digitar('C')
        self.digitar(nome)

    def criar_nota(self, nome, conteudo=""):
        self.digitar('N')
        self.digitar(nome)          # cai no editor
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

    def test_contagem_de_itens(self):
        self.criar_pasta("Pai")
        self.digitar('1')
        self.criar_pasta("F1")
        self.criar_pasta("F2")
        self.digitar('V')
        self.assertIn("[2]", self.tela())

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
        self.assertEqual(self.nome_tela(), 'EditorScreen')
        self.assertTrue(self.app.atual.usa_editor())

    def test_nome_duplicado_e_recusado_sem_perder_o_digitado(self):
        self.criar_pasta("Igual")
        self.digitar('C')
        self.digitar('igual')  # mesma coisa ignorando caixa
        self.assertEqual(self.nome_tela(), 'PromptScreen')
        self.assertIn("Já existe", self.tela())
        self.assertEqual(self.view.entrada.text(), 'igual')

    def test_nome_vazio_cancela(self):
        self.digitar('C')
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
        self.app.cancel()            # Esc
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')
        self.assertIn("Descartar", self.tela())

    def test_esc_descartando_preserva_o_original(self):
        self.criar_nota("Nota", "original")
        self.digitar('1')
        self.digitar('E')
        self.anexar_no_editor(' alterado')
        self.app.cancel()
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
        self.app.cancel()
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
        self.app.cancel()
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
        self.app.cancel()
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


class TestAjudaERodape(BaseUI):
    def test_ajuda_abre_e_volta(self):
        self.digitar('?')
        self.assertEqual(self.nome_tela(), 'HelpScreen')
        self.assertNaTela("comandos do KeyBase")
        self.digitar('V')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')

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
        self.assertNaoNaTela("V - Voltar")
        self.criar_pasta("A")
        self.digitar('1')
        self.assertNaTela("V - Voltar")

    def test_comando_invalido_avisa(self):
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
        self.assertIs(self.view.pilha.currentWidget(), self.view.painel)

        self.app.save()
        self.assertIs(self.view.pilha.currentWidget(), self.view.out)

    def test_barra_de_dica_so_aparece_no_editor(self):
        self.assertFalse(self.view.ajuda.isVisibleTo(self.janela))
        self.digitar('N')
        self.digitar('Nota')
        self.assertTrue(self.view.ajuda.isVisibleTo(self.janela))
        self.assertIn("Ctrl+S", self.view.ajuda.text())

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
        self.assertNaTela("C - Nova pasta")
        self.assertNaTela("N - Nova nota")
        self.assertNaTela("sair - Encerrar")

    def test_contadores_alinhados_a_direita(self):
        self.criar_pasta("Curto")
        self.digitar('1'); self.criar_pasta("x"); self.digitar('V')
        self.criar_pasta("Um nome bem mais comprido que o outro")
        self.digitar('2'); self.criar_pasta("y"); self.criar_pasta("z"); self.digitar('V')

        fins = [len(l.rstrip()) for l in self.tela().splitlines() if l.rstrip().endswith(']')]
        self.assertEqual(len(fins), 2)
        self.assertEqual(fins[0], fins[1], "os contadores [N] devem terminar na mesma coluna")

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
        self.assertIn('[editar]', self.view.ajuda.text())
        self.app.modo('dividido')
        self.assertIn('[dividido]', self.view.ajuda.text())

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
        self.app.cancel()
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
