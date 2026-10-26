# Lignes du journal en attente

Chaque PR ajoute ici **un fichier d'une ligne** qui dit, pour un membre ou pour Ben, ce qui change. Elle ne touche pas à `CHANGELOG.md` : deux PR ouvertes en même temps n'entrent plus en conflit.

- Nom du fichier : le sujet de la branche, sans la version : `feature/match-a-trois-v5.2000` → `changelog.d/match-a-trois.md`.
- Contenu : une ligne qui commence par `- `, avec le numéro de PR s'il est connu.

```
- Le Match : boucles à trois proposées depuis l'onglet Match (#51).
```

Au moment de livrer la production, le workflow **Versions** lancé à la main (ou `python3 scripts/version.py livraison`) rassemble ces lignes dans `CHANGELOG.md` sous le numéro de livraison (`V5.200`), change `VERSION` dans `web/site.js` et supprime les fichiers. Ce README reste.
