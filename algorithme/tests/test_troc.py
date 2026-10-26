"""Tests : python3 -m unittest discover -s tests (depuis le dossier algorithme/)."""
import random
import sys
import unittest
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from troc_echanges import (Contraintes, GrapheEchanges, Marche, Souhait, boucles_autour,  # noqa: E402
                           enumerer_boucles, math_trade, proba_tous_acceptent, remplacants, replanifier,
                           solveur_exact)

AVEC_ORTOOLS = unittest.skipUnless(solveur_exact.disponible(), "OR-Tools n'est pas installé")


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
            test.assertTrue(t.objet.accepte(b.transferts[k - 1]), "liste « contre » stricte respectée")
            donnes[t.objet.id] += 1
            souhaits[t.cle_souhait] += 1
    test.assertTrue(all(v == 1 for v in donnes.values()), "objet donné deux fois")
    for (u, i), v in souhaits.items():
        test.assertLessEqual(v, m.utilisateurs[u].souhaits[i].quantite)


def optimum_force_brute_borne(m, longueur_max, valeur=lambda b: b.longueur):
    """Parcourt tous les ensembles de boucles compatibles (sans élagage par borne) ; ``valeur`` d'une boucle :
    sa longueur (objets échangés) ou, pour l'objectif « esperance », longueur × chance de réussite."""
    g = GrapheEchanges(m)
    cands = list(enumerer_boucles(g, longueur_max, options_par_transfert=99, variantes=True))
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
            best = max(best, valeur(b) + rec(k + 1))
            for o in b.objets:
                objets[o] -= 1
            for t in b.transferts:
                souhaits[t.cle_souhait] -= 1
        return best

    return rec(0)


def optimum_force_brute_libre(m):
    """Plus grand ensemble de transferts où chacun reçoit autant qu'il donne."""
    g = GrapheEchanges(m)
    ts = list(g.tous_les_transferts(variantes=True))
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

    def test_longueur_hors_bornes_refusee(self):
        for lm in (1, 7):
            with self.assertRaises(ValueError):
                boucles_autour(marche_abc(), "A", longueur_max=lm)

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

    def test_coups_de_coeur_regroupes(self):
        # A aime le siège de B et celui de D, qui veulent chacun un livre de A : un seul souhait de quantité 1.
        m = Marche()
        m.ajouter_utilisateur("A", [Souhait(objets={"sB", "sD"})])
        m.ajouter_utilisateur("B", [Souhait(categorie="livre")])
        m.ajouter_utilisateur("D", [Souhait(categorie="livre")])
        m.ajouter_objet("l1", "A", "livre")
        m.ajouter_objet("l2", "A", "livre")
        m.ajouter_objet("sB", "B", "siege")
        m.ajouter_objet("sD", "D", "siege")
        for lm in (3, None):
            self.assertEqual(math_trade(m, longueur_max=lm).nb_objets_echanges, 2)
        m.utilisateurs["A"].souhaits = [Souhait(objets={"sB", "sD"}, quantite=2)]
        for lm in (3, None):
            self.assertEqual(math_trade(m, longueur_max=lm).nb_objets_echanges, 4)
        with self.assertRaises(ValueError):
            Souhait(objet_id="sB", objets={"sD"})

    def test_sous_categorie_et_criteres(self):
        """Une sous-catégorie ou une taille demandées écartent les objets qui en précisent une autre."""
        m = Marche()
        m.ajouter_utilisateur("A", [Souhait(categorie="siege")])
        m.ajouter_objet("pA", "A", "poussette")
        m.ajouter_utilisateur("B", [Souhait(categorie="poussette", sous_categorie="canne", criteres=(("age", "0-6 mois"),))])
        m.ajouter_objet("sB", "B", "siege")
        m.retirer_objet("pA")
        m.ajouter_objet("pA", "A", "poussette", sous_categorie="trio")
        self.assertEqual(boucles_autour(m, "A"), [])
        m.retirer_objet("pA")
        m.ajouter_objet("pA", "A", "poussette", sous_categorie="canne", caracteristiques={"age": "6-36 mois"})
        self.assertEqual(boucles_autour(m, "A"), [])
        m.retirer_objet("pA")
        m.ajouter_objet("pA", "A", "poussette", sous_categorie="canne", caracteristiques={"age": "0-6 mois"})
        self.assertEqual(len(boucles_autour(m, "A")), 1)
        # Un critère obligatoire que l'objet ne précise pas l'écarte aussi.
        m.retirer_objet("pA")
        m.ajouter_objet("pA", "A", "poussette", sous_categorie="canne")
        self.assertEqual(boucles_autour(m, "A"), [])
        # Un souhait de toute la catégorie prend toutes les sous-catégories.
        m.utilisateurs["B"].souhaits = [Souhait(categorie="poussette")]
        m.retirer_objet("pA")
        m.ajouter_objet("pA", "A", "poussette", sous_categorie="trio")
        self.assertEqual(len(boucles_autour(m, "A")), 1)
        with self.assertRaises(ValueError):
            Souhait(objet_id="x", sous_categorie="canne")

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

    def test_plafond_par_personne(self):
        # D a 4 livres et veut des sièges ; 4 personnes ont chacune un siège et veulent un livre.
        def marche(plafond=None):
            m = Marche()
            m.ajouter_utilisateur("D", [Souhait(categorie="siege", quantite=4)], plafond=plafond)
            for k in range(4):
                m.ajouter_utilisateur(f"P{k}", [Souhait(categorie="livre")])
                m.ajouter_objet(f"l{k}", "D", "livre")
                m.ajouter_objet(f"s{k}", f"P{k}", "siege")
            return m
        moteurs = ["heuristique"] + (["exact"] if solveur_exact.disponible() else [])
        for moteur in moteurs:
            self.assertEqual(math_trade(marche(), moteur=moteur, options_par_transfert=4).nb_objets_echanges, 8)
            sol = math_trade(marche(plafond=2), moteur=moteur, options_par_transfert=4)
            self.assertEqual(sol.nb_objets_echanges, 4)
            self.assertEqual(sum("D" in b.participants for b in sol.boucles), 2)
        self.assertEqual(math_trade(marche(plafond=2), longueur_max=None).nb_objets_echanges, 4)
        self.assertEqual(math_trade(marche(plafond=0), longueur_max=None).nb_objets_echanges, 0)

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


def marche_contre(seed, n_users=5, n_cat=4):
    """Marché aléatoire avec 3 objets par personne, dont certains à liste « contre » stricte ou de préférence."""
    rnd = random.Random(seed)
    m = Marche(meme_zone=False)
    for u in range(n_users):
        ws = [Souhait(categorie=f"c{c}", rang=i + 1, quantite=rnd.choice([1, 2]))
              for i, c in enumerate(rnd.sample(range(n_cat), 2))]
        m.ajouter_utilisateur(f"u{u}", ws)
    k = 0
    for u in range(n_users):
        for _ in range(3):
            contre = {i for i in range(2) if rnd.random() < 0.4}
            m.ajouter_objet(f"o{k}", f"u{u}", f"c{rnd.randrange(n_cat)}", contre=contre,
                            contre_strict=rnd.random() < 0.5)
            k += 1
    return m


def marche_souhaits_recouvrants(seed, n_users=5, n_cat=3):
    """Marché aléatoire où un même objet peut remplir deux souhaits de son receveur : le premier accepte une
    alternative, qui est la catégorie du second."""
    rnd = random.Random(seed)
    m = Marche(meme_zone=False)
    for u in range(n_users):
        a, b = rnd.sample(range(n_cat), 2)
        m.ajouter_utilisateur(f"u{u}", [Souhait(categorie=f"c{a}", alternatives=((f"c{b}", None),)),
                                        Souhait(categorie=f"c{b}", rang=2)])
    for k in range(2 * n_users):
        m.ajouter_objet(f"o{k}", f"u{k % n_users}", f"c{rnd.randrange(n_cat)}")
    return m


class TestMoteurExact(unittest.TestCase):
    @staticmethod
    def marche_trois_paires():
        """A et B ont chacun trois objets que l'autre veut (souhaits de quantité 3)."""
        m = Marche()
        m.ajouter_utilisateur("A", [Souhait(categorie="Y", quantite=3)])
        m.ajouter_utilisateur("B", [Souhait(categorie="X", quantite=3)])
        for i in range(3):
            m.ajouter_objet(f"a{i}", "A", "X")
            m.ajouter_objet(f"b{i}", "B", "Y")
        return m

    @AVEC_ORTOOLS
    def test_tous_les_objets_entre_deux_personnes(self):
        # L'énumération ne garde que 2 objets par couple : l'heuristique s'arrête à 4 objets.
        m = self.marche_trois_paires()
        sol = math_trade(m, longueur_max=3, moteur="exact")
        verifier_solution(self, m, sol, 3)
        self.assertEqual((sol.nb_objets_echanges, sol.optimal, sol.moteur), (6, True, "exact"))
        self.assertEqual(math_trade(m, longueur_max=3, moteur="heuristique").nb_objets_echanges, 4)

    def test_heuristique_ne_se_dit_pas_optimale_quand_elle_ecarte_des_boucles(self):
        # 3 objets par couple, l'énumération n'en garde que 2 : 4 objets échangés, sans preuve.
        sol = math_trade(self.marche_trois_paires(), longueur_max=3, moteur="heuristique")
        self.assertEqual((sol.nb_objets_echanges, sol.optimal), (4, False))
        self.assertFalse(sol.stats["enumeration_complete"])
        # Avec assez d'options par couple, rien n'est écarté : l'optimum (6) est prouvé.
        sol = math_trade(self.marche_trois_paires(), longueur_max=3, moteur="heuristique", options_par_transfert=3)
        self.assertEqual((sol.nb_objets_echanges, sol.optimal), (6, True))
        # Un objet qui remplit deux souhaits du receveur : l'heuristique n'en voit qu'un, pas de preuve non plus.
        m = Marche()
        m.ajouter_utilisateur("A", [Souhait(categorie="poussette", alternatives=(("siege", None),)),
                                    Souhait(categorie="siege", rang=2)])
        m.ajouter_utilisateur("B", [Souhait(categorie="livre", quantite=2)])
        for i in range(2):
            m.ajouter_objet(f"s{i}", "B", "siege")
            m.ajouter_objet(f"l{i}", "A", "livre")
        sol = math_trade(m, longueur_max=3, moteur="heuristique")
        self.assertEqual((sol.nb_objets_echanges, sol.optimal), (2, False))

    @AVEC_ORTOOLS
    def test_un_objet_pour_un_autre_souhait(self):
        # Les deux sièges de B remplissent les deux souhaits de A (le premier par son alternative) :
        # chacun en comble un. Avant, un objet ne comptait que pour le meilleur souhait : 2 objets au lieu de 4.
        m = Marche()
        m.ajouter_utilisateur("A", [Souhait(categorie="poussette", alternatives=(("siege", None),)),
                                    Souhait(categorie="siege", rang=2)])
        m.ajouter_utilisateur("B", [Souhait(categorie="livre", quantite=2)])
        for i in range(2):
            m.ajouter_objet(f"s{i}", "B", "siege")
            m.ajouter_objet(f"l{i}", "A", "livre")
        for lm in (2, 3, None):
            sol = math_trade(m, longueur_max=lm, moteur="exact") if lm else math_trade(m, longueur_max=None)
            verifier_solution(self, m, sol, lm)
            self.assertEqual((sol.nb_objets_echanges, sol.optimal), (4, True), lm)
        self.assertEqual({t.souhait_idx for b in sol.boucles for t in b.transferts if t.receveur == "A"}, {0, 1})

    @AVEC_ORTOOLS
    def test_souhaits_qui_se_recouvrent_contre_force_brute(self):
        for seed in range(30):
            m = marche_souhaits_recouvrants(seed)
            for lm in (2, 3):
                sol = math_trade(m, longueur_max=lm, moteur="exact")
                verifier_solution(self, m, sol, lm)
                self.assertTrue(sol.optimal)
                self.assertEqual(sol.nb_objets_echanges, optimum_force_brute_borne(m, lm), f"seed {seed}")

    def test_souhaits_qui_se_recouvrent_libre_contre_force_brute(self):
        testes = 0
        for seed in range(100):
            m = marche_souhaits_recouvrants(seed, n_users=3)
            if len(list(GrapheEchanges(m).tous_les_transferts(variantes=True))) > 14:
                continue
            testes += 1
            sol = math_trade(m, longueur_max=None)
            verifier_solution(self, m, sol, None)
            self.assertEqual(sol.nb_objets_echanges, optimum_force_brute_libre(m), f"seed {seed}")
        self.assertGreater(testes, 20)

    @AVEC_ORTOOLS
    def test_un_objet_pour_un_autre_souhait(self):
        # Les deux sièges de B remplissent les deux souhaits de A (le premier par son alternative) :
        # chacun en comble un. Avant, un objet ne comptait que pour le meilleur souhait : 2 objets au lieu de 4.
        m = Marche()
        m.ajouter_utilisateur("A", [Souhait(categorie="poussette", alternatives=(("siege", None),)),
                                    Souhait(categorie="siege", rang=2)])
        m.ajouter_utilisateur("B", [Souhait(categorie="livre", quantite=2)])
        for i in range(2):
            m.ajouter_objet(f"s{i}", "B", "siege")
            m.ajouter_objet(f"l{i}", "A", "livre")
        for lm in (2, 3, None):
            sol = math_trade(m, longueur_max=lm, moteur="exact") if lm else math_trade(m, longueur_max=None)
            verifier_solution(self, m, sol, lm)
            self.assertEqual((sol.nb_objets_echanges, sol.optimal), (4, True), lm)
        self.assertEqual({t.souhait_idx for b in sol.boucles for t in b.transferts if t.receveur == "A"}, {0, 1})

    @AVEC_ORTOOLS
    def test_souhaits_qui_se_recouvrent_contre_force_brute(self):
        for seed in range(30):
            m = marche_souhaits_recouvrants(seed)
            for lm in (2, 3):
                sol = math_trade(m, longueur_max=lm, moteur="exact")
                verifier_solution(self, m, sol, lm)
                self.assertTrue(sol.optimal)
                self.assertEqual(sol.nb_objets_echanges, optimum_force_brute_borne(m, lm), f"seed {seed}")

    def test_souhaits_qui_se_recouvrent_libre_contre_force_brute(self):
        testes = 0
        for seed in range(100):
            m = marche_souhaits_recouvrants(seed, n_users=3)
            if len(list(GrapheEchanges(m).tous_les_transferts(variantes=True))) > 14:
                continue
            testes += 1
            sol = math_trade(m, longueur_max=None)
            verifier_solution(self, m, sol, None)
            self.assertEqual(sol.nb_objets_echanges, optimum_force_brute_libre(m), f"seed {seed}")
        self.assertGreater(testes, 20)

    @AVEC_ORTOOLS
    def test_contre_force_brute_avec_listes_contre(self):
        for seed in range(30):
            m = marche_contre(seed)
            for lm in (2, 3):
                sol = math_trade(m, longueur_max=lm, moteur="exact")
                verifier_solution(self, m, sol, lm)
                self.assertTrue(sol.optimal)
                self.assertEqual(sol.nb_objets_echanges, optimum_force_brute_borne(m, lm), f"seed {seed}")

    @AVEC_ORTOOLS
    def test_le_plus_de_personnes_servies(self):
        # A peut faire deux échanges avec B, ou un avec B et un avec C : autant d'objets, mais C est servi.
        m = Marche()
        m.ajouter_utilisateur("A", [Souhait(categorie="Y", quantite=2)])
        m.ajouter_utilisateur("B", [Souhait(categorie="X", quantite=2)])
        m.ajouter_utilisateur("C", [Souhait(categorie="X")])
        for o, u, c in [("a1", "A", "X"), ("a2", "A", "X"), ("b1", "B", "Y"), ("b2", "B", "Y"), ("c1", "C", "Y")]:
            m.ajouter_objet(o, u, c)
        sol = math_trade(m, longueur_max=3, moteur="exact")
        self.assertEqual(sol.nb_objets_echanges, 4)
        self.assertEqual(sol.participants, {"A", "B", "C"})

    def test_contre_strict(self):
        # A ne donne sa poussette que contre un siège ; B n'a qu'un livre (que A souhaite aussi).
        def marche(strict):
            m = Marche()
            m.ajouter_utilisateur("A", [Souhait(categorie="siege"), Souhait(categorie="livre")])
            m.ajouter_utilisateur("B", [Souhait(categorie="poussette")])
            m.ajouter_objet("p", "A", "poussette", contre={0}, contre_strict=strict)
            m.ajouter_objet("l", "B", "livre")
            return m
        moteurs = ["heuristique"] + (["exact"] if solveur_exact.disponible() else [])
        for moteur in moteurs:
            self.assertEqual(math_trade(marche(True), moteur=moteur).nb_objets_echanges, 0, moteur)
            self.assertEqual(math_trade(marche(False), moteur=moteur).nb_objets_echanges, 2, moteur)
        self.assertEqual(boucles_autour(marche(True), "A"), [])

    def test_contre_preference(self):
        # B (livre) et C (siège) veulent la poussette ; A la donne de préférence contre un siège.
        m = Marche()
        m.ajouter_utilisateur("A", [Souhait(categorie="livre"), Souhait(categorie="siege")])
        m.ajouter_utilisateur("B", [Souhait(categorie="poussette")])
        m.ajouter_utilisateur("C", [Souhait(categorie="poussette")])
        m.ajouter_objet("p", "A", "poussette", contre={1})
        m.ajouter_objet("l", "B", "livre")
        m.ajouter_objet("s", "C", "siege")
        moteurs = ["heuristique"] + (["exact"] if solveur_exact.disponible() else [])
        for moteur in moteurs:
            sol = math_trade(m, moteur=moteur)
            self.assertEqual(sol.participants, {"A", "C"}, moteur)
            self.assertEqual(sol.boucles[0].preferences_respectees, 1)

    def test_contre_designe_ses_propres_souhaits(self):
        m = Marche()
        m.ajouter_utilisateur("A", [Souhait(categorie="siege")])
        with self.assertRaises(ValueError):
            m.ajouter_objet("p", "A", "poussette", contre={1})


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


def marche_paire(souhait_de_a: Souhait, **objet_de_b):
    """A a une poussette et veut ce que décrit ``souhait_de_a`` ; B a l'objet ``bB`` et veut une poussette."""
    m = Marche()
    m.ajouter_utilisateur("A", [souhait_de_a])
    m.ajouter_utilisateur("B", [Souhait(categorie="poussette")])
    m.ajouter_objet("pA", "A", "poussette")
    m.ajouter_objet("bB", "B", **{"categorie": "bricolage", **objet_de_b})
    return m


def echange_possible(m) -> bool:
    return bool(boucles_autour(m, "A"))


class TestReglesDuMatching(unittest.TestCase):
    """Les dix règles du document « Catégories et caractéristiques » (section 13)."""

    def test_1_intercategories(self):
        sol = math_trade(marche_abc())
        self.assertEqual(sol.nb_objets_echanges, 3)
        self.assertEqual(len({t.objet.categorie for t in sol.boucles[0].transferts}), 3)

    def test_2_criteres_obligatoires(self):
        bosch = Souhait(categorie="bricolage", criteres=(("marque", "Bosch"),))
        self.assertTrue(echange_possible(marche_paire(bosch, caracteristiques={"marque": " bosch "})))
        self.assertFalse(echange_possible(marche_paire(bosch, caracteristiques={"marque": "Makita"})))
        self.assertFalse(echange_possible(marche_paire(bosch)), "marque non précisée")

    def test_2_etat_minimum(self):
        tres_bon = Souhait(categorie="bricolage", etat_min="tres_bon")
        self.assertFalse(echange_possible(marche_paire(tres_bon, etat="bon")))
        self.assertTrue(echange_possible(marche_paire(tres_bon, etat="comme_neuf")))
        self.assertFalse(echange_possible(marche_paire(tres_bon)), "état non précisé")
        with self.assertRaises(ValueError):
            Souhait(categorie="x", etat_min="usage")

    def test_3_alternatives_et_modes_de_recherche(self):
        def souhait(mode, alternatives=(("bricolage", "perceuses"),)):
            return Souhait(categorie="velo", alternatives=alternatives, mode=mode)

        perceuse = {"sous_categorie": "perceuses"}
        self.assertTrue(echange_possible(marche_paire(souhait("flexible"), **perceuse)))
        self.assertFalse(echange_possible(marche_paire(souhait("precise"), **perceuse)))
        self.assertFalse(echange_possible(marche_paire(souhait("flexible"), sous_categorie="scies")))
        # Ouverte : toute la catégorie d'intérêt, quelle que soit la sous-catégorie.
        self.assertTrue(echange_possible(marche_paire(souhait("ouverte"), sous_categorie="scies")))
        # Les critères du souhait (catégorie vélo) ne s'appliquent pas à une alternative d'une autre catégorie.
        avec_critere = Souhait(categorie="velo", criteres=(("taille", "M"),), alternatives=(("bricolage", None),))
        self.assertTrue(echange_possible(marche_paire(avec_critere)))
        with self.assertRaises(ValueError):
            Souhait(categorie="velo", mode="au hasard")

    def test_3_5_objet_vise_puis_preferences(self):
        """À nombre d'objets égal, l'objet visé passe avant l'alternative, et le critère préférentiel compte."""
        for moteur in ("heuristique",) + (("exact",) if solveur_exact.disponible() else ()):
            m = Marche()
            m.ajouter_utilisateur("A", [Souhait(categorie="velo", alternatives=(("trottinette", None),),
                                                preferences=(("couleur", "Rouge"),))])
            m.ajouter_utilisateur("B", [Souhait(categorie="poussette")])
            m.ajouter_objet("pA", "A", "poussette")
            m.ajouter_objet("t", "B", "trottinette")
            m.ajouter_objet("v_bleu", "B", "velo", caracteristiques={"couleur": "Bleu"})
            m.ajouter_objet("v_rouge", "B", "velo", caracteristiques={"couleur": "rouge"})
            sol = math_trade(m, moteur=moteur)
            self.assertEqual(sol.nb_objets_echanges, 2)
            self.assertIn("v_rouge", sol.boucles[0].objets, moteur)

    def test_4_boucles_de_quatre_et_cinq(self):
        m = Marche()
        noms = "ABCDE"
        for k, u in enumerate(noms):
            m.ajouter_utilisateur(u, [Souhait(categorie=f"c{(k + 1) % 5}")])
        for k, u in enumerate(noms):
            m.ajouter_objet(f"o{u}", u, f"c{k}")
        self.assertEqual(math_trade(m, longueur_max=4).nb_objets_echanges, 0)
        for moteur in ("heuristique",) + (("exact",) if solveur_exact.disponible() else ()):
            sol = math_trade(m, longueur_max=5, moteur=moteur)
            self.assertEqual([b.longueur for b in sol.boucles], [5], moteur)
            self.assertEqual(len(boucles_autour(m, "C", longueur_max=5)), 1)

    @AVEC_ORTOOLS
    def test_4_boucles_de_quatre_contre_force_brute(self):
        for seed in range(25):
            m = marche_aleatoire(seed, n_users=6, n_cat=5)
            sol = math_trade(m, longueur_max=4, moteur="exact")
            verifier_solution(self, m, sol, 4)
            self.assertEqual(sol.stats["longueur_max"], 4)
            self.assertEqual(sol.nb_objets_echanges, optimum_force_brute_borne(m, 4), f"seed {seed}")
            self.assertGreaterEqual(sol.nb_objets_echanges, math_trade(m, longueur_max=3).nb_objets_echanges)

    def test_4_longueur_reduite_si_incalculable(self):
        m = marche_aleatoire(3, n_users=12, n_cat=4)
        self.assertEqual(math_trade(m, longueur_max=5, budget_cycles=10).stats["longueur_max"], 3)
        self.assertEqual(math_trade(m, longueur_max=5).stats["longueur_max"], 5)

    def test_7_modes_d_echange(self):
        relais = Souhait(categorie="bricolage", modes={"point_relais"})
        self.assertFalse(echange_possible(marche_paire(relais, modes={"main_propre"})))
        self.assertTrue(echange_possible(marche_paire(relais, modes={"main_propre", "point_relais"})))
        self.assertTrue(echange_possible(marche_paire(relais)), "objet sans mode précisé : tous")

    def test_7_zones(self):
        souhait = Souhait(categorie="bricolage", zones={"Marseille 6e", "Marseille 5e"})
        m = marche_paire(souhait)
        m.utilisateurs["B"].zone = "Marseille 1er"
        self.assertFalse(echange_possible(m))
        m.utilisateurs["B"].zone = "Marseille 5e"
        self.assertTrue(echange_possible(m), "zone acceptée même si différente de celle de A")
        # Le lieu de l'objet passe avant la zone de son propriétaire.
        m = marche_paire(souhait, zone="Marseille 6e")
        m.utilisateurs["B"].zone = "Lyon"
        self.assertTrue(echange_possible(m))

    def test_8_objet_indisponible(self):
        self.assertFalse(echange_possible(marche_paire(Souhait(categorie="bricolage"), disponible=False)))

    def test_10_equite(self):
        """C et D veulent la poussette de A et ont ce qu'il veut : à égalité, la plus forte priorité passe."""
        for moteur in ("heuristique",) + (("exact",) if solveur_exact.disponible() else ()):
            for prioritaire in ("C", "D"):
                m = Marche()
                m.ajouter_utilisateur("A", [Souhait(categorie="velo")])
                m.ajouter_objet("pA", "A", "poussette")
                for u in "CD":
                    m.ajouter_utilisateur(u, [Souhait(categorie="poussette")], priorite=3 if u == prioritaire else 1)
                    m.ajouter_objet(f"v{u}", u, "velo")
                sol = math_trade(m, moteur=moteur)
                self.assertEqual(set(sol.participants), {"A", prioritaire}, moteur)


if __name__ == "__main__":
    unittest.main()


class TestAcceptationParMembre(unittest.TestCase):
    def test_taux_du_membre_sauf_acceptation_d_office(self):
        """Le taux de « oui » de chacun remplace la valeur commune, sauf pour un souhait « j'accepte d'office »."""
        m = Marche(p_acceptation=0.7, p_auto=0.95)
        m.ajouter_utilisateur("A", [Souhait("livres")], acceptation=0.4)
        m.ajouter_utilisateur("B", [Souhait("jeux", acceptation_auto=True)], acceptation=0.4)
        m.ajouter_utilisateur("C", [Souhait("jeux")])
        m.ajouter_objet("a", "A", "jeux")
        m.ajouter_objet("b", "B", "livres")
        (boucle,) = math_trade(m, longueur_max=2).boucles
        self.assertEqual({t.receveur: t.proba_acceptation for t in boucle.transferts}, {"A": 0.4, "B": 0.95})
        self.assertEqual(m.p_acceptation_de(m.utilisateurs["C"]), 0.7)
        with self.assertRaises(ValueError):
            m.ajouter_utilisateur("D", acceptation=0)

class TestObjetsAttendus(unittest.TestCase):
    @staticmethod
    def marche_quatre_contre_trois(p_acceptation):
        """L'objet d'Alice ferme soit une boucle de 4 (A, B, C, D), soit une boucle de 3 (A, E, F)."""
        m = Marche(p_acceptation=p_acceptation, meme_zone=False)
        m.ajouter_utilisateur("A", [Souhait("w"), Souhait("u")])
        for u, cat in (("B", "x"), ("C", "y"), ("D", "z"), ("E", "x"), ("F", "v")):
            m.ajouter_utilisateur(u, [Souhait(cat)])
        for o, u, cat in (("a", "A", "x"), ("b", "B", "y"), ("c", "C", "z"), ("d", "D", "w"),
                          ("e", "E", "v"), ("f", "F", "u")):
            m.ajouter_objet(o, u, cat)
        return m

    @AVEC_ORTOOLS
    def test_une_boucle_de_3_plus_sure_l_emporte(self):
        # 70 % : la boucle de 4 réussit à 24 % (0,96 objet attendu), celle de 3 à 34 % (1,03).
        m = self.marche_quatre_contre_trois(0.7)
        self.assertEqual(math_trade(m, longueur_max=4, moteur="exact").nb_objets_echanges, 4)
        sol = math_trade(m, longueur_max=4, moteur="exact", objectif="esperance")
        self.assertEqual((sol.nb_objets_echanges, sol.optimal, sol.stats["objectif"]), (3, True, "esperance"))
        # Membres qui disent souvent oui : la boucle de 4 rapporte plus (2,62 contre 2,19), elle reste.
        m = self.marche_quatre_contre_trois(0.9)
        self.assertEqual(math_trade(m, longueur_max=4, moteur="exact", objectif="esperance").nb_objets_echanges, 4)

    @AVEC_ORTOOLS
    def test_contre_force_brute(self):
        # Souhaits « j'accepte d'office » au hasard : une étape peut offrir deux chances différentes (table).
        for seed in range(25):
            m = marche_aleatoire(seed, n_users=6)
            for u in m.utilisateurs.values():  # taux de « oui » propres à certains membres
                u.acceptation = random.Random(seed * 7 + int(u.id[1:])).choice([None, 0.4, 0.9])
            for lm in (2, 3):
                sol = math_trade(m, longueur_max=lm, moteur="exact", objectif="esperance")
                verifier_solution(self, m, sol, lm)
                attendu = optimum_force_brute_borne(m, lm, lambda b: b.longueur * b.proba_reussite)
                self.assertAlmostEqual(sol.esperance_objets, attendu, delta=0.005 * attendu + 1e-9, msg=f"seed {seed}")
