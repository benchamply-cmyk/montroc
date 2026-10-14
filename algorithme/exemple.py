"""Exemple : un petit groupe de parents à Marseille qui échangent des affaires d'enfants.

Lancer : python3 exemple.py
"""
from troc_echanges import Marche, Souhait, boucles_autour, math_trade, remplacants, replanifier

m = Marche(p_acceptation=0.7, p_auto=0.95)

m.ajouter_utilisateur("Alice", [Souhait(categorie="siege-auto-1-4", acceptation_auto=True)], zone="Marseille")
m.ajouter_utilisateur("Bruno", [Souhait(categorie="velo-enfant"), Souhait(categorie="livres", rang=2)], zone="Marseille")
m.ajouter_utilisateur("Chloé", [Souhait(categorie="poussette")], zone="Marseille")
m.ajouter_utilisateur("David", [Souhait(categorie="lit-parapluie"), Souhait(categorie="poussette", rang=2)], zone="Marseille")
m.ajouter_utilisateur("Emma", [Souhait(categorie="vetements-2ans")], zone="Marseille")
m.ajouter_utilisateur("Farid", [Souhait(categorie="jeux-societe")], zone="Marseille")
m.ajouter_utilisateur("Léa", [Souhait(categorie="poussette")], zone="Marseille")
# Quatre voisins qui ne peuvent échanger qu'en boucle de 4
m.ajouter_utilisateur("Hugo", [Souhait(categorie="puzzle")], zone="Marseille")
m.ajouter_utilisateur("Inès", [Souhait(categorie="doudou")], zone="Marseille")
m.ajouter_utilisateur("Jules", [Souhait(categorie="tricycle")], zone="Marseille")
m.ajouter_utilisateur("Karim", [Souhait(categorie="trottinette")], zone="Marseille")
m.ajouter_utilisateur("Gaëlle", [Souhait(categorie="poussette")], zone="Marseille")  # autre ville

m.ajouter_objet("p1", "Alice", "poussette", "Poussette Yoyo")
m.ajouter_objet("s1", "Bruno", "siege-auto-1-4", "Siège auto 1-4 ans")
m.ajouter_objet("v1", "Chloé", "velo-enfant", "Vélo 14 pouces")
m.ajouter_objet("l1", "Chloé", "lit-parapluie", "Lit parapluie")
m.ajouter_objet("j1", "David", "vetements-2ans", "Lot vêtements 2 ans")
m.ajouter_objet("b1", "Emma", "livres", "10 albums jeunesse")
m.ajouter_objet("g1", "Emma", "jeux-societe", "Dobble")
m.ajouter_objet("x1", "Farid", "lit-parapluie", "Lit parapluie Ikea")
m.ajouter_objet("s2", "Léa", "siege-auto-1-4", "Siège auto Römer")
m.ajouter_objet("t1", "Hugo", "trottinette", "Trottinette 3 roues")
m.ajouter_objet("z1", "Inès", "puzzle", "Puzzle 100 pièces")
m.ajouter_objet("d1", "Jules", "doudou", "Doudou lapin neuf")
m.ajouter_objet("r1", "Karim", "tricycle", "Tricycle")
m.ajouter_objet("p2", "Gaëlle", "siege-auto-1-4", "Siège auto (Marseille)")

print("== 1. Version simple : les échanges possibles pour Alice ==")
for b in boucles_autour(m, "Alice"):
    print(" -", b.decrire())

print("\n== 2. Math trade, boucles limitées à 3 (lancement) ==")
sol = math_trade(m, longueur_max=3)
print(sol.resume())
for b in sol.boucles:
    print(" -", b.decrire())

print("\n== 3. Même chose, en maximisant les échanges *attendus* (refus pris en compte) ==")
sol_e = math_trade(m, longueur_max=3, objectif="esperance")
print(sol_e.resume())

print("\n== 4. TradeMaximizer pur (longueur illimitée), pour comparaison ==")
sol_u = math_trade(m, longueur_max=None)
print(sol_u.resume())
for b in sol_u.boucles:
    print(" -", b.decrire())

boucle = next(b for b in sol.boucles if "Bruno" in b.participants)
autres = [b for b in sol.boucles if b is not boucle]  # boucles déjà acceptées, on n'y touche pas
print("\n== 5. Bruno refuse : on cherche des remplaçants pour les autres participants ==")
for p, options in remplacants(m, boucle, "Bruno", boucles_maintenues=autres).items():
    print(f" {p} :", options[0].decrire() if options else "rien pour l'instant")
nouvelle = replanifier(m, autres, [(boucle, "Bruno")])
print(" Nouvelle passe de math trade :", nouvelle.resume())
for b in nouvelle.boucles:
    print(" -", b.decrire())
