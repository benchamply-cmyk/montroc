"""Tests : python3 -m unittest discover -s tests (depuis le dossier algorithme/)."""
import random
import sys
import unittest
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from troc_echanges import (Contraintes, GrapheEchanges, Marche, Souhait, boucles_autour,  # noqa: E402
                           enumerer_boucles, math_trade, proba_tous_acceptent, remplacants, replanifier)


def marche_abc():
    """A a une poussette et veut un siège ; B a un siège et veut un vélo ; C a un vélo et veut une poussette."""
    m = Marche()
    m.ajouter_utilisateur("A", [Souhait(categorie="siege")])
    m.ajouter_utilisateur("B", [Souhait(categorie="velo")])
    m.ajouter_utilisateur("C", [Souhait(categorie="poussette")])
    m.ajouter_objet("pA", "A", "poussette")
    m.ajouter_objet("sB", "B", "siege")
    m.ajouter_objet("vC", "C", "velo")
    return m


def marche_aleatoire(seed, n_users=7, n_cat=5, objets=2, souhaits=2, longueur_libre=False):
    rnd = random.Random(seed)
    m = Marche(meme_zone=False)
    for u in range(n_users):
        ws = [Souhait(categorie=f"c{c}", rang=i + 1, quantite=rnd.choice([1, 1, 2]),
                      acceptation_auto=rnd.random() < 0.3)
              for i, c in enumerate(rnd.sample(range(n_cat), souhaits))]
        m.ajouter_utilisateur(f"u{u}", ws, fiabilite=rnd.choice([1.0, 0.9]))
    k = 0
    for u in range(n_users):
        for _ in range(objets):
            m.ajouter_objet(f"o{k}", f"u{u}", f"c{rnd.randrange(n_cat)}")
            k += 1
    return m


def verifier_solution(test, m, sol, longueur_max):
    """Une solution doit être réalisable : chaque objet donné une fois, il
    correspond à un souhait du receveur, les quantités sont respectées."""
    donnes = Counter()
    souhaits = Counter()
    for b in sol.boucles:
        if longueur_max is not None:
            test.assertLessEqual(b.longueur, longueur_max)
        test.assertEqual(len(set(b.participants)), b.longueur, "un participant par boucle")
        n = b.longueur
        for k, t in enumerate(b.transferts):
            test.assertEqual(t.receveur, b.transferts[(k + 1) % n].donneur, "la boucle se referme")
            test.assertEqual(m.objets[t.objet.id].proprietaire, t.donneur)
            s = m.utilisateurs[t.receveur].souhaits[t.souhait_idx]
            test.assertTrue(s.correspond(t.objet))
            donnes[t.objet.id] += 1
            souhaits[t.cle_souhait] += 1
    test.assertTrue(all(v == 1 for v in donnes.values()), "objet donné deux fois")
    for (u, i), v in souhaits.items():
        test.assertLessEqual(v, m.utilisateurs[u].souhaits[i].quantite)


def optimum_force_brute_borne(m, longueur_max):
    """Parcourt tous les ensembles de boucles compatibles (sans élagage par borne)."""
    g = GrapheEchanges(m)
    cands = list(enumerer_boucles(g, longueur_max, options_par_transfert=99))
    objets, souhaits = Counter(), Counter()

    def rec(k):
        if k == len(cands):
            return 0
        best = rec(k + 1)
        b = cands[k]
        if all(objets[o] == 0 for o in b.objets) and all(
                souhaits[t.cle_souhait] < g.capacite_souhait[t.cle_souhait] for t in b.transferts):
            for o in b.objets:
                objets[o] += 1
            for t in b.transferts:
                souhaits[t.cle_souhait] += 1
            best = max(best, b.longueur + rec(k + 1))
            for o in b.objets:
                objets[o] -= 1
            for t in b.transferts:
                souhaits[t.cle_souhait] -= 1
        return best

    return rec(0)


def optimum_force_brute_libre(m):
    """Plus grand ensemble de transferts où chacun reçoit autant qu'il donne."""
    g = GrapheEchanges(m)
    ts = list(g.tous_les_transferts())
    best = 0
    for mask in range(1 << len(ts)):
        choisis = [ts[i] for i in range(len(ts)) if mask >> i & 1]
        if len(choisis) <= best:
            continue
        if any(v > 1 for v in Counter(t.objet.id for t in choisis).values()):
            continue
        if any(v > g.capacite_souhait[k] for k, v in Counter(t.cle_souhait for t in choisis).items()):
            continue
        if Counter(t.donneur for t in choisis) != Counter(t.receveur for t in choisis):
            continue
        best = len(choisis)
    return best


class TestBouclesAutour(unittest.TestCase):
    def test_boucle_a_trois(self):
        bs = boucles_autour(marche_abc(), "A")
        self.assertEqual(len(bs), 1)
        b = bs[0]
        self.assertEqual(b.longueur, 3)
        self.assertEqual(set(b.participants), {"A", "B", "C"})
        self.assertAlmostEqual(b.proba_reussite, 0.7 ** 3)

    def test_echange_direct_prefere(self):
        m = marche_abc()
        m.ajouter_utilisateur("D", [Souhait(categorie="poussette", acceptation_auto=True)])
        m.ajouter_objet("sD", "D", "siege")
        bs = boucles_autour(m, "A")
        self.assertEqual([b.longueur for b in bs], [2, 3])
        self.assertEqual(set(bs[0].participants), {"A", "D"})

    def test_limite_a_deux(self):
        self.assertEqual(boucles_autour(marche_abc(), "A", longueur_max=2), [])

    def test_longueur_4_refusee(self):
        with self.assertRaises(ValueError):
            boucles_autour(marche_abc(), "A", longueur_max=4)

    def test_zone(self):
        m = marche_abc()
        m.utilisateurs["C"].zone = "Paris"
        m.utilisateurs["A"].zone = "Marseille"
        self.assertEqual(boucles_autour(m, "A"), [])

    def test_objet_precis(self):
        m = marche_abc()
        m.utilisateurs["A"].souhaits = [Souhait(objet_id="autre")]
        self.assertEqual(boucles_autour(m, "A"), [])
        m.utilisateurs["A"].souhaits = [Souhait(objet_id="sB")]
        self.assertEqual(len(boucles_autour(m, "A")), 1)

    def test_souhait_invalide(self):
        with self.assertRaises(ValueError):
            Souhait()
        with self.assertRaises(ValueError):
            Souhait(categorie="x", objet_id="y")

    def test_pas_d_echange_avec_soi_meme(self):
        m = Marche()
        m.ajouter_utilisateur("A", [Souhait(categorie="x")])
        m.ajouter_objet("o", "A", "x")
        self.assertEqual(boucles_autour(m, "A"), [])
        self.assertEqual(math_trade(m, longueur_max=None).boucles, [])


class TestMathTrade(unittest.TestCase):
    def test_abc(self):
        for lm in (3, None):
            sol = math_trade(marche_abc(), longueur_max=lm)
            self.assertEqual(sol.nb_objets_echanges, 3)
            self.assertTrue(sol.optimal)

    def test_maximise_le_nombre_d_echanges(self):
        # A peut faire un échange direct avec D, ou une boucle à 3 avec B et C.
        m = marche_abc()
        m.ajouter_utilisateur("D", [Souhait(categorie="poussette")])
        m.ajouter_objet("sD", "D", "siege")
        sol = math_trade(m, longueur_max=3)
        self.assertEqual(sol.nb_objets_echanges, 3)
        # En espérance, l'échange direct est plus sûr : 2*0.49 = 0.98 < 3*0.343 = 1.03,
        # la boucle à 3 reste meilleure ; avec acceptation auto, l'échange direct gagne.
        m.utilisateurs["A"].souhaits = [Souhait(categorie="siege", acceptation_auto=True)]
        m.utilisateurs["D"].souhaits = [Souhait(categorie="poussette", acceptation_auto=True)]
        sol_e = math_trade(m, longueur_max=3, objectif="esperance")
        self.assertEqual([b.longueur for b in sol_e.boucles], [2])

    def test_quantite_souhait(self):
        # A veut UN siège ; B et D en ont chacun un et veulent les objets de A.
        m = Marche()
        m.ajouter_utilisateur("A", [Souhait(categorie="siege")])
        m.ajouter_utilisateur("B", [Souhait(categorie="livre")])
        m.ajouter_utilisateur("D", [Souhait(categorie="livre")])
        m.ajouter_objet("l1", "A", "livre")
        m.ajouter_objet("l2", "A", "livre")
        m.ajouter_objet("sB", "B", "siege")
        m.ajouter_objet("sD", "D", "siege")
        for lm in (3, None):
            self.assertEqual(math_trade(m, longueur_max=lm).nb_objets_echanges, 2)
        m.utilisateurs["A"].souhaits = [Souhait(categorie="siege", quantite=2)]
        for lm in (3, None):
            self.assertEqual(math_trade(m, longueur_max=lm).nb_objets_echanges, 4)

    def test_boucle_de_quatre(self):
        m = Marche()
        for u, has, want in [("A", "a", "b"), ("B", "b", "c"), ("C", "c", "d"), ("D", "d", "a")]:
            m.ajouter_utilisateur(u, [Souhait(categorie=want)])
        for u, has, want in [("A", "a", "b"), ("B", "b", "c"), ("C", "c", "d"), ("D", "d", "a")]:
            m.ajouter_objet(has + "1", u, has)
        self.assertEqual(math_trade(m, longueur_max=3).nb_objets_echanges, 0)
        sol = math_trade(m, longueur_max=None)
        self.assertEqual([b.longueur for b in sol.boucles], [4])

    def test_contre_force_brute(self):
        for seed in range(40):
            m = marche_aleatoire(seed)
            for lm in (2, 3):
                sol = math_trade(m, longueur_max=lm)
                verifier_solution(self, m, sol, lm)
                self.assertTrue(sol.optimal)
                self.assertEqual(sol.nb_objets_echanges, optimum_force_brute_borne(m, lm), f"seed {seed}")

    def test_libre_contre_force_brute(self):
        testes = 0
        for seed in range(200):
            m = marche_aleatoire(seed, n_users=5, n_cat=4, objets=2, souhaits=1)
            if len(list(GrapheEchanges(m).tous_les_transferts())) > 14:
                continue
            testes += 1
            sol = math_trade(m, longueur_max=None)
            verifier_solution(self, m, sol, None)
            self.assertEqual(sol.nb_objets_echanges, optimum_force_brute_libre(m), f"seed {seed}")
            self.assertGreaterEqual(sol.nb_objets_echanges, math_trade(m, longueur_max=3).nb_objets_echanges)
        self.assertGreater(testes, 50)

    def test_grand_marche(self):
        m = marche_aleatoire(1, n_users=600, n_cat=150, objets=3, souhaits=4)
        sol3 = math_trade(m, longueur_max=3, duree_max_s=3)
        verifier_solution(self, m, sol3, 3)
        sol_libre = math_trade(m, longueur_max=None)
        verifier_solution(self, m, sol_libre, None)
        self.assertGreater(sol3.nb_objets_echanges, 0)
        self.assertGreaterEqual(sol_libre.nb_objets_echanges, sol3.nb_objets_echanges)


class TestRobustesse(unittest.TestCase):
    def test_probas_de_l_etude(self):
        self.assertAlmostEqual(round(proba_tous_acceptent(0.7, 2), 2), 0.49)
        self.assertAlmostEqual(round(proba_tous_acceptent(0.7, 3), 2), 0.34)

    def test_remplacement_apres_refus(self):
        m = marche_abc()
        m.ajouter_utilisateur("D", [Souhait(categorie="poussette")])
        m.ajouter_objet("sD", "D", "siege")
        sol = math_trade(m)
        boucle = sol.boucles[0]
        self.assertIn("B", boucle.participants)
        r = remplacants(m, boucle, "B")
        self.assertEqual(set(r["A"][0].participants), {"A", "D"})
        self.assertEqual(r["C"], [])
        nouvelle = replanifier(m, [], [(boucle, "B")])
        self.assertEqual([set(b.participants) for b in nouvelle.boucles], [{"A", "D"}])

    def test_boucles_maintenues_reservees(self):
        m = marche_abc()
        sol = math_trade(m)
        nouvelle = replanifier(m, sol.boucles, [])
        self.assertEqual(nouvelle.boucles, [])

    def test_refusant_hors_boucle(self):
        m = marche_abc()
        b = math_trade(m).boucles[0]
        with self.assertRaises(ValueError):
            replanifier(m, [], [(b, "Z")])

    def test_contraintes_objet_indisponible(self):
        m = marche_abc()
        c = Contraintes(objets_indisponibles={"sB"})
        self.assertEqual(math_trade(m, contraintes=c).boucles, [])


if __name__ == "__main__":
    unittest.main()
