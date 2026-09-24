"""Logica sem Qt da fase 3: favoritos no modelo, links e busca aproximada."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keybase import cripto, links, search, tree
from keybase.model import node_from_dict, nova_raiz
from keybase.qt.render.pipeline import RenderizadorMarkdown


def arvore():
    raiz = nova_raiz()
    vscode = tree.novo_folder("Vscode")
    tree.adicionar(raiz, vscode)
    tree.adicionar(vscode, tree.novo_file("Ctrl + P", "abre o seletor"))
    outro = tree.novo_folder("Sublime")
    tree.adicionar(raiz, outro)
    tree.adicionar(outro, tree.novo_file("ctrl + p", "outro editor"))
    tree.adicionar(raiz, tree.novo_file("Pandas", "dataframes"))
    return raiz


class TestFavorito(unittest.TestCase):
    def test_ida_e_volta_e_so_quando_true(self):
        nota = tree.novo_file("n")
        self.assertNotIn("favorito", nota.to_dict())
        nota.favorito = True
        self.assertTrue(node_from_dict(nota.to_dict()).favorito)
        pasta = tree.novo_folder("p")
        pasta.favorito = True
        self.assertTrue(node_from_dict(pasta.to_dict()).favorito)

    def test_pasta_cifrada_trancada_guarda_o_favorito(self):
        cripto_n = cripto.SCRYPT_N
        cripto.SCRYPT_N = 2 ** 10
        try:
            cofre = cripto.Cofre.criar("segredo1")
            pasta = tree.novo_folder("p")
            pasta.favorito = True
            cripto.cifrar_pasta(cofre, pasta)
            cripto.fechar_pasta(pasta)
            self.assertTrue(node_from_dict(pasta.to_dict()).favorito)
        finally:
            cripto.SCRYPT_N = cripto_n


class TestLinks(unittest.TestCase):
    def test_por_nome_acha_todas_as_iguais(self):
        self.assertEqual(len(links.resolver(arvore(), "CTRL + P")), 2)

    def test_por_caminho_acha_uma(self):
        achadas = links.resolver(arvore(), "Vscode/Ctrl + P")
        self.assertEqual([n.conteudo for n in achadas], ["abre o seletor"])

    def test_inexistente(self):
        self.assertEqual(links.resolver(arvore(), "Nada"), [])
        self.assertEqual(links.resolver(arvore(), "Vscode/Nada"), [])

    def test_pasta_nao_e_alvo(self):
        self.assertEqual(links.resolver(arvore(), "Vscode"), [])

    def test_texto_mostrado(self):
        self.assertEqual(links.separar("A/B|ver aqui"), ("A/B", "ver aqui"))
        self.assertEqual(links.separar("A"), ("A", "A"))


class TestRenderLinks(unittest.TestCase):
    def setUp(self):
        self.r = RenderizadorMarkdown()

    def test_vira_link_com_o_texto(self):
        html = self.r.html("veja [[Vscode/Ctrl + P|o atalho]]")
        self.assertIn('<a href="kb:Vscode/Ctrl%20%2B%20P">o atalho</a>', html)

    def test_dentro_de_crase_fica_texto(self):
        self.assertIn("<code>[[cru]]</code>", self.r.html("`[[cru]]`"))

    def test_quebrado_sai_riscado_e_sem_link(self):
        html = self.r.html("[[Sumiu]]", existe=lambda alvo: False)
        self.assertIn("line-through", html)
        self.assertNotIn("<a ", html)

    def test_existe_nao_vaza_para_a_proxima_conversao(self):
        self.r.html("[[x]]", existe=lambda alvo: False)
        self.assertIn("<a ", self.r.html("[[x]]"))


class TestBuscaAproximada(unittest.TestCase):
    def test_distancia_com_transposicao(self):
        self.assertEqual(search.distancia("cotnrol", "control"), 1)
        self.assertEqual(search.distancia("abc", "abc"), 0)

    def test_erro_de_digitacao_acha(self):
        achados, _ = search.buscar(arvore(), "pnadas")
        self.assertEqual([r.no.nome for r in achados], ["Pandas"])
        self.assertEqual(achados[0].campo, "aproximado")

    def test_aproximado_fica_abaixo_do_exato(self):
        raiz = arvore()
        tree.adicionar(raiz, tree.novo_file("Pandsa", "x"))
        achados, _ = search.buscar(raiz, "pandsa")
        self.assertEqual(achados[0].no.nome, "Pandsa")

    def test_termo_curto_nao_e_aproximado(self):
        achados, _ = search.buscar(arvore(), "pnd")
        self.assertEqual(achados, [])


if __name__ == '__main__':
    unittest.main()
