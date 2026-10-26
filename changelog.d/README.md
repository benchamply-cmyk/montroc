# Lignes du journal en attente

Chaque PR ajoute ici **un fichier d'une ligne** qui dit, pour un membre ou pour Ben, ce qui change. Elle ne touche pas à `CHANGELOG.md` : deux PR ouvertes en même temps n'entrent plus en conflit.

- Nom du fichier : le sujet de la branche, `feature/match-a-trois` → `changelog.d/match-a-trois.md`.
- Contenu : une ligne qui commence par `- `, avec le numéro de PR s'il est connu.

```
- Le Match : boucles à trois proposées depuis l'onglet Match (#51).
```

Au moment de sortir une version, `python3 scripts/version.py 0.6.0` (ou le workflow **Versions** lancé à la main avec le numéro) rassemble ces lignes dans `CHANGELOG.md`, change `VERSION` dans `web/site.js` et supprime les fichiers. Ce README reste.
