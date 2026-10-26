## Quoi

Avant :

Après :

## Comment

## Vérifications

- [ ] Base de la PR : `preprod` (seule la PR de livraison `preprod → prod` vise `prod`)
- [ ] Branche nommée `type/sujet-vX.Y` (`feature/`, `fix/`, `docs/`, `chore/`, `db/`, `mobile/`), ex. `feature/photos-v5.2000` (`python3 scripts/version.py branche feature photos`)
- [ ] Une ligne dans `changelog.d/<sujet>.md` (pas dans `CHANGELOG.md`)
- [ ] `make tests` passe en local
- [ ] Si `models.py` a changé : migration Alembic ajoutée (`make migration m="..."`)
- [ ] Documentation `docs/` mise à jour si le fonctionnement change
