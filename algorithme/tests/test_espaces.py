"""Espaces réservés (salariés d'une entreprise, habitants d'une résidence) : un objet réservé à un espace ne part
qu'à un membre de cet espace ; les objets ouverts à tous restent accessibles à tous."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from troc_echanges import Marche, Souhait, math_trade  # noqa: E402


def marche(espace_b: str | None):
    """A (espace acme) réserve sa poussette aux salariés d'acme et veut un siège ; B a un siège et veut une poussette."""
    m = Marche()
    m.ajouter_utilisateur("A", [Souhait(categorie="siege")], espace="acme")
    m.ajouter_utilisateur("B", [Souhait(categorie="poussette")], espace=espace_b)
    m.ajouter_objet("pA", "A", "poussette", espace="acme")
    m.ajouter_objet("sB", "B", "siege")
    return m


class TestEspaces(unittest.TestCase):
    def test_entre_collegues(self):
        self.assertEqual(math_trade(marche("acme")).nb_objets_echanges, 2)

    def test_hors_de_l_espace(self):
        self.assertEqual(math_trade(marche(None)).nb_objets_echanges, 0)
        self.assertEqual(math_trade(marche("autre")).nb_objets_echanges, 0)

    def test_objet_ouvert_a_tous(self):
        m = marche(None)
        m.objets["pA"] = m.objets["pA"].__class__(**{**m.objets["pA"].__dict__, "espace": None})
        self.assertEqual(math_trade(m).nb_objets_echanges, 2)


if __name__ == "__main__":
    unittest.main()
