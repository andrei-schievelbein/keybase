"""Testes do motor de Markdown. Funcao pura str -> str, sem Qt e sem display.

Boa parte deles existe para travar decisoes de seguranca de conteudo: varias
extensoes populares do Markdown COMEM texto do usuario em silencio, que e a
mesma classe do bug historico em que uma nota terminada na palavra CTRL_S era
truncada ao salvar.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keybase.qt.render import RenderizadorMarkdown, folha_de_estilo
from keybase.qt.render.pos_html import realcar


def render(texto, tema='dark'):
    r = RenderizadorMarkdown(tema, {'output_size': 14, 'family': 'Menlo'})
    return r.html(texto)


class TestBasico(unittest.TestCase):
    def test_titulo(self):
        self.assertIn('<h1', render('# Titulo'))

    def test_negrito_e_italico(self):
        html = render('**forte** e *fraco*')
        self.assertIn('<strong>', html)
        self.assertIn('<em>', html)

    def test_riscado(self):
        """~~x~~ nao existe no Python-Markdown core; vem de pymdownx.tilde."""
        self.assertIn('<del>', render('~~cortado~~'))

    def test_codigo_inline(self):
        self.assertIn('<code>', render('use `git status` aqui'))

    def test_citacao(self):
        self.assertIn('<blockquote>', render('> citado'))

    def test_lista(self):
        html = render('- um\n- dois')
        self.assertIn('<ul>', html)
        self.assertEqual(html.count('<li>'), 2)


class TestTabela(unittest.TestCase):
    MD = '| A | B |\n|---|---|\n| 1 | 2 |'

    def test_vira_table(self):
        self.assertIn('<table', render(self.MD))

    def test_ganha_grade(self):
        """Tabela sem atributos renderiza sem linha nenhuma no Qt."""
        html = render(self.MD)
        self.assertIn('border="1"', html)
        self.assertIn('cellpadding="4"', html)

    def test_cabecalho(self):
        self.assertIn('<th>', render(self.MD))


class TestTarefas(unittest.TestCase):
    def test_caixa_marcada(self):
        html = render('- [x] feita')
        self.assertIn('☑', html)

    def test_caixa_vazia(self):
        self.assertIn('☐', render('- [ ] pendente'))

    def test_input_e_removido(self):
        """O Qt descarta <input> em silencio, deixando o item sem marcador."""
        html = render('- [x] feita\n- [ ] pendente')
        self.assertNotIn('<input', html)

    def test_espacamento_simples(self):
        self.assertIn('☑ feita', render('- [x] feita'))

    def test_lista_marcada_como_tarefa(self):
        self.assertIn('task-list', render('- [x] feita'))


class TestBlocoDeCodigo(unittest.TestCase):
    def test_envolvido_em_tabela(self):
        """padding nao vale em bloco no Qt; cellpadding numa celula, sim."""
        html = render('```python\nx = 1\n```')
        self.assertIn('class="codigo"', html)
        self.assertIn('cellpadding="8"', html)
        self.assertIn('bgcolor=', html)

    def test_realce_inline(self):
        """Estilo inline, nao classe: o Qt nao garante seletor descendente."""
        html = render('```python\ndef f(): pass\n```')
        self.assertIn('<span style="color:', html)

    def test_linguagem_desconhecida_nao_explode(self):
        html = render('```xyzzy\nalgo\n```')
        self.assertIn('algo', html)
        self.assertIn('class="codigo"', html)

    def test_bloco_sem_linguagem(self):
        html = render('```\ntexto puro\n```')
        self.assertIn('texto puro', html)

    def test_cerca_dentro_de_cerca(self):
        """superfences trata cerca aninhada; fenced_code quebrava."""
        html = render('````\n```\ninterno\n```\n````')
        self.assertIn('interno', html)

    def test_html_no_codigo_e_escapado(self):
        html = render('```\n<script>alert(1)</script>\n```')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_realcar_nunca_levanta(self):
        self.assertTrue(realcar('x = 1', 'naoexiste', 'dark'))
        self.assertTrue(realcar('', '', 'dark') == '')


class TestConteudoNaoEComido(unittest.TestCase):
    """Cada teste aqui trava a recusa de uma extensao que corrompia conteudo."""

    def test_chaves_no_fim_sobrevivem(self):
        """attr_list comeria `{...}` e transformaria em atributos."""
        html = render('config final { "debug": true }')
        self.assertIn('debug', html)
        self.assertIn('true', html)

    def test_hashtag_nao_vira_titulo(self):
        """saneheaders exige espaco depois do #."""
        html = render('#!/bin/bash')
        self.assertNotIn('<h1', html)
        self.assertIn('#!/bin/bash', html)

    def test_hashtag_de_config_nao_vira_titulo(self):
        self.assertNotIn('<h1', render('#config'))

    def test_aspas_nao_sao_curvadas(self):
        """smarty tornaria um comando de shell nao copiavel."""
        html = render('git commit -m "mensagem"')
        self.assertIn('"mensagem"', html)
        self.assertNotIn('&ldquo;', html)

    def test_travessao_nao_e_convertido(self):
        self.assertIn('--flag', render('use --flag aqui'))

    def test_colchete_negado_sem_definicao_sobrevive(self):
        """Regex [^abc] nao pode virar nota de rodape."""
        html = render('o padrao [^abc] casa qualquer coisa')
        self.assertIn('[^abc]', html)

    def test_til_nao_vira_subscrito(self):
        """tilde com subscript ligado mangleria caminhos."""
        html = render('veja ~/projetos ~ backup')
        self.assertIn('~/projetos', html)
        self.assertNotIn('<sub>', html)

    def test_palavra_CTRL_S_sobrevive(self):
        """Regressao historica: conteudo do usuario nunca e comido."""
        self.assertIn('CTRL_S', render('pressione CTRL_S para salvar'))

    def test_texto_com_e_comercial(self):
        self.assertIn('&amp;', render('a &amp; b'))


class TestEstado(unittest.TestCase):
    def test_instancia_reusada_nao_acumula_rodape(self):
        """Sem reset(), footnotes e toc vazam de uma conversao para a seguinte."""
        r = RenderizadorMarkdown('dark', {'output_size': 14})
        primeiro = r.html('texto[^1]\n\n[^1]: primeira nota')
        segundo = r.html('outro texto sem rodape')
        self.assertIn('primeira nota', primeiro)
        self.assertNotIn('primeira nota', segundo)

    def test_duas_conversoes_iguais_dao_o_mesmo_html(self):
        r = RenderizadorMarkdown('dark', {'output_size': 14})
        md = '# Titulo\n\n- [x] feita\n\n```python\nx=1\n```'
        self.assertEqual(r.html(md), r.html(md))

    def test_texto_vazio(self):
        self.assertEqual(render(''), '')

    def test_none_nao_explode(self):
        r = RenderizadorMarkdown('dark', {})
        self.assertEqual(r.html(None), '')


class TestEstilo(unittest.TestCase):
    def test_css_usa_as_cores_do_tema(self):
        self.assertIn('#569CD6', folha_de_estilo('dark', {'output_size': 14}))

    def test_temas_diferem(self):
        escuro = folha_de_estilo('dark', {'output_size': 14})
        claro = folha_de_estilo('light', {'output_size': 14})
        self.assertNotEqual(escuro, claro)

    def test_cabecalhos_tem_tamanhos_diferentes(self):
        """A limitacao do CustomTkinter era so cor; aqui h1 e maior de fato."""
        css = folha_de_estilo('dark', {'output_size': 14})
        self.assertIn('font-size: 22px', css)   # h1 = base + 8
        self.assertIn('font-size: 19px', css)   # h2 = base + 5

    def test_tamanho_acompanha_a_config(self):
        css = folha_de_estilo('dark', {'output_size': 20})
        self.assertIn('font-size: 28px', css)

    def test_sem_seletor_descendente(self):
        """O suporte a combinadores no rich text do Qt nao e confiavel."""
        css = folha_de_estilo('dark', {'output_size': 14})
        # cada regra e "seletor { declaracoes }"; pega o que vem antes da chave
        for regra in css.split('}'):
            if '{' not in regra:
                continue
            seletor = regra.rsplit('{', 1)[0].strip()
            for parte in seletor.split(','):
                parte = parte.strip()
                if not parte:
                    continue
                self.assertEqual(
                    len(parte.split()), 1,
                    f"seletor descendente encontrado: {parte!r}")
                self.assertNotIn('>', parte)
                self.assertNotIn('+', parte)


class TestTemaClaro(unittest.TestCase):
    def test_realce_usa_cores_escuras_no_tema_claro(self):
        """No tema claro o codigo precisa contrastar com fundo claro."""
        html = render('```python\ndef f(): pass\n```', tema='light')
        self.assertIn('#795E26', html)   # Name.Function do tema claro

    def test_fundo_do_codigo_muda_por_tema(self):
        from keybase.qt.theme import cores_markdown
        for tema in ('dark', 'light'):
            self.assertIn(cores_markdown(tema)['code_bg'], render('```\nx\n```', tema))

    def test_fundo_do_codigo_contrasta_com_o_da_janela(self):
        """Sem contraste suficiente o bloco some no fundo."""
        from keybase.qt.theme import cores_interface, cores_markdown
        for tema in ('dark', 'light'):
            fundo = cores_interface(tema)['fundo']
            codigo = cores_markdown(tema)['code_bg']
            self.assertNotEqual(fundo.lower(), codigo.lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
