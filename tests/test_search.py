import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keybase import search, tree
from keybase.model import nova_raiz


def base():
    """
    KeyBase
      Vscode (Editor principal)
        Navegação
          Ctrl + P        -> "Abre o seletor rapido de arquivos"
          Ctrl + G
      Cursor
        Atalhos
          Paleta de comandos -> "...abrir arquivo rapido com Ctrl + P..."
    """
    raiz = nova_raiz()
    vscode = tree.novo_folder("Vscode", "Editor principal")
    navegacao = tree.novo_folder("Navegação")
    ctrl_p = tree.novo_file("Ctrl + P", "Abre o seletor rápido de arquivos.")
    ctrl_g = tree.novo_file("Ctrl + G", "Vai para a linha.")
    cursor = tree.novo_folder("Cursor")
    atalhos = tree.novo_folder("Atalhos")
    paleta = tree.novo_file(
        "Paleta de comandos",
        "Voce pode abrir arquivo rapido com Ctrl + P e digitar o nome do arquivo.")

    tree.adicionar(raiz, vscode)
    tree.adicionar(vscode, navegacao)
    tree.adicionar(navegacao, ctrl_p)
    tree.adicionar(navegacao, ctrl_g)
    tree.adicionar(raiz, cursor)
    tree.adicionar(cursor, atalhos)
    tree.adicionar(atalhos, paleta)
    return raiz, {"vscode": vscode, "navegacao": navegacao, "ctrl_p": ctrl_p,
                  "paleta": paleta, "cursor": cursor}


class TestNormalizacao(unittest.TestCase):
    def test_sem_acento_acha_com_acento(self):
        raiz, _ = base()
        achados, _ = search.buscar(raiz, "navegacao")
        self.assertEqual(achados[0].no.nome, "Navegação")

    def test_caixa_diferente_acha(self):
        raiz, _ = base()
        achados, _ = search.buscar(raiz, "CTRL")
        self.assertTrue(achados)
        self.assertIn("Ctrl", achados[0].no.nome)


class TestRanking(unittest.TestCase):
    def test_nome_exato_vem_antes_de_hit_em_conteudo(self):
        raiz, nos = base()
        achados, _ = search.buscar(raiz, "Ctrl + P")
        self.assertIs(achados[0].no, nos["ctrl_p"])
        self.assertEqual(achados[0].campo, "nome")
        # a paleta casa só no conteúdo, então vem depois
        ids = [r.no.id for r in achados]
        self.assertGreater(ids.index(nos["paleta"].id), ids.index(nos["ctrl_p"].id))

    def test_prefixo_pontua_mais_que_substring(self):
        raiz = nova_raiz()
        prefixo = tree.novo_file("abcdef")
        meio = tree.novo_file("zzz abc")
        tree.adicionar(raiz, prefixo)
        tree.adicionar(raiz, meio)
        achados, _ = search.buscar(raiz, "abc")
        self.assertIs(achados[0].no, prefixo)

    def test_hit_na_descricao_da_pasta(self):
        raiz, nos = base()
        achados, _ = search.buscar(raiz, "Editor principal")
        self.assertIs(achados[0].no, nos["vscode"])
        self.assertEqual(achados[0].campo, "descricao")

    def test_um_hit_por_no(self):
        """Nó que casa em nome e conteúdo aparece uma vez só."""
        raiz = nova_raiz()
        tree.adicionar(raiz, tree.novo_file("python", "python python python"))
        achados, total = search.buscar(raiz, "python")
        self.assertEqual(total, 1)
        self.assertEqual(len(achados), 1)


class TestTrecho(unittest.TestCase):
    def test_hit_em_conteudo_traz_contexto(self):
        raiz, nos = base()
        achados, _ = search.buscar(raiz, "digitar o nome")
        alvo = [r for r in achados if r.no is nos["paleta"]][0]
        self.assertEqual(alvo.campo, "conteudo")
        self.assertIn("digitar o nome", alvo.trecho)
        self.assertTrue(alvo.trecho.startswith("..."))

    def test_hit_em_nome_nao_traz_trecho(self):
        raiz, _ = base()
        achados, _ = search.buscar(raiz, "Navegação")
        self.assertEqual(achados[0].trecho, "")

    def test_trecho_colapsa_quebras_de_linha(self):
        raiz = nova_raiz()
        tree.adicionar(raiz, tree.novo_file("x", "linha um\n\n\nalvo aqui\n\nlinha tres"))
        achados, _ = search.buscar(raiz, "alvo")
        self.assertNotIn("\n", achados[0].trecho)


class TestCaminho(unittest.TestCase):
    def test_ancestrais_batem_com_tree_caminho(self):
        raiz, nos = base()
        indice = tree.construir_indice(raiz)
        achados, _ = search.buscar(raiz, "Ctrl + P")
        resultado = achados[0]
        esperado = tree.caminho(indice, nos["ctrl_p"])[:-1]  # sem o próprio nó
        self.assertEqual([a.id for a in resultado.ancestrais], [n.id for n in esperado])

    def test_caminho_legivel_pula_a_raiz(self):
        raiz, _ = base()
        achados, _ = search.buscar(raiz, "Ctrl + P")
        self.assertEqual(achados[0].caminho, "Vscode / Navegação")

    def test_caminho_na_raiz(self):
        raiz = nova_raiz()
        tree.adicionar(raiz, tree.novo_folder("Solto"))
        achados, _ = search.buscar(raiz, "Solto")
        self.assertEqual(achados[0].caminho, "(raiz)")

    def test_rotulo_tipo(self):
        raiz, _ = base()
        achados, _ = search.buscar(raiz, "Navegação")
        self.assertEqual(achados[0].rotulo_tipo, "pasta")
        achados, _ = search.buscar(raiz, "Ctrl + G")
        self.assertEqual(achados[0].rotulo_tipo, "nota")


class TestGuardas(unittest.TestCase):
    def test_termo_curto_e_recusado(self):
        raiz, _ = base()
        with self.assertRaises(search.TermoCurtoError):
            search.buscar(raiz, "a")

    def test_limite_e_total(self):
        raiz = nova_raiz()
        for i in range(60):
            tree.adicionar(raiz, tree.novo_file(f"item {i}"))
        achados, total = search.buscar(raiz, "item", limite=50)
        self.assertEqual(len(achados), 50)
        self.assertEqual(total, 60)

    def test_sem_resultado(self):
        raiz, _ = base()
        achados, total = search.buscar(raiz, "inexistente")
        self.assertEqual(achados, [])
        self.assertEqual(total, 0)


class TestFiltro(unittest.TestCase):
    def test_filtro_e_raso(self):
        raiz, nos = base()
        # 'Ctrl' existe dentro de Navegação, mas não entre os filhos da raiz
        self.assertEqual(search.filtrar(raiz, "ctrl"), [])
        achados = search.filtrar(nos["navegacao"], "ctrl")
        self.assertEqual(len(achados), 2)

    def test_filtro_vazio_devolve_none(self):
        raiz, _ = base()
        self.assertIsNone(search.filtrar(raiz, ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
