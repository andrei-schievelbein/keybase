import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keybase import tree
from keybase.model import File, Folder, node_from_dict, nova_raiz, EsquemaInvalidoError


def arvore_exemplo():
    """raiz / Vscode / Navegacao / 'Ctrl + P'"""
    raiz = nova_raiz()
    vscode = tree.novo_folder("Vscode", "Editor principal")
    navegacao = tree.novo_folder("Navegação")
    ctrl_p = tree.novo_file("Ctrl + P", "Abre o seletor.\n\n```python\nprint('ex')\n```\n")
    tree.adicionar(raiz, vscode)
    tree.adicionar(vscode, navegacao)
    tree.adicionar(navegacao, ctrl_p)
    return raiz, vscode, navegacao, ctrl_p


class TestSerializacao(unittest.TestCase):
    def test_round_trip_identico(self):
        raiz, _, _, _ = arvore_exemplo()
        bruto = raiz.to_dict()
        reconstruida = node_from_dict(bruto)
        self.assertEqual(reconstruida.to_dict(), bruto)

    def test_discriminador_tipo_presente(self):
        raiz, _, _, ctrl_p = arvore_exemplo()
        self.assertEqual(raiz.to_dict()["tipo"], "folder")
        self.assertEqual(ctrl_p.to_dict()["tipo"], "file")

    def test_no_sem_id_e_reparado_com_aviso(self):
        bruto = {"tipo": "file", "nome": "orfa", "conteudo": "x"}
        reparos = []
        no = node_from_dict(bruto, reparos)
        self.assertTrue(no.id)
        self.assertEqual(len(reparos), 1)

    def test_tipo_desconhecido_e_erro(self):
        with self.assertRaises(EsquemaInvalidoError):
            node_from_dict({"tipo": "snippet", "nome": "x"})

    def test_filhos_com_forma_errada_e_erro(self):
        with self.assertRaises(EsquemaInvalidoError):
            node_from_dict({"tipo": "folder", "nome": "x", "filhos": "nao e lista"})


class TestOrdenacao(unittest.TestCase):
    def test_folders_antes_de_files(self):
        raiz = nova_raiz()
        tree.adicionar(raiz, tree.novo_file("aaa"))
        tree.adicionar(raiz, tree.novo_folder("zzz"))
        nomes = [n.nome for n in tree.filhos_ordenados(raiz)]
        self.assertEqual(nomes, ["zzz", "aaa"])

    def test_alfabetico_ignora_acento(self):
        raiz = nova_raiz()
        for nome in ["Beta", "Ágil", "carro"]:
            tree.adicionar(raiz, tree.novo_file(nome))
        nomes = [n.nome for n in tree.filhos_ordenados(raiz)]
        self.assertEqual(nomes, ["Ágil", "Beta", "carro"])

    def test_ordem_exibida_difere_da_ordem_em_filhos(self):
        # É esse descasamento que torna a invariante de numeração necessária.
        raiz = nova_raiz()
        tree.adicionar(raiz, tree.novo_file("zebra"))
        tree.adicionar(raiz, tree.novo_folder("alpha"))
        self.assertNotEqual(
            [n.nome for n in raiz.filhos],
            [n.nome for n in tree.filhos_ordenados(raiz)],
        )


class TestNavegacao(unittest.TestCase):
    def test_caminho_ate_a_folha(self):
        raiz, vscode, navegacao, ctrl_p = arvore_exemplo()
        indice = tree.construir_indice(raiz)
        cadeia = tree.caminho(indice, ctrl_p)
        self.assertEqual([n.nome for n in cadeia],
                         ["KeyBase", "Vscode", "Navegação", "Ctrl + P"])

    def test_breadcrumb_pula_a_raiz(self):
        raiz, _, navegacao, _ = arvore_exemplo()
        indice = tree.construir_indice(raiz)
        self.assertEqual(tree.breadcrumb(tree.caminho(indice, navegacao)),
                         "Vscode / Navegação")

    def test_indice_mapeia_pai(self):
        raiz, vscode, navegacao, _ = arvore_exemplo()
        indice = tree.construir_indice(raiz)
        self.assertIs(indice[navegacao.id][1], vscode)
        self.assertIsNone(indice[raiz.id][1])

    def test_percorrer_carrega_ancestrais(self):
        raiz, vscode, navegacao, ctrl_p = arvore_exemplo()
        achados = {no.id: anc for no, anc in tree.percorrer(raiz)}
        self.assertEqual([a.nome for a in achados[ctrl_p.id]],
                         ["KeyBase", "Vscode", "Navegação"])


class TestContagem(unittest.TestCase):
    def test_contar_recursivo_tres_niveis(self):
        raiz, vscode, _, _ = arvore_exemplo()
        self.assertEqual(tree.contar_recursivo(vscode), (1, 1))
        self.assertEqual(tree.contar_recursivo(raiz), (2, 1))

    def test_contar_notas_separa_direto_de_recursivo(self):
        raiz, vscode, navegacao, _ = arvore_exemplo()
        self.assertEqual(tree.contar_notas(raiz), (0, 1))      # nada solto, 1 no fundo
        self.assertEqual(tree.contar_notas(vscode), (0, 1))
        self.assertEqual(tree.contar_notas(navegacao), (1, 1))  # a nota está aqui

    def test_contar_notas_ignora_pastas(self):
        """Sub-pasta não é nota: não entra em nenhuma das duas metades."""
        raiz = nova_raiz()
        tree.adicionar(raiz, tree.novo_folder("so uma pasta"))
        self.assertEqual(tree.contar_notas(raiz), (0, 0))

    def test_contar_notas_soma_ramos_irmaos(self):
        raiz = nova_raiz()
        a, b = tree.novo_folder("A"), tree.novo_folder("B")
        tree.adicionar(raiz, a)
        tree.adicionar(raiz, b)
        tree.adicionar(raiz, tree.novo_file("solta"))
        for nome in ("a1", "a2"):
            tree.adicionar(a, tree.novo_file(nome))
        tree.adicionar(b, tree.novo_file("b1"))
        self.assertEqual(tree.contar_notas(raiz), (1, 4))

    def test_contar_itens_conta_so_diretos(self):
        raiz, vscode, _, _ = arvore_exemplo()
        self.assertEqual(tree.contar_itens(raiz), 1)
        self.assertEqual(tree.contar_itens(vscode), 1)

    def test_resumo_delecao(self):
        raiz, vscode, _, ctrl_p = arvore_exemplo()
        self.assertIn("1 pasta, 1 nota", tree.resumo_delecao(vscode))
        self.assertIn("nota", tree.resumo_delecao(ctrl_p))
        self.assertIn("vazia", tree.resumo_delecao(tree.novo_folder("nada")))

    def test_confirmacao_forte_so_para_folder_cheio(self):
        raiz, vscode, _, ctrl_p = arvore_exemplo()
        self.assertTrue(tree.precisa_confirmacao_forte(vscode))
        self.assertFalse(tree.precisa_confirmacao_forte(ctrl_p))
        self.assertFalse(tree.precisa_confirmacao_forte(tree.novo_folder("vazia")))


class TestMutacao(unittest.TestCase):
    def test_renomear_atualiza_timestamp(self):
        no = tree.novo_file("antes")
        no.atualizado_em = "2020-01-01T00:00:00+00:00"
        tree.renomear(no, "depois")
        self.assertEqual(no.nome, "depois")
        self.assertNotEqual(no.atualizado_em, "2020-01-01T00:00:00+00:00")

    def test_remover(self):
        raiz, vscode, _, _ = arvore_exemplo()
        tree.remover(raiz, vscode)
        self.assertEqual(raiz.filhos, [])

    def test_mover_para_dentro_de_si_e_erro(self):
        raiz, vscode, navegacao, _ = arvore_exemplo()
        with self.assertRaises(tree.CicloError):
            tree.mover(vscode, raiz, navegacao)

    def test_mover_valido(self):
        raiz, vscode, navegacao, ctrl_p = arvore_exemplo()
        tree.mover(ctrl_p, navegacao, raiz)
        self.assertIn(ctrl_p, raiz.filhos)
        self.assertNotIn(ctrl_p, navegacao.filhos)

    def test_nome_disponivel(self):
        raiz, vscode, _, _ = arvore_exemplo()
        self.assertFalse(tree.nome_disponivel(raiz, "vscode"))
        self.assertFalse(tree.nome_disponivel(raiz, "VSCODE"))
        self.assertTrue(tree.nome_disponivel(raiz, "outro"))
        self.assertTrue(tree.nome_disponivel(raiz, "Vscode", ignorar=vscode))


class TestPreview(unittest.TestCase):
    def test_preview_pula_heading_e_linhas_vazias(self):
        f = tree.novo_file("x", "\n\n# Titulo\n\ncorpo aqui\n")
        self.assertEqual(tree.preview_conteudo(f), "Titulo")

    def test_preview_vazio(self):
        self.assertEqual(tree.preview_conteudo(tree.novo_file("x", "")), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
