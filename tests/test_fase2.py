"""Logica sem Qt da fase 2: conflito de arquivo, pasta de dados e exportacao."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keybase import cripto, exportar, paths, storage, tree


class BaseTmp(unittest.TestCase):
    def setUp(self):
        self._n = cripto.SCRYPT_N
        cripto.SCRYPT_N = 2 ** 10
        self.dir = Path(tempfile.mkdtemp())
        self.arquivo = self.dir / 'keybase_data.json'

    def tearDown(self):
        cripto.SCRYPT_N = self._n
        shutil.rmtree(self.dir, ignore_errors=True)


class TestConflito(BaseTmp):
    def test_arquivo_alterado_por_fora_nao_e_sobrescrito(self):
        doc = storage.Documento.novo()
        storage.salvar(doc, self.arquivo)
        outro = storage.carregar(self.arquivo)          # "outro computador"
        tree.adicionar(outro.raiz, tree.novo_folder("De la"))
        storage.salvar(outro, self.arquivo)
        de_la = self.arquivo.read_bytes()

        tree.adicionar(doc.raiz, tree.novo_folder("Daqui"))
        with self.assertRaises(storage.ConflitoError):
            storage.salvar(doc, self.arquivo)
        self.assertEqual(self.arquivo.read_bytes(), de_la)

    def test_forcar_grava_e_a_versao_de_la_fica_no_bak(self):
        doc = storage.Documento.novo()
        storage.salvar(doc, self.arquivo)
        outro = storage.carregar(self.arquivo)
        tree.adicionar(outro.raiz, tree.novo_folder("De la"))
        storage.salvar(outro, self.arquivo)
        tree.adicionar(doc.raiz, tree.novo_folder("Daqui"))
        storage.salvar(doc, self.arquivo, forcar=True)
        self.assertIn("Daqui", self.arquivo.read_text(encoding='utf-8'))
        self.assertIn("De la", storage.caminho_backup(self.arquivo).read_text(encoding='utf-8'))

    def test_nossas_gravacoes_seguidas_nao_sao_conflito(self):
        doc = storage.Documento.novo()
        for nome in ("a", "b", "c"):
            tree.adicionar(doc.raiz, tree.novo_folder(nome))
            storage.salvar(doc, self.arquivo)

    def test_arquivo_criado_por_fora_depois_de_abrir_vazio_e_conflito(self):
        doc = storage.Documento.novo()                  # arquivo nao existia
        storage.salvar(storage.Documento.novo(), self.arquivo)   # outro criou
        tree.adicionar(doc.raiz, tree.novo_folder("x"))
        with self.assertRaises(storage.ConflitoError):
            storage.salvar(doc, self.arquivo)

    def test_copia_de_conflito_e_legivel(self):
        doc = storage.Documento.novo()
        tree.adicionar(doc.raiz, tree.novo_folder("Daqui"))
        copia = storage.salvar_copia_de_conflito(doc, self.arquivo)
        self.assertIn(".conflito-", copia.name)
        self.assertEqual(storage.carregar(copia).raiz.filhos[0].nome, "Daqui")

    def test_fechar_em_conflito_guarda_a_copia(self):
        doc = storage.Documento.novo()
        storage.salvar(doc, self.arquivo)
        outro = storage.carregar(self.arquivo)
        tree.adicionar(outro.raiz, tree.novo_folder("De la"))
        storage.salvar(outro, self.arquivo)
        tree.adicionar(doc.raiz, tree.novo_folder("Daqui"))
        doc.marcar_sujo()
        storage.salvar_se_sujo(doc, self.arquivo)
        copias = list(self.dir.glob('keybase_data.conflito-*.json'))
        self.assertEqual(len(copias), 1)
        self.assertIn("Daqui", copias[0].read_text(encoding='utf-8'))


class TestPastaDeDados(BaseTmp):
    def test_vazio_usa_o_padrao(self):
        self.assertEqual(paths.resolver_arquivo_dados("", self.arquivo),
                         (self.arquivo, None, None))

    def test_pasta_nova_recebe_copia_dos_dados(self):
        storage.salvar(storage.Documento.novo(), self.arquivo)
        nuvem = self.dir / 'nuvem'
        nuvem.mkdir()
        caminho, aviso, erro = paths.resolver_arquivo_dados(str(nuvem), self.arquivo)
        self.assertEqual(caminho, nuvem / 'keybase_data.json')
        self.assertTrue(caminho.exists())
        self.assertTrue(self.arquivo.exists())          # copia, nao move
        self.assertIn("copiados", aviso)
        self.assertIsNone(erro)

    def test_pasta_que_nao_existe_cai_no_padrao_com_erro(self):
        caminho, _, erro = paths.resolver_arquivo_dados(str(self.dir / 'nao'), self.arquivo)
        self.assertEqual(caminho, self.arquivo)
        self.assertIn("não existe", erro)

    def test_config_valida_a_pasta(self):
        from keybase import config
        _, erros = config.validar_texto(f'[dados]\npasta = "{self.dir}/nao-existe"\n')
        self.assertIn("dados.pasta deveria ser uma pasta que existe", erros)
        usuario, erros = config.validar_texto(f'[dados]\npasta = "{self.dir}"\n')
        self.assertEqual(erros, [])


class TestExportar(BaseTmp):
    def arvore(self):
        raiz = tree.novo_folder("KeyBase")
        vscode = tree.novo_folder("Vscode", "editor")
        tree.adicionar(raiz, vscode)
        tree.adicionar(vscode, tree.novo_file("Ctrl + P", "abre"))
        tree.adicionar(vscode, tree.novo_file("a/b:c?", "nome ruim"))
        return raiz

    def test_arvore_vira_pastas_e_md(self):
        r = exportar.exportar(self.arvore(), self.dir / 'saida')
        self.assertEqual((r.notas, r.pastas), (2, 1))
        self.assertEqual((self.dir / 'saida/Vscode/Ctrl + P.md').read_text(encoding='utf-8'), "abre")
        self.assertTrue((self.dir / 'saida/Vscode/a_b_c_.md').exists())
        self.assertEqual((self.dir / 'saida/Vscode/_descricao.md').read_text(encoding='utf-8'),
                         "editor\n")

    def test_nomes_que_colidem_ganham_numero(self):
        raiz = tree.novo_folder("r")
        tree.adicionar(raiz, tree.novo_file("a?", "1"))
        tree.adicionar(raiz, tree.novo_file("a*", "2"))
        exportar.exportar(raiz, self.dir / 'saida')
        self.assertEqual(sorted(p.name for p in (self.dir / 'saida').iterdir()),
                         ["a_ (2).md", "a_.md"])

    def test_reservado_do_windows(self):
        self.assertEqual(exportar.nome_de_arquivo("CON"), "_CON")

    def test_cifrados_pulados_ou_em_claro(self):
        cofre = cripto.Cofre.criar("segredo1")
        raiz = self.arvore()
        segredo = tree.novo_file("Senha", "sigiloso-kappa")
        tree.adicionar(raiz, segredo)
        cripto.cifrar_nota(cofre, segredo)
        pasta = tree.novo_folder("Cofre")
        tree.adicionar(pasta, tree.novo_file("x", "dentro"))
        tree.adicionar(raiz, pasta)
        cripto.cifrar_pasta(cofre, pasta)

        r = exportar.exportar(raiz, self.dir / 'sem')
        self.assertEqual(sorted(r.pulados), ["Cofre/", "Senha"])
        self.assertFalse((self.dir / 'sem/Senha.md').exists())

        r = exportar.exportar(raiz, self.dir / 'com', incluir_cifrados=True)
        self.assertEqual(r.pulados, [])
        self.assertEqual((self.dir / 'com/Senha.md').read_text(encoding='utf-8'), "sigiloso-kappa")
        self.assertEqual((self.dir / 'com/Cofre/x.md').read_text(encoding='utf-8'), "dentro")

    def test_trancado_nunca_sai_pela_metade(self):
        cofre = cripto.Cofre.criar("segredo1")
        raiz = tree.novo_folder("r")
        nota = tree.novo_file("Senha", "x")
        tree.adicionar(raiz, nota)
        cripto.cifrar_nota(cofre, nota)
        cripto.trancar_arvore(raiz)
        r = exportar.exportar(raiz, self.dir / 'saida', incluir_cifrados=True)
        self.assertEqual(r.pulados, ["Senha"])

    def test_pasta_de_saida_nao_sobrescreve(self):
        primeira = exportar.pasta_de_saida(self.dir)
        primeira.mkdir()
        self.assertNotEqual(exportar.pasta_de_saida(self.dir), primeira)


if __name__ == '__main__':
    unittest.main()
