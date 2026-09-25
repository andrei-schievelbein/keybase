"""Logica sem Qt da fase 1: blocos de codigo, duplicar e trocar senha."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keybase import cripto, tree
from keybase.blocos import blocos_de_codigo
from keybase.model import nova_raiz


class TestBlocos(unittest.TestCase):
    def test_blocos_na_ordem_com_linguagem(self):
        texto = "# T\n```python\nx = 1\n```\ntexto\n~~~\nls\n~~~\n"
        blocos = blocos_de_codigo(texto)
        self.assertEqual([(b.linguagem, b.texto) for b in blocos],
                         [("python", "x = 1"), ("", "ls")])

    def test_cerca_maior_contem_cerca_menor(self):
        blocos = blocos_de_codigo("````md\n```\ndentro\n```\n````\n")
        self.assertEqual(blocos[0].texto, "```\ndentro\n```")

    def test_cerca_aberta_ate_o_fim_conta(self):
        self.assertEqual(blocos_de_codigo("```sh\necho oi")[0].texto, "echo oi")

    def test_recuo_da_cerca_sai_do_corpo(self):
        self.assertEqual(blocos_de_codigo("  ```\n  a\n    b\n  ```")[0].texto, "a\n  b")

    def test_sem_blocos(self):
        self.assertEqual(blocos_de_codigo("so texto `inline`"), [])

    def test_rotulo(self):
        bloco = blocos_de_codigo("```python\n\nprint(1)\nx\n```")[0]
        self.assertEqual(bloco.rotulo(), "python (3 linhas): print(1)")


class TestDuplicar(unittest.TestCase):
    def setUp(self):
        self._n = cripto.SCRYPT_N
        cripto.SCRYPT_N = 2 ** 10

    def tearDown(self):
        cripto.SCRYPT_N = self._n

    def test_copia_tem_ids_novos_e_mesmo_conteudo(self):
        pasta = tree.novo_folder("A", "desc")
        tree.adicionar(pasta, tree.novo_file("n", "x"))
        copia = tree.copia_profunda(pasta)
        self.assertNotEqual(copia.id, pasta.id)
        self.assertNotEqual(copia.filhos[0].id, pasta.filhos[0].id)
        self.assertEqual((copia.descricao, copia.filhos[0].conteudo), ("desc", "x"))

    def test_nome_de_copia_procura_o_primeiro_livre(self):
        raiz = nova_raiz()
        tree.adicionar(raiz, tree.novo_file("n"))
        self.assertEqual(tree.nome_de_copia(raiz, "n"), "n (cópia)")
        tree.adicionar(raiz, tree.novo_file("n (cópia)"))
        self.assertEqual(tree.nome_de_copia(raiz, "n"), "n (cópia 2)")

    def test_copia_cifrada_e_recifrada_com_o_id_novo(self):
        cofre = cripto.Cofre.criar("segredo1")
        nota = tree.novo_file("n", "sigiloso-kappa")
        cripto.cifrar_nota(cofre, nota)
        copia = tree.copia_profunda(nota)
        cripto.selar_copia(cofre, copia)
        self.assertEqual(cofre.decifrar(copia.blob, copia.id), "sigiloso-kappa")
        with self.assertRaises(cripto.BlobInvalidoError):
            cofre.decifrar(nota.blob, copia.id)   # o blob antigo nao serviria

    def test_copia_de_pasta_cifrada_com_nota_dentro(self):
        cofre = cripto.Cofre.criar("segredo1")
        pasta = tree.novo_folder("P")
        tree.adicionar(pasta, tree.novo_file("n", "conteudo"))
        cripto.cifrar_pasta(cofre, pasta)
        copia = tree.copia_profunda(pasta)
        cripto.selar_copia(cofre, copia)
        cripto.fechar_pasta(copia)
        cripto.abrir_pasta(cofre, copia)
        self.assertEqual(copia.filhos[0].conteudo, "conteudo")

    def test_pasta_trancada_nao_duplica(self):
        cofre = cripto.Cofre.criar("segredo1")
        pasta = tree.novo_folder("P")
        cripto.cifrar_pasta(cofre, pasta)
        cripto.fechar_pasta(pasta)
        with self.assertRaises(ValueError):
            tree.copia_profunda(pasta)


class TestTrocarSenha(unittest.TestCase):
    def setUp(self):
        self._n = cripto.SCRYPT_N
        cripto.SCRYPT_N = 2 ** 10

    def tearDown(self):
        cripto.SCRYPT_N = self._n

    def test_nova_senha_abre_a_mesma_chave(self):
        cofre = cripto.Cofre.criar("antiga1")
        blob = cofre.cifrar("sigiloso", "id1")
        antigo = cofre.to_dict()
        cofre.trocar_senha("antiga1", "novinha1")
        outro = cripto.Cofre.from_dict(cofre.to_dict())
        outro.destravar("novinha1")
        self.assertEqual(outro.decifrar(blob, "id1"), "sigiloso")   # nada recifrado
        with self.assertRaises(cripto.SenhaIncorretaError):
            cripto.Cofre.from_dict(cofre.to_dict()).destravar("antiga1")
        velho = cripto.Cofre.from_dict(antigo)   # cabecalho de um backup antigo
        velho.destravar("antiga1")

    def test_senha_atual_errada(self):
        cofre = cripto.Cofre.criar("antiga1")
        with self.assertRaises(cripto.SenhaIncorretaError):
            cofre.trocar_senha("errada", "novinha1")

    def test_conferir_nao_destrava(self):
        cofre = cripto.Cofre.from_dict(cripto.Cofre.criar("antiga1").to_dict())
        self.assertTrue(cofre.conferir("antiga1"))
        self.assertFalse(cofre.conferir("x"))
        self.assertFalse(cofre.destravado)


if __name__ == '__main__':
    unittest.main()
