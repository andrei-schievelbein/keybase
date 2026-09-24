import json
import os
import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keybase import config


class BaseConfig(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.toml = self.dir / 'keybase_config.toml'
        self.estado = self.dir / 'keybase_estado.json'
        self.legado = self.dir / 'window_config.json'

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def carregar(self):
        return config.carregar_config(self.toml, self.estado, self.legado)


class TestModelo(BaseConfig):
    def test_modelo_e_toml_valido_e_volta_os_padroes(self):
        texto = config.modelo_toml()
        tomllib.loads(texto)
        usuario, erros = config.validar_texto(texto)
        self.assertEqual(erros, [])
        self.assertEqual(usuario['theme'], 'dark')
        self.assertEqual(usuario['cofre']['auto_lock_min'], 10)

    def test_modelo_tem_comentarios(self):
        self.assertIn("# Tema:", config.modelo_toml())


class TestValidacao(BaseConfig):
    def test_erro_de_sintaxe_traz_a_linha(self):
        _, erros = config.validar_texto('tema = "dark"\n[fontes]\nfamilia = Consolas\n')
        self.assertIn("linha 3", erros[0])

    def test_chave_desconhecida_e_recusada(self):
        _, erros = config.validar_texto('[fontes]\ntamanho_said = 12\n')
        self.assertIn("Chave desconhecida: fontes.tamanho_said", erros)

    def test_secao_desconhecida_e_recusada(self):
        _, erros = config.validar_texto('[janela]\nx = 1\n')
        self.assertIn("Seção desconhecida: [janela]", erros)

    def test_valor_fora_da_faixa_e_recusado(self):
        _, erros = config.validar_texto('[fontes]\ntamanho_saida = 200\n')
        self.assertIn("fontes.tamanho_saida deveria ser entre 6 e 72", erros)

    def test_tempo_do_aviso_tem_faixa(self):
        _, erros = config.validar_texto('[interface]\ntempo_aviso_ms = 100\n')
        self.assertIn("interface.tempo_aviso_ms deveria ser entre 500 e 30000", erros)

    def test_tema_invalido(self):
        _, erros = config.validar_texto('tema = "azul"\n')
        self.assertIn('tema deveria ser "dark" ou "light"', erros)

    def test_booleano_nao_passa_por_numero(self):
        _, erros = config.validar_texto('[cofre]\ntrancar_apos_min = true\n')
        self.assertIn("cofre.trancar_apos_min deveria ser um número inteiro", erros)

    def test_chave_que_falta_usa_o_padrao(self):
        usuario, erros = config.validar_texto('tema = "light"\n')
        self.assertEqual(erros, [])
        self.assertEqual(usuario['theme'], 'light')
        self.assertEqual(usuario['fonts']['output_size'], 14)


class TestCarga(BaseConfig):
    def test_arquivo_ausente_e_criado_com_os_padroes(self):
        cfg, erros = self.carregar()
        self.assertEqual(erros, [])
        self.assertTrue(self.toml.exists())
        self.assertEqual(cfg['theme'], 'dark')
        self.assertEqual(cfg['geometry'], '800x600')

    def test_migra_o_window_config_antigo(self):
        self.legado.write_text(json.dumps({
            "geometry": "690x578+10+20", "theme": "light",
            "fonts": {"output_size": 16, "family": "Fira Code"},
            "interface": {"help_area_height": 45},
            "cofre": {"auto_lock_min": 3},
            "editor": {"modo": "dividido"},
        }), encoding='utf-8')
        cfg, _ = self.carregar()
        texto = self.toml.read_text(encoding='utf-8')
        self.assertIn('tema = "light"', texto)
        self.assertIn('familia = "Fira Code"', texto)
        self.assertIn('trancar_apos_min = 3', texto)
        self.assertEqual(cfg['geometry'], "690x578+10+20")
        self.assertEqual(cfg['editor']['modo'], "dividido")
        self.assertTrue(self.legado.exists())   # o antigo nao e apagado

    def test_toml_invalido_usa_padroes_e_nao_sobrescreve(self):
        quebrado = 'tema = "light"\n[fontes\n'
        self.toml.write_text(quebrado, encoding='utf-8')
        cfg, erros = self.carregar()
        self.assertTrue(erros)
        self.assertEqual(cfg['theme'], 'dark')
        self.assertEqual(self.toml.read_text(encoding='utf-8'), quebrado)

    def test_estado_nao_toca_o_toml(self):
        self.carregar()
        editado = config.modelo_toml() + "\n# meu comentario\n"
        self.toml.write_text(editado, encoding='utf-8')
        cfg, _ = self.carregar()
        config.salvar_estado(cfg, "1000x700+0+0", self.estado)
        self.assertEqual(self.toml.read_text(encoding='utf-8'), editado)
        cfg, _ = self.carregar()
        self.assertEqual(cfg['geometry'], "1000x700+0+0")

    def test_salvar_texto_grava_exatamente_o_texto(self):
        texto = '# so isto\ntema = "light"\n'
        config.salvar_texto_config(texto, self.toml)
        self.assertEqual(self.toml.read_text(encoding='utf-8'), texto)

    def test_aplicar_no_config_diz_o_que_mudou(self):
        cfg, _ = self.carregar()
        usuario, _ = config.validar_texto('tema = "light"\n[fontes]\ntamanho_saida = 16\n')
        mudou = config.aplicar_no_config(cfg, usuario)
        self.assertEqual(mudou, {'theme', 'fonts'})
        self.assertEqual(cfg['theme'], 'light')
        self.assertEqual(cfg['geometry'], '800x600')   # o estado nao e tocado



class TestCompletarTexto(BaseConfig):
    SEM_AVISO = config.modelo_toml().replace(
        '# Quanto tempo um aviso ("Pasta criada.", "Itens cifrados trancados.") fica no\n'
        '# lugar do caminho antes de sumir, em milissegundos (2500 = 2,5 s). Aplica na hora.\n'
        'tempo_aviso_ms = 2500\n', '')

    def test_opcao_nova_entra_na_secao_certa_com_comentario(self):
        self.assertNotIn("tempo_aviso_ms", self.SEM_AVISO)
        novo, chaves = config.completar_texto(self.SEM_AVISO)
        self.assertEqual(chaves, ["interface.tempo_aviso_ms"])
        interface = novo[novo.index("[interface]"):novo.index("[cofre]")]
        self.assertIn("tempo_aviso_ms = 2500", interface)
        self.assertIn("# Quanto tempo um aviso", interface)
        self.assertEqual(config.validar_texto(novo)[1], [])

    def test_preserva_o_que_o_usuario_escreveu(self):
        meu = self.SEM_AVISO.replace('tema = "dark"', 'tema = "light"  # meu gosto')
        novo, _ = config.completar_texto(meu)
        self.assertIn('tema = "light"  # meu gosto', novo)

    def test_arquivo_completo_nao_muda(self):
        texto = config.modelo_toml()
        self.assertEqual(config.completar_texto(texto), (texto, []))

    def test_secao_ausente_vai_para_o_fim(self):
        novo, chaves = config.completar_texto('tema = "light"\n')
        self.assertIn("cofre.trancar_apos_min", chaves)
        self.assertTrue(novo.startswith('tema = "light"'))
        self.assertEqual(config.validar_texto(novo)[1], [])

    def test_texto_invalido_fica_intacto(self):
        quebrado = 'tema = "light"\n[fontes\n'
        self.assertEqual(config.completar_texto(quebrado), (quebrado, []))


if __name__ == '__main__':
    unittest.main()
