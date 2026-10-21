"""Chance de dire oui : le taux de « oui » de chacun, lissé vers 70 %, remplace les 70 % communs."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from montroc_api import services
from montroc_api.db import engine


def _acceptations():
    with Session(engine) as session:
        marche = services.construire_marche(session)
        return {u.id: marche.p_acceptation_de(u) for u in marche.utilisateurs.values()}


def test_un_refus_baisse_la_chance_de_dire_oui(client, creer):
    (a, b, c), echange = creer.echange_abc()
    assert set(_acceptations().values()) == {0.7}  # personne n'a encore répondu
    client.post(f"/echanges/{echange['id']}/reponse", json={"accepte": True}, headers=b.headers)
    client.post(f"/echanges/{echange['id']}/reponse", json={"accepte": False}, headers=c.headers)
    with engine.begin() as conn:
        lignes = conn.execute(text("SELECT pseudo, reponses_oui, reponses_non FROM utilisateurs ORDER BY id")).all()
    # Alice a proposé la boucle (accord d'office) : ce n'est pas une réponse.
    assert [tuple(r) for r in lignes] == [("alice", 0, 0), ("bruno", 1, 0), ("chloe", 0, 1)]
    taux = _acceptations()
    assert taux[str(a.id)] == 0.7
    assert taux[str(b.id)] == 8 / 11
    assert taux[str(c.id)] == 7 / 11


def test_les_accords_du_match_ne_comptent_pas(client, creer):
    (_, b, _), echange = creer.echange_abc()
    with engine.begin() as conn:
        conn.execute(text("UPDATE echanges SET par_match = true WHERE id = :e"), {"e": echange["id"]})
    client.post(f"/echanges/{echange['id']}/reponse", json={"accepte": False}, headers=b.headers)
    assert _acceptations()[str(b.id)] == 0.7
