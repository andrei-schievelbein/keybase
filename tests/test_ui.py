"""Testes da camada de UI dirigindo o app de verdade, sem interacao manual.

Exigem display (Tk). Pulam sozinhos quando nao ha um.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import customtkinter as ctk
    _tk_erro = None
except Exception as e:  # pragma: no cover
    ctk = None
    _tk_erro = e

from keybase import storage, tree
from keybase.config import DEFAULT_CONFIG
from keybase.model import ID_RAIZ


def _tem_display():
    if ctk is None:
        return False
    try:
        r = ctk.CTk()
        r.destroy()
        return True
    except Exception:
        return False


@unittest.skipUnless(_tem_display(), f"sem display para Tk ({_tk_erro})")
class BaseUI(unittest.TestCase):
    def setUp(self):
        from keybase.ui.app import App
        from keybase.ui.screens.browser import BrowserScreen
        from keybase.ui.view import TerminalView

        self.dir = Path(tempfile.mkdtemp())
        self.arquivo = self.dir / 'keybase_data.json'

        config = {k: (dict(v) if isinstance(v, dict) else v)
                  for k, v in DEFAULT_CONFIG.items()}
        config['theme'] = 'light'

        self.root = ctk.CTk()
        self.root.withdraw()
        self.view = TerminalView(self.root, config)

        doc = storage.Documento.novo()
        self.app = App(self.root, self.view, doc, self.arquivo, config)
        self.app.stack = [BrowserScreen(self.app, ID_RAIZ)]
        self.app.rerender()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        shutil.rmtree(self.dir, ignore_errors=True)

    # --- helpers -----------------------------------------------------------

    def digitar(self, comando):
        """Simula digitar no campo de entrada e apertar Enter."""
        self.view.entrada.delete(0, 'end')
        self.view.entrada.insert(0, comando)
        self.app.submit()

    def tela(self):
        return self.view.out.get("1.0", "end")

    def nome_tela(self):
        return type(self.app.atual).__name__

    def criar_pasta(self, nome):
        self.digitar('C')
        self.digitar(nome)

    def criar_nota(self, nome, conteudo=""):
        self.digitar('N')
        self.digitar(nome)          # cai no editor
        if conteudo:
            self.view.edit.delete("1.0", "end")
            self.view.edit.insert("1.0", conteudo)
        self.app.save()             # Ctrl+S
        self.digitar('')            # sai do viewer


class TestNavegacao(BaseUI):
    def test_raiz_comeca_vazia(self):
        self.assertIn("pasta vazia", self.tela())
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
        self.assertEqual(self.view.entrada.get(), 'igual')

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
        self.view.edit.insert("end", " alterado")
        self.app.cancel()            # Esc
        self.assertEqual(self.nome_tela(), 'ConfirmScreen')
        self.assertIn("Descartar", self.tela())

    def test_esc_descartando_preserva_o_original(self):
        self.criar_nota("Nota", "original")
        self.digitar('1')
        self.digitar('E')
        self.view.edit.insert("end", " alterado")
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
        self.view.edit.insert("end", " descartado")
        self.app.cancel()
        self.digitar('S')
        # a segunda edição tem de funcionar normalmente
        self.digitar('E')
        self.assertEqual(self.nome_tela(), 'EditorScreen')
        self.view.edit.insert("end", " salvo")
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
        self.assertEqual(self.view.entrada.get(), 'Antigo')

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
        self.assertIn("comandos do KeyBase", self.tela())
        self.digitar('V')
        self.assertEqual(self.nome_tela(), 'BrowserScreen')

    def test_rodape_so_mostra_comando_implementado(self):
        """Rodape e despacho saem do mesmo dict, entao nao podem divergir."""
        from keybase.ui.screens.browser import BrowserScreen
        from keybase.ui.screens.search import SearchResultsScreen
        from keybase.ui.screens.viewer import ViewerScreen

        for classe in (BrowserScreen, ViewerScreen, SearchResultsScreen):
            for letra, metodo in classe.COMANDOS.items():
                self.assertTrue(hasattr(classe, metodo),
                                f"{classe.__name__}: {letra} aponta para {metodo} inexistente")
                self.assertIn(letra, classe.ROTULOS,
                              f"{classe.__name__}: {letra} sem rótulo no rodapé")

    def test_rodape_esconde_voltar_na_raiz(self):
        self.assertNotIn("V voltar", self.tela())
        self.criar_pasta("A")
        self.digitar('1')
        self.assertIn("V voltar", self.tela())

    def test_comando_invalido_avisa(self):
        self.digitar('XYZ')
        self.assertIn("não reconhecido", self.tela())

    def test_saida_e_somente_leitura(self):
        # CTkTextbox nao expoe 'state' via cget; o estado fica no widget Tk interno
        self.assertEqual(str(self.view.out._textbox.cget('state')), 'disabled')

    def test_digitar_na_saida_nao_altera_o_conteudo(self):
        antes = self.tela()
        self.view.out._textbox.event_generate('<Key>', keysym='a')
        self.root.update_idletasks()
        self.assertEqual(self.tela(), antes)


class TestModos(BaseUI):
    def test_editor_e_saida_sao_exclusivos(self):
        self.assertTrue(self.view.out.winfo_manager())
        self.assertFalse(self.view.edit.winfo_manager())

        self.digitar('N')
        self.digitar('Nota')
        self.assertTrue(self.view.edit.winfo_manager())
        self.assertFalse(self.view.out.winfo_manager())

        self.app.save()
        self.assertTrue(self.view.out.winfo_manager())
        self.assertFalse(self.view.edit.winfo_manager())

    def test_barra_de_dica_so_aparece_no_editor(self):
        self.assertFalse(self.view.ajuda.winfo_manager())
        self.digitar('N')
        self.digitar('Nota')
        self.assertTrue(self.view.ajuda.winfo_manager())
        self.assertIn("Ctrl+S", self.view.ajuda.get("1.0", "end"))

    def test_ctrl_s_fora_do_editor_e_inocuo(self):
        self.app.save()
        self.assertEqual(self.nome_tela(), 'BrowserScreen')


class TestRecuperacao(BaseUI):
    def test_arquivo_corrompido_entra_em_modo_recuperacao(self):
        from keybase.ui.app import App
        from keybase.ui.screens.recovery import RecoveryScreen

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
            app = App(self.root, self.view, doc, self.arquivo, self.app.config)
            app.stack = [RecoveryScreen(app, e, self.arquivo)]
            app.rerender()

        self.assertIn("Não foi possível ler", self.tela())
        self.assertIn("Restaurar", self.tela())
        # o arquivo corrompido continua intacto
        self.assertEqual(self.arquivo.read_text(encoding='utf-8'), corrompido)

    def test_restaurar_backup_recupera_os_dados(self):
        from keybase.ui.app import App
        from keybase.ui.screens.recovery import RecoveryScreen

        self.criar_pasta("A")
        self.criar_pasta("B")
        self.arquivo.write_text('{quebrado', encoding='utf-8')

        try:
            storage.carregar(self.arquivo)
        except storage.StorageError as e:
            doc = storage.Documento.novo()
            doc.somente_leitura = True
            app = App(self.root, self.view, doc, self.arquivo, self.app.config)
            app.stack = [RecoveryScreen(app, e, self.arquivo)]
            app.rerender()
            app.atual.selecionar(0)

        self.assertTrue(storage.carregar(self.arquivo).raiz.filhos)


if __name__ == "__main__":
    unittest.main(verbosity=2)


@unittest.skipUnless(_tem_display(), "sem display para Tk")
class TestFonteELayout(BaseUI):
    def test_familia_escolhida_existe_de_fato(self):
        """Pedir familia inexistente ao Tk devolve fonte proporcional em silencio."""
        import tkinter.font as tkfont
        self.assertIn(self.view.familia, set(tkfont.families()))

    def test_familia_escolhida_e_monoespacada(self):
        import tkinter.font as tkfont
        f = tkfont.Font(family=self.view.familia, size=14)
        self.assertEqual(f.measure('0'), f.measure('W'),
                         f"{self.view.familia} não é monoespaçada; o alinhamento "
                         "por contagem de caracteres depende disso")

    def test_colunas_dentro_dos_limites(self):
        from keybase.ui.view import LARGURA_MAXIMA, LARGURA_MINIMA
        self.assertGreaterEqual(self.view.colunas(), LARGURA_MINIMA)
        self.assertLessEqual(self.view.colunas(), LARGURA_MAXIMA)

    def test_separador_cabe_na_largura(self):
        largura = self.view.colunas()
        for linha in self.tela().splitlines():
            if linha.startswith("─"):
                self.assertLessEqual(len(linha), largura)

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
        from keybase.ui.layout import montar_breadcrumb
        from keybase.model import nova_raiz
        cadeia = [nova_raiz()] + [tree.novo_folder("Nivel " + "x" * 20) for _ in range(6)]
        texto = montar_breadcrumb(cadeia, 60)
        self.assertLessEqual(len(texto), 60)
        self.assertIn("…", texto)
        self.assertTrue(texto.startswith("~"))
