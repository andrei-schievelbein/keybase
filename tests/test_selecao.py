"""Selecao de varios itens por numero: '1,2,5', '1-4', '1-3, 7'."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keybase.selecao import SelecaoInvalida, descricao_lote, interpretar
from keybase.tree import novo_file


class TestInterpretar(unittest.TestCase):
    def test_um_numero(self):
        self.assertEqual(interpretar("3", 5), [2])

    def test_virgula(self):
        self.assertEqual(interpretar("1,2,5", 5), [0, 1, 4])

    def test_intervalo(self):
        self.assertEqual(interpretar("1-4", 5), [0, 1, 2, 3])

    def test_intervalo_e_virgula_com_espacos(self):
        self.assertEqual(interpretar(" 1 - 3 , 5 ", 5), [0, 1, 2, 4])

    def test_repetidos_e_ordem_da_lista(self):
        self.assertEqual(interpretar("5,1,1-2", 5), [0, 1, 4])

    def test_virgula_sobrando_e_ignorada(self):
        self.assertEqual(interpretar("1,,2,", 5), [0, 1])

    def test_fora_da_lista(self):
        with self.assertRaises(SelecaoInvalida) as ctx:
            interpretar("1,9", 5)
        self.assertIn("9", str(ctx.exception))

    def test_zero(self):
        with self.assertRaises(SelecaoInvalida):
            interpretar("0", 5)

    def test_intervalo_invertido(self):
        with self.assertRaises(SelecaoInvalida) as ctx:
            interpretar("3-1", 5)
        self.assertIn("1-3", str(ctx.exception))

    def test_invalidos(self):
        for texto in ("", "  ", ",", "a", "1,a", "1-", "-2", "1--3", "M"):
            with self.subTest(texto=texto), self.assertRaises(SelecaoInvalida):
                interpretar(texto, 5)


class TestDescricaoLote(unittest.TestCase):
    def test_um_item_pelo_nome(self):
        self.assertEqual(descricao_lote("mover", [novo_file("Nota")]), "mover 'Nota'")

    def test_varios_pela_contagem(self):
        nos = [novo_file("a"), novo_file("b")]
        self.assertEqual(descricao_lote("copiar", nos), "copiar 2 itens")


if __name__ == '__main__':
    unittest.main()
