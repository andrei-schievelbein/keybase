import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keybase import storage, tree
from keybase.model import EsquemaInvalidoError, nova_raiz


class BaseStorage(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.arquivo = self.dir / 'keybase_data.json'

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def doc_exemplo(self):
        doc = storage.Documento.novo()
        vscode = tree.novo_folder("Vscode", "Editor")
        nota = tree.novo_file("Ctrl + P", "Abre o seletor.")
        tree.adicionar(doc.raiz, vscode)
        tree.adicionar(vscode, nota)
        return doc


class TestRoundTrip(BaseStorage):
    def test_salvar_e_recarregar_preserva_arvore(self):
        doc = self.doc_exemplo()
        storage.salvar(doc, self.arquivo)
        recarregado = storage.carregar(self.arquivo)
        self.assertEqual(recarregado.raiz.to_dict(), doc.raiz.to_dict())

    def test_arquivo_ausente_devolve_base_vazia(self):
        doc = storage.carregar(self.arquivo)
        self.assertEqual(doc.raiz.filhos, [])
        self.assertFalse(doc.somente_leitura)

    def test_tmp_nao_sobra(self):
        doc = self.doc_exemplo()
        storage.salvar(doc, self.arquivo)
        self.assertFalse((self.dir / 'keybase_data.json.tmp').exists())

    def test_sem_crlf_no_arquivo(self):
        doc = self.doc_exemplo()
        storage.salvar(doc, self.arquivo)
        self.assertNotIn(b'\r\n', self.arquivo.read_bytes())


class TestCorrupcao(BaseStorage):
    def test_json_invalido_levanta_e_nao_apaga_nada(self):
        """O teste que fecha o bug grave da versao anterior."""
        doc = self.doc_exemplo()
        storage.salvar(doc, self.arquivo)
        original = self.arquivo.read_bytes()
        # segundo save para existir um .bak da versao boa
        tree.adicionar(doc.raiz, tree.novo_folder("Outro"))
        storage.salvar(doc, self.arquivo)

        self.arquivo.write_text('{"schema_version": 2, "raiz": {tru', encoding='utf-8')
        corrompido = self.arquivo.read_bytes()

        with self.assertRaises(storage.DadosCorrompidosError):
            storage.carregar(self.arquivo)

        # o arquivo continua exatamente como estava: carregar nao escreve
        self.assertEqual(self.arquivo.read_bytes(), corrompido)
        # e o backup da versao boa segue disponivel
        self.assertEqual(storage.caminho_backup(self.arquivo).read_bytes(), original)

    def test_versao_futura_e_recusada(self):
        self.arquivo.write_text(
            json.dumps({"schema_version": 99, "raiz": nova_raiz().to_dict()}),
            encoding='utf-8')
        with self.assertRaises(storage.VersaoFuturaError):
            storage.carregar(self.arquivo)

    def test_schema_version_ausente_e_erro(self):
        self.arquivo.write_text(json.dumps({"raiz": nova_raiz().to_dict()}), encoding='utf-8')
        with self.assertRaises(EsquemaInvalidoError):
            storage.carregar(self.arquivo)

    def test_raiz_ausente_e_erro(self):
        self.arquivo.write_text(json.dumps({"schema_version": 2}), encoding='utf-8')
        with self.assertRaises(EsquemaInvalidoError):
            storage.carregar(self.arquivo)

    def test_modo_recuperacao_recusa_escrita(self):
        doc = storage.Documento(nova_raiz(), somente_leitura=True)
        with self.assertRaises(storage.StorageBloqueadoError):
            storage.salvar(doc, self.arquivo)


class TestBackups(BaseStorage):
    def test_segundo_save_sem_mudanca_e_noop(self):
        doc = self.doc_exemplo()
        self.assertTrue(storage.salvar(doc, self.arquivo))
        self.assertFalse(storage.salvar(doc, self.arquivo))

    def test_noop_nao_rotaciona_backup(self):
        doc = self.doc_exemplo()
        storage.salvar(doc, self.arquivo)
        bak = storage.caminho_backup(self.arquivo)
        antes = bak.read_bytes() if bak.exists() else None
        storage.salvar(doc, self.arquivo)
        depois = bak.read_bytes() if bak.exists() else None
        self.assertEqual(antes, depois)

    def test_bak_guarda_a_versao_anterior(self):
        doc = self.doc_exemplo()
        storage.salvar(doc, self.arquivo)
        v1 = self.arquivo.read_bytes()

        tree.adicionar(doc.raiz, tree.novo_folder("Novo"))
        storage.salvar(doc, self.arquivo)

        self.assertEqual(storage.caminho_backup(self.arquivo).read_bytes(), v1)
        self.assertNotEqual(self.arquivo.read_bytes(), v1)

    def test_snapshot_do_dia_e_criado_uma_vez(self):
        doc = self.doc_exemplo()
        storage.salvar(doc, self.arquivo)
        tree.adicionar(doc.raiz, tree.novo_folder("A"))
        storage.salvar(doc, self.arquivo)
        snap = storage.caminho_snapshot(self.arquivo)
        primeiro = snap.read_bytes()

        tree.adicionar(doc.raiz, tree.novo_folder("B"))
        storage.salvar(doc, self.arquivo)
        self.assertEqual(snap.read_bytes(), primeiro)

    def test_snapshot_forcado_antes_de_delete(self):
        doc = self.doc_exemplo()
        storage.salvar(doc, self.arquivo)
        antes = self.arquivo.read_bytes()

        storage.snapshot(doc, self.arquivo)
        tree.remover(doc.raiz, doc.raiz.filhos[0])
        storage.salvar(doc, self.arquivo)

        self.assertEqual(storage.caminho_backup(self.arquivo).read_bytes(), antes)

    def test_restaurar_volta_o_conteudo(self):
        doc = self.doc_exemplo()
        storage.salvar(doc, self.arquivo)
        v1 = self.arquivo.read_bytes()

        tree.adicionar(doc.raiz, tree.novo_folder("Novo"))
        storage.salvar(doc, self.arquivo)

        storage.restaurar(storage.caminho_backup(self.arquivo), self.arquivo)
        self.assertEqual(self.arquivo.read_bytes(), v1)

    def test_backups_disponiveis_lista(self):
        doc = self.doc_exemplo()
        storage.salvar(doc, self.arquivo)
        tree.adicionar(doc.raiz, tree.novo_folder("Novo"))
        storage.salvar(doc, self.arquivo)
        self.assertTrue(storage.backups_disponiveis(self.arquivo))


class TestSujo(BaseStorage):
    def test_salvar_se_sujo_nao_levanta_em_modo_leitura(self):
        doc = storage.Documento(nova_raiz(), somente_leitura=True)
        doc.marcar_sujo()
        storage.salvar_se_sujo(doc, self.arquivo)  # nao pode explodir
        self.assertFalse(self.arquivo.exists())

    def test_salvar_limpa_a_flag(self):
        doc = self.doc_exemplo()
        doc.marcar_sujo()
        storage.salvar(doc, self.arquivo)
        self.assertFalse(doc.sujo)


class TestReparo(BaseStorage):
    def test_no_sem_id_e_reparado_com_aviso(self):
        bruto = {
            "schema_version": 2,
            "raiz": {
                "tipo": "folder", "id": "raiz", "nome": "KeyBase",
                "filhos": [{"tipo": "file", "nome": "sem id", "conteudo": "x"}],
            },
        }
        self.arquivo.write_text(json.dumps(bruto), encoding='utf-8')
        doc = storage.carregar(self.arquivo)
        self.assertEqual(len(doc.avisos), 1)
        self.assertTrue(doc.raiz.filhos[0].id)
        self.assertTrue(doc.sujo)


if __name__ == "__main__":
    unittest.main(verbosity=2)
