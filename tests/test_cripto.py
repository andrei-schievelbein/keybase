import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keybase import cripto, search, storage, tree
from keybase.model import EsquemaInvalidoError, node_from_dict

SEGREDO = "senha do banco: sigiloso-kappa"


class BaseCripto(unittest.TestCase):
    def setUp(self):
        # scrypt de verdade custa ~128 MB por derivacao; nos testes o custo
        # baixo basta, e o parametro gravado no cofre continua sendo respeitado
        self._n_original = cripto.SCRYPT_N
        cripto.SCRYPT_N = 2 ** 10
        self.dir = Path(tempfile.mkdtemp())
        self.arquivo = self.dir / 'keybase_data.json'

    def tearDown(self):
        cripto.SCRYPT_N = self._n_original
        shutil.rmtree(self.dir, ignore_errors=True)

    def doc_com_nota_cifrada(self, senha="segredo1"):
        doc = storage.Documento.novo()
        pasta = tree.novo_folder("Pessoal")
        nota = tree.novo_file("Banco", SEGREDO)
        livre = tree.novo_file("Lista", "comprar pão")
        tree.adicionar(doc.raiz, pasta)
        tree.adicionar(pasta, nota)
        tree.adicionar(pasta, livre)
        cofre = cripto.Cofre.criar(senha)
        doc.cofre = cofre.to_dict()
        cripto.cifrar_nota(cofre, nota)
        return doc, cofre, nota


class TestCofre(BaseCripto):
    def test_roundtrip(self):
        cofre = cripto.Cofre.criar("segredo1")
        blob = cofre.cifrar(SEGREDO, "id1")
        self.assertNotIn("sigiloso-kappa", json.dumps(blob))
        self.assertEqual(cofre.decifrar(blob, "id1"), SEGREDO)

    def test_destravar_com_a_senha_certa(self):
        meta = cripto.Cofre.criar("segredo1").to_dict()
        cofre = cripto.Cofre.from_dict(meta)
        self.assertFalse(cofre.destravado)
        cofre.destravar("segredo1")
        self.assertTrue(cofre.destravado)

    def test_senha_errada(self):
        cofre = cripto.Cofre.from_dict(cripto.Cofre.criar("segredo1").to_dict())
        with self.assertRaises(cripto.SenhaIncorretaError):
            cofre.destravar("outra")
        self.assertFalse(cofre.destravado)

    def test_blob_de_outra_nota_nao_decifra(self):
        cofre = cripto.Cofre.criar("segredo1")
        blob = cofre.cifrar(SEGREDO, "id1")
        with self.assertRaises(cripto.BlobInvalidoError):
            cofre.decifrar(blob, "id2")

    def test_trancado_nao_cifra(self):
        cofre = cripto.Cofre.criar("segredo1")
        cofre.trancar()
        with self.assertRaises(cripto.CofreTrancadoError):
            cofre.cifrar("x", "id1")

    def test_trancar_arvore_esquece_o_texto(self):
        doc, cofre, nota = self.doc_com_nota_cifrada()
        cofre.trancar()
        cripto.trancar_arvore(doc.raiz)
        self.assertIsNone(nota.conteudo)
        cofre.destravar("segredo1")
        cripto.destravar_arvore(doc.raiz, cofre)
        self.assertEqual(nota.conteudo, SEGREDO)

    def test_selar_sem_mudanca_nao_troca_o_blob(self):
        _, cofre, nota = self.doc_com_nota_cifrada()
        antes = dict(nota.blob)
        cripto.selar(cofre, nota, SEGREDO)
        self.assertEqual(nota.blob, antes)
        cripto.selar(cofre, nota, "novo")
        self.assertNotEqual(nota.blob, antes)
        self.assertEqual(cofre.decifrar(nota.blob, nota.id), "novo")

    def test_decifrar_nota(self):
        _, cofre, nota = self.doc_com_nota_cifrada()
        cripto.decifrar_nota(cofre, nota)
        self.assertFalse(nota.cifrado)
        self.assertIsNone(nota.blob)
        self.assertEqual(nota.to_dict()["conteudo"], SEGREDO)


class TestModelo(BaseCripto):
    def test_nota_cifrada_nunca_serializa_texto_claro(self):
        _, _, nota = self.doc_com_nota_cifrada()
        d = nota.to_dict()
        self.assertNotIn("conteudo", d)
        self.assertTrue(d["cifrado"])
        self.assertNotIn("sigiloso-kappa", json.dumps(d))

    def test_cifrada_sem_blob_e_erro_de_esquema(self):
        with self.assertRaises(EsquemaInvalidoError):
            node_from_dict({"tipo": "file", "nome": "x", "cifrado": True})

    def test_pasta_comum_nao_ganha_campo_novo(self):
        self.assertNotIn("nasce_cifrada", tree.novo_folder("x").to_dict())

    def test_nasce_cifrada_ida_e_volta(self):
        pasta = tree.novo_folder("x")
        pasta.nasce_cifrada = True
        self.assertTrue(node_from_dict(pasta.to_dict()).nasce_cifrada)


class TestStorage(BaseCripto):
    def test_arquivo_nao_tem_texto_claro(self):
        doc, _, _ = self.doc_com_nota_cifrada()
        storage.salvar(doc, self.arquivo)
        texto = self.arquivo.read_text(encoding='utf-8')
        self.assertNotIn("sigiloso-kappa", texto)
        self.assertIn("comprar pão", texto)  # a nota livre continua legivel

    def test_recarregar_vem_trancado_e_destrava(self):
        doc, _, _ = self.doc_com_nota_cifrada()
        storage.salvar(doc, self.arquivo)
        recarregado = storage.carregar(self.arquivo)
        nota = recarregado.raiz.filhos[0].filhos[0]
        self.assertTrue(nota.cifrado)
        self.assertIsNone(nota.conteudo)
        cofre = cripto.Cofre.from_dict(recarregado.cofre)
        cofre.destravar("segredo1")
        cripto.destravar_arvore(recarregado.raiz, cofre)
        self.assertEqual(nota.conteudo, SEGREDO)

    def test_segundo_save_sem_mudanca_e_noop(self):
        doc, _, _ = self.doc_com_nota_cifrada()
        self.assertTrue(storage.salvar(doc, self.arquivo))
        self.assertFalse(storage.salvar(doc, self.arquivo))

    def test_save_trancado_preserva_o_blob(self):
        doc, cofre, nota = self.doc_com_nota_cifrada()
        storage.salvar(doc, self.arquivo)
        cofre.trancar()
        cripto.trancar_arvore(doc.raiz)
        tree.adicionar(doc.raiz, tree.novo_folder("Outra"))
        storage.salvar(doc, self.arquivo)
        recarregado = storage.carregar(self.arquivo)
        cofre.destravar("segredo1")
        cripto.destravar_arvore(recarregado.raiz, cofre)
        self.assertEqual(recarregado.raiz.filhos[0].filhos[0].conteudo, SEGREDO)

    def test_schema_2_carrega(self):
        doc = storage.Documento.novo()
        tree.adicionar(doc.raiz, tree.novo_file("x", "y"))
        bruto = doc.to_dict()
        bruto["schema_version"] = 2
        self.arquivo.write_text(json.dumps(bruto), encoding='utf-8')
        recarregado = storage.carregar(self.arquivo)
        self.assertEqual(recarregado.raiz.filhos[0].conteudo, "y")
        self.assertIsNone(recarregado.cofre)

    def test_nota_cifrada_sem_cofre_e_recusada(self):
        doc, _, _ = self.doc_com_nota_cifrada()
        bruto = doc.to_dict()
        del bruto["cofre"]
        self.arquivo.write_text(json.dumps(bruto), encoding='utf-8')
        with self.assertRaises(EsquemaInvalidoError):
            storage.carregar(self.arquivo)

    def test_sanear_backups_cifra_o_conteudo_antigo(self):
        doc = storage.Documento.novo()
        nota = tree.novo_file("Banco", "versao antiga sigiloso-kappa")
        tree.adicionar(doc.raiz, nota)
        storage.salvar(doc, self.arquivo)
        tree.definir_conteudo(nota, SEGREDO)
        storage.salvar(doc, self.arquivo)   # .bak e snapshot com texto claro

        cofre = cripto.Cofre.criar("segredo1")
        doc.cofre = cofre.to_dict()
        cripto.cifrar_nota(cofre, nota)
        storage.salvar(doc, self.arquivo)   # e o .bak agora tem SEGREDO em claro

        sujos = storage.backups_com_texto_claro(self.arquivo, [nota.id])
        self.assertTrue(sujos)
        n = storage.sanear_backups(self.arquivo, cofre, [nota.id])
        self.assertEqual(n, len(sujos))
        self.assertEqual(storage.backups_com_texto_claro(self.arquivo, [nota.id]), [])

        for _, arquivo in storage.backups_disponiveis(self.arquivo):
            self.assertNotIn("sigiloso-kappa", arquivo.read_text(encoding='utf-8'))
            # e o backup continua restauravel, com o conteudo DAQUELA epoca
            antigo = storage.carregar(arquivo)
            c = cripto.Cofre.from_dict(antigo.cofre)
            c.destravar("segredo1")
            cripto.destravar_arvore(antigo.raiz, c)
            self.assertIn("sigiloso-kappa", antigo.raiz.filhos[0].conteudo)


class TestBusca(BaseCripto):
    def test_trancado_so_acha_pelo_nome(self):
        doc, cofre, _ = self.doc_com_nota_cifrada()
        cofre.trancar()
        cripto.trancar_arvore(doc.raiz)
        achados, _ = search.buscar(doc.raiz, "sigiloso-kappa")
        self.assertEqual(achados, [])
        achados, _ = search.buscar(doc.raiz, "Banco")
        self.assertEqual(len(achados), 1)

    def test_destravado_acha_pelo_conteudo(self):
        doc, _, _ = self.doc_com_nota_cifrada()
        achados, _ = search.buscar(doc.raiz, "sigiloso-kappa")
        self.assertEqual(len(achados), 1)


class TestPastaCifrada(BaseCripto):
    def doc_com_pasta(self):
        doc = storage.Documento.novo()
        pasta = tree.novo_folder("Pessoal", "descricao secreta-lambda")
        sub = tree.novo_folder("Bancos-segredo-mu")
        nota = tree.novo_file("Senha-nome-nu", SEGREDO)
        tree.adicionar(doc.raiz, pasta)
        tree.adicionar(pasta, sub)
        tree.adicionar(sub, nota)
        cofre = cripto.Cofre.criar("segredo1")
        doc.cofre = cofre.to_dict()
        return doc, cofre, pasta, nota

    def test_arquivo_so_mostra_o_nome_da_pasta(self):
        doc, cofre, pasta, _ = self.doc_com_pasta()
        cripto.cifrar_pasta(cofre, pasta)
        storage.salvar(doc, self.arquivo)
        texto = self.arquivo.read_text(encoding='utf-8')
        self.assertIn("Pessoal", texto)
        for segredo in ("secreta-lambda", "segredo-mu", "nome-nu", "sigiloso-kappa"):
            self.assertNotIn(segredo, texto)

    def test_recarrega_trancada_e_abre_com_a_senha(self):
        doc, cofre, pasta, _ = self.doc_com_pasta()
        cripto.cifrar_pasta(cofre, pasta)
        storage.salvar(doc, self.arquivo)
        recarregado = storage.carregar(self.arquivo)
        p = recarregado.raiz.filhos[0]
        self.assertTrue(p.cifrada and p.trancada)
        self.assertEqual(tree.construir_indice(recarregado.raiz).keys(), {"raiz", p.id})
        c = cripto.Cofre.from_dict(recarregado.cofre)
        c.destravar("segredo1")
        cripto.destravar_arvore(recarregado.raiz, c)
        self.assertEqual(p.descricao, "descricao secreta-lambda")
        self.assertEqual(p.filhos[0].filhos[0].conteudo, SEGREDO)

    def test_segundo_save_sem_mudanca_e_noop(self):
        doc, cofre, pasta, _ = self.doc_com_pasta()
        cripto.cifrar_pasta(cofre, pasta)
        self.assertTrue(storage.salvar(doc, self.arquivo))
        cripto.selar_pastas(doc.raiz, cofre)
        self.assertFalse(storage.salvar(doc, self.arquivo))

    def test_mudanca_sem_selar_nao_vai_para_o_disco(self):
        """A rede de seguranca: blob velho nunca e gravado em silencio."""
        from keybase.model import PastaNaoSeladaError
        doc, cofre, pasta, _ = self.doc_com_pasta()
        cripto.cifrar_pasta(cofre, pasta)
        tree.adicionar(pasta, tree.novo_file("nova"))
        with self.assertRaises(PastaNaoSeladaError):
            storage.salvar(doc, self.arquivo)
        cripto.selar_pastas(doc.raiz, cofre)
        storage.salvar(doc, self.arquivo)

    def test_trancar_sela_fecha_e_preserva(self):
        doc, cofre, pasta, _ = self.doc_com_pasta()
        cripto.cifrar_pasta(cofre, pasta)
        tree.adicionar(pasta, tree.novo_file("nova", "conteudo novo"))
        cripto.trancar_arvore(doc.raiz, cofre)
        self.assertTrue(pasta.trancada)
        storage.salvar(doc, self.arquivo)
        cripto.destravar_arvore(doc.raiz, cofre)
        self.assertIn("nova", [f.nome for f in pasta.filhos])

    def test_cifrar_pasta_decifra_notas_de_dentro_e_desliga_nasce_cifrada(self):
        doc, cofre, pasta, nota = self.doc_com_pasta()
        pasta.filhos[0].nasce_cifrada = True
        cripto.cifrar_nota(cofre, nota)
        cripto.cifrar_pasta(cofre, pasta)
        self.assertFalse(nota.cifrado)
        self.assertFalse(pasta.filhos[0].nasce_cifrada)

    def test_decifrar_pasta(self):
        doc, cofre, pasta, _ = self.doc_com_pasta()
        cripto.cifrar_pasta(cofre, pasta)
        cripto.decifrar_pasta(pasta)
        storage.salvar(doc, self.arquivo)
        self.assertIn("segredo-mu", self.arquivo.read_text(encoding='utf-8'))

    def test_busca_trancada_nao_ve_nada_dentro(self):
        doc, cofre, pasta, _ = self.doc_com_pasta()
        cripto.cifrar_pasta(cofre, pasta)
        cripto.trancar_arvore(doc.raiz, cofre)
        self.assertEqual(search.buscar(doc.raiz, "segredo-mu")[0], [])
        self.assertEqual(len(search.buscar(doc.raiz, "Pessoal")[0]), 1)

    def test_apagar_trancada_exige_confirmacao_forte(self):
        doc, cofre, pasta, _ = self.doc_com_pasta()
        cripto.cifrar_pasta(cofre, pasta)
        cripto.trancar_arvore(doc.raiz, cofre)
        self.assertTrue(tree.precisa_confirmacao_forte(pasta))
        self.assertIn("cifrada", tree.resumo_delecao(pasta))

    def test_schema_3_carrega_e_schema_4_e_futuro_para_build_3(self):
        doc = storage.Documento.novo()
        bruto = doc.to_dict()
        bruto["schema_version"] = 3
        self.arquivo.write_text(json.dumps(bruto), encoding='utf-8')
        storage.carregar(self.arquivo)
        self.assertEqual(storage.SCHEMA_VERSION, 4)

    def test_sanear_backups_cifra_a_pasta_com_o_conteudo_antigo(self):
        doc, cofre, pasta, _ = self.doc_com_pasta()
        doc.cofre = None
        storage.salvar(doc, self.arquivo)
        tree.renomear(pasta.filhos[0], "Bancos-segredo-mu-2")
        storage.salvar(doc, self.arquivo)
        doc.cofre = cofre.to_dict()
        cripto.cifrar_pasta(cofre, pasta)
        storage.salvar(doc, self.arquivo)

        self.assertTrue(storage.backups_com_texto_claro(self.arquivo, [pasta.id]))
        storage.sanear_backups(self.arquivo, cofre, [pasta.id])
        self.assertEqual(storage.backups_com_texto_claro(self.arquivo, [pasta.id]), [])
        for _, arquivo in storage.backups_disponiveis(self.arquivo):
            self.assertNotIn("segredo-mu", arquivo.read_text(encoding='utf-8'))
            antigo = storage.carregar(arquivo)
            c = cripto.Cofre.from_dict(antigo.cofre)
            c.destravar("segredo1")
            cripto.destravar_arvore(antigo.raiz, c)
            self.assertIn("segredo-mu", antigo.raiz.filhos[0].filhos[0].nome)


if __name__ == '__main__':

    unittest.main()
