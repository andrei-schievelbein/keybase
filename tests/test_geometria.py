"""Testes de geometria da janela. Funcoes puras, sem Qt e sem display."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from keybase.qt.janela import (ajustar_a_area, formatar_geometria,
                               parse_geometria)

PRIMARIA = (0, 0, 1920, 1080)
SECUNDARIA = (-1920, 0, 1920, 1080)


class TestParse(unittest.TestCase):
    def test_forma_completa(self):
        self.assertEqual(parse_geometria('800x600+100+50'), (800, 600, 100, 50))

    def test_so_tamanho(self):
        self.assertEqual(parse_geometria('800x600'), (800, 600, None, None))

    def test_coordenada_negativa_do_tk(self):
        """O Tk gravava '+-1566'; ha arquivos reais nesse formato."""
        self.assertEqual(parse_geometria('630x578+-1566+174'), (630, 578, -1566, 174))

    def test_coordenada_com_sinal_de_menos(self):
        self.assertEqual(parse_geometria('800x600-100-50'), (800, 600, -100, -50))

    def test_lixo_devolve_none(self):
        for entrada in ('', 'nada', '800', 'xX', None):
            self.assertIsNone(parse_geometria(entrada))

    def test_round_trip(self):
        for texto in ('800x600+100+50', '1024x768+0+0'):
            l, a, x, y = parse_geometria(texto)
            self.assertEqual(formatar_geometria(l, a, x, y), texto)


class TestAjuste(unittest.TestCase):
    def test_dentro_da_tela_nao_muda(self):
        self.assertEqual(ajustar_a_area(800, 600, 100, 50, [PRIMARIA]),
                         (800, 600, 100, 50))

    def test_fora_de_todas_as_telas_centraliza(self):
        """O caso real: geometria salva num monitor que nao existe mais."""
        l, a, x, y = ajustar_a_area(630, 578, -1566, 174, [PRIMARIA])
        self.assertEqual((l, a), (630, 578))
        self.assertEqual(x, (1920 - 630) // 2)
        self.assertEqual(y, (1080 - 578) // 2)

    def test_monitor_secundario_existente_e_respeitado(self):
        l, a, x, y = ajustar_a_area(630, 578, -1566, 174, [PRIMARIA, SECUNDARIA])
        self.assertEqual((x, y), (-1566, 174))

    def test_parcialmente_fora_e_puxada_para_dentro(self):
        l, a, x, y = ajustar_a_area(800, 600, 1800, 900, [PRIMARIA])
        self.assertLessEqual(x + l, 1920)
        self.assertLessEqual(y + a, 1080)

    def test_maior_que_a_tela_e_encolhida(self):
        l, a, _, _ = ajustar_a_area(3000, 2000, 0, 0, [PRIMARIA])
        self.assertLessEqual(l, 1920)
        self.assertLessEqual(a, 1080)

    def test_tamanho_minimo(self):
        l, a, _, _ = ajustar_a_area(10, 10, 0, 0, [PRIMARIA])
        self.assertGreaterEqual(l, 400)
        self.assertGreaterEqual(a, 300)

    def test_sem_posicao_centraliza(self):
        l, a, x, y = ajustar_a_area(800, 600, None, None, [PRIMARIA])
        self.assertEqual(x, (1920 - 800) // 2)

    def test_sem_areas_nao_explode(self):
        self.assertEqual(ajustar_a_area(800, 600, 10, 20, []), (800, 600, 10, 20))

    def test_barra_de_titulo_permanece_alcancavel(self):
        _, _, _, y = ajustar_a_area(800, 600, 100, -500, [PRIMARIA])
        self.assertGreaterEqual(y, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
