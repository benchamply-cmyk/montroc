"""Prépare une version : rassemble les fragments de changelog.d/ dans CHANGELOG.md et change VERSION.

    python3 scripts/version.py 0.6.0 "Le Match à trois"   # titre facultatif
    python3 scripts/version.py --apercu                    # montre les lignes en attente, sans rien changer

Chaque PR ajoute un fichier d'une ligne dans changelog.d/ au lieu d'éditer CHANGELOG.md : deux PR ouvertes en
même temps ne se gênent plus. Ce script, lancé dans la PR de version (à la main ou par le workflow Versions) :
1. ajoute les lignes des fragments sous « À venir » et renomme cette section en « [0.6.0] – date » ;
2. remet une section « À venir » vide en tête ;
3. met à jour les liens de comparaison en bas du journal ;
4. change VERSION en haut de web/site.js (affichée dans le pied de page) ;
5. supprime les fragments.
"""

import re
import sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
JOURNAL = RACINE / "CHANGELOG.md"
SITE = RACINE / "web" / "site.js"
FRAGMENTS = RACINE / "changelog.d"
DEPOT = "https://github.com/benchamply-cmyk/montroc"
INTRO = (
    "Chaque PR ajoute sa ligne dans un fichier de [changelog.d/](changelog.d/) ; "
    "les lignes arrivent ici quand on prépare la version (`python3 scripts/version.py X.Y.Z`)."
)
FORMAT_VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def fragments() -> list[Path]:
    return sorted(p for p in FRAGMENTS.glob("*.md") if p.name != "README.md")


def lignes_des_fragments() -> list[str]:
    lignes = []
    for p in fragments():
        for ligne in p.read_text(encoding="utf-8").splitlines():
            ligne = ligne.strip()
            if ligne:
                lignes.append(ligne if ligne.startswith("- ") else "- " + ligne)
    return lignes


def version_actuelle() -> str:
    trouve = re.search(r"const VERSION='([0-9.]+)'", SITE.read_text(encoding="utf-8"))
    if not trouve:
        sys.exit("VERSION introuvable en haut de web/site.js")
    return trouve.group(1)


def preparer(version: str, titre: str | None) -> None:
    if not FORMAT_VERSION.match(version):
        sys.exit(f"Version invalide : {version} (attendu : 0.6.0)")
    precedente = version_actuelle()
    journal = JOURNAL.read_text(encoding="utf-8")
    debut = journal.index("## [À venir]")
    fin = journal.index("\n## [", debut + 1) + 1
    anciennes = [ligne for ligne in journal[debut:fin].splitlines() if ligne.startswith("- ")]
    lignes = anciennes + lignes_des_fragments()
    if not lignes:
        sys.exit("Rien à publier : aucune ligne sous « À venir » ni dans changelog.d/.")

    entete = f"## [{version}] – {date.today().isoformat()}" + (f" · {titre}" if titre else "")
    section = f"## [À venir]\n\n{INTRO}\n\n{entete}\n\n" + "\n".join(lignes) + "\n\n"
    journal = journal[:debut] + section + journal[fin:]

    # Liens en bas du journal : « À venir » compare la dernière version à preprod.
    journal = re.sub(r"^\[À venir\]: .*$", f"[À venir]: {DEPOT}/compare/v{version}...preprod", journal, flags=re.M)
    lien = f"[{version}]: {DEPOT}/compare/v{precedente}...v{version}"
    journal = re.sub(r"^(\[À venir\]: .*)$", lambda t: t.group(1) + "\n" + lien, journal, count=1, flags=re.M)
    JOURNAL.write_text(journal, encoding="utf-8")

    SITE.write_text(
        SITE.read_text(encoding="utf-8").replace(f"const VERSION='{precedente}'", f"const VERSION='{version}'"),
        encoding="utf-8",
    )
    for p in fragments():
        p.unlink()
    print(f"Version {version} prête ({len(lignes)} lignes, précédente : {precedente}).")


if __name__ == "__main__":
    if sys.argv[1:] == ["--apercu"]:
        print("\n".join(lignes_des_fragments()) or "Aucun fragment en attente.")
    elif len(sys.argv) in (2, 3):
        preparer(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
    else:
        sys.exit(__doc__)
