"""Logica sem Qt da fase 4: modelos de nota e historico nos backups."""

import os
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keybase import cripto, historico, modelos, storage, tree
from keybase.model import nova_raiz


class TestModelos(unittest.TestCase):
    def raiz(self):
        raiz = nova_raiz()
        pasta = tree.novo_folder("Modelos")
        tree.adicionar(raiz, pasta)
        tree.adicionar(pasta, tree.novo_file("Atalho", "# {nome}\n\nQuando: {data}"))
        tree.adicionar(pasta, tree.novo_file("Codigo", '```json\n{ "a": 1 }\n```'))
        return raiz

    def test_acha_a_pasta_sem_caixa_nem_acento(self):
        self.assertIsNotNone(modelos.pasta_de_modelos(self.raiz(), "modelos"))
        self.assertIsNone(modelos.pasta_de_modelos(self.raiz(), ""))

    def test_lista_os_modelos_em_ordem(self):
        self.assertEqual([m.nome for m in modelos.modelos(self.raiz(), "Modelos")],
                         ["Atalho", "Codigo"])

    def test_preencher_nome_e_data(self):
        texto = modelos.preencher("# {nome} - {data}", "Ctrl + P", date(2026, 9, 24))
        self.assertEqual(texto, "# Ctrl + P - 24/09/2026")

    def test_chaves_de_codigo_nao_quebram(self):
        self.assertEqual(modelos.preencher('{ "a": 1 }', "x"), '{ "a": 1 }')


class TestHistorico(unittest.TestCase):
    def setUp(self):
        self._n = cripto.SCRYPT_N
        cripto.SCRYPT_N = 2 ** 10
        self.dir = Path(tempfile.mkdtemp())
        self.arquivo = self.dir / 'keybase_data.json'

    def tearDown(self):
        cripto.SCRYPT_N = self._n
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_versoes_distintas_sem_a_atual(self):
        doc = storage.Documento.novo()
        nota = tree.novo_file("n", "v1")
        tree.adicionar(doc.raiz, nota)
        storage.salvar(doc, self.arquivo)        # vira o snapshot de hoje
        tree.definir_conteudo(nota, "v2")
        storage.salvar(doc, self.arquivo)        # .bak = v1
        tree.definir_conteudo(nota, "v3")
        storage.salvar(doc, self.arquivo)        # .bak = v2
        textos = [v.conteudo for v in historico.versoes(self.arquivo, nota.id, atual="v3")]
        self.assertEqual(textos, ["v2", "v1"])

    def test_versao_cifrada_dentro_de_pasta_cifrada(self):
        doc = storage.Documento.novo()
        cofre = cripto.Cofre.criar("segredo1")
        doc.cofre = cofre.to_dict()
        pasta = tree.novo_folder("P")
        nota = tree.novo_file("n", "antiga")
        tree.adicionar(doc.raiz, pasta)
        tree.adicionar(pasta, nota)
        cripto.cifrar_pasta(cofre, pasta)
        storage.salvar(doc, self.arquivo)
        tree.definir_conteudo(nota, "nova")
        cripto.selar_pastas(doc.raiz, cofre)
        storage.salvar(doc, self.arquivo)
        textos = [v.conteudo for v in historico.versoes(self.arquivo, nota.id, cofre,
                                                        atual="nova")]
        self.assertEqual(textos, ["antiga"])
        cofre.trancar()
        self.assertEqual(historico.versoes(self.arquivo, nota.id, cofre, atual="nova"), [])

    def test_senha_trocada_ainda_abre_versoes_antigas(self):
        doc = storage.Documento.novo()
        cofre = cripto.Cofre.criar("antiga1")
        doc.cofre = cofre.to_dict()
        nota = tree.novo_file("n", "antes")
        tree.adicionar(doc.raiz, nota)
        cripto.cifrar_nota(cofre, nota)
        storage.salvar(doc, self.arquivo)
        cofre.trocar_senha("antiga1", "novinha1")
        doc.cofre = cofre.to_dict()
        cripto.selar(cofre, nota, "depois")
        storage.salvar(doc, self.arquivo)
        textos = [v.conteudo for v in historico.versoes(self.arquivo, nota.id, cofre,
                                                        atual="depois")]
        self.assertEqual(textos, ["antes"])


if __name__ == '__main__':
    unittest.main()
