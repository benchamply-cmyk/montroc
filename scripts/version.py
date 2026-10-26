"""Numérotation des versions TrocTroc (règle de Ben du 26/10/2026, voir docs/05-git-et-branches.md).

- prod : V5.100, puis +100 à chaque livraison preprod → prod (V5.200, V5.300…), étiquette Git « V5.200 » ;
- preprod : V5.1000, puis +1000 à chaque PR fusionnée dans preprod (V5.2000, V5.3000…), étiquette « preprod-V5.2000 » ;
- le chiffre de gauche (V6.100, puis V6.1000 en preprod) ne monte que quand Ben le décide (livraison --majeure).

Les étiquettes Git font foi : elles sont posées par le workflow Versions, jamais à la main.

    python3 scripts/version.py suivante                   # prochaine version preprod : 5.2000
    python3 scripts/version.py branche feature photos     # nom de branche à créer : feature/photos-v5.2000
    python3 scripts/version.py livraisons-possibles       # versions de prod acceptées à la livraison : 5.200 6.100
    python3 scripts/version.py livraison [--majeure] ["Titre"]   # prépare la livraison vers prod
    python3 scripts/version.py --apercu                   # lignes de changelog.d/ en attente

« livraison » (lancé par Actions > Versions > Run workflow) :
1. calcule la prochaine version de prod (dernière étiquette V… + 100, ou V(n+1).100 avec --majeure) ;
2. range les lignes de changelog.d/ (et celles restées sous « À venir ») dans « [V5.200] – date » de CHANGELOG.md ;
3. met à jour les liens de comparaison en bas du journal et VERSION en haut de web/site.js (pied de page) ;
4. supprime les fragments.
"""

import re
import subprocess
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
    "les lignes arrivent ici à la préparation de la livraison (`python3 scripts/version.py livraison`)."
)
PAS_PROD, PAS_PREPROD = 100, 1000
# Versions du 26/10/2026, quand aucune étiquette n'existe encore.
DEPART_PROD, DEPART_PREPROD = (5, 100), (5, 1000)
ETIQUETTE = re.compile(r"^refs/tags/(preprod-)?V(\d+)\.(\d+)$")

Version = tuple[int, int]


def texte(v: Version) -> str:
    return f"{v[0]}.{v[1]}"


def etiquettes() -> tuple[list[Version], list[Version]]:
    """Versions de prod et de preprod d'après les étiquettes du dépôt GitHub."""
    sortie = subprocess.run(
        ["git", "ls-remote", "--tags", "origin"],
        cwd=RACINE,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    prod, preprod = [], []
    for ligne in sortie.splitlines():
        trouve = ETIQUETTE.match(ligne.split("\t")[-1])
        if trouve:
            (preprod if trouve.group(1) else prod).append(
                (int(trouve.group(2)), int(trouve.group(3)))
            )
    return sorted(prod), sorted(preprod)


def version_du_site() -> Version:
    trouve = re.search(
        r"const VERSION='(\d+)\.(\d+)'", SITE.read_text(encoding="utf-8")
    )
    if not trouve:
        sys.exit("VERSION (ex. '5.100') introuvable en haut de web/site.js")
    return int(trouve.group(1)), int(trouve.group(2))


def suivante_preprod() -> Version:
    prod, preprod = etiquettes()
    majeur, numero = preprod[-1] if preprod else DEPART_PREPROD
    # Quand prod passe à V6.100, la preprod repart à V6.1000.
    if prod and prod[-1][0] > majeur:
        return prod[-1][0], PAS_PREPROD
    return majeur, numero + PAS_PREPROD


def suivante_prod(majeure: bool) -> Version:
    prod, _ = etiquettes()
    majeur, numero = prod[-1] if prod else DEPART_PROD
    return (majeur + 1, PAS_PROD) if majeure else (majeur, numero + PAS_PROD)


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


def livraison(majeure: bool, titre: str | None) -> None:
    precedente, version = version_du_site(), suivante_prod(majeure)
    v, p = texte(version), texte(precedente)
    journal = JOURNAL.read_text(encoding="utf-8")
    debut = journal.index("## [À venir]")
    fin = journal.index("\n## [", debut + 1) + 1
    anciennes = [
        ligne for ligne in journal[debut:fin].splitlines() if ligne.startswith("- ")
    ]
    lignes = anciennes + lignes_des_fragments()
    if not lignes:
        sys.exit("Rien à livrer : aucune ligne sous « À venir » ni dans changelog.d/.")

    entete = f"## [V{v}] – {date.today().isoformat()}" + (
        f" · {titre}" if titre else ""
    )
    section = f"## [À venir]\n\n{INTRO}\n\n{entete}\n\n" + "\n".join(lignes) + "\n\n"
    journal = journal[:debut] + section + journal[fin:]

    # Liens en bas du journal : « À venir » compare la dernière version de prod à preprod.
    journal = re.sub(
        r"^\[À venir\]: .*$",
        f"[À venir]: {DEPOT}/compare/V{v}...preprod",
        journal,
        flags=re.M,
    )
    lien = f"[V{v}]: {DEPOT}/compare/V{p}...V{v}"
    journal = re.sub(
        r"^(\[À venir\]: .*)$",
        lambda t: t.group(1) + "\n" + lien,
        journal,
        count=1,
        flags=re.M,
    )
    JOURNAL.write_text(journal, encoding="utf-8")

    SITE.write_text(
        SITE.read_text(encoding="utf-8").replace(
            f"const VERSION='{p}'", f"const VERSION='{v}'"
        ),
        encoding="utf-8",
    )
    for f in fragments():
        f.unlink()
    print(v)
    print(
        f"Livraison V{v} prête ({len(lignes)} lignes, précédente : V{p}).",
        file=sys.stderr,
    )


if __name__ == "__main__":
    arguments = sys.argv[1:]
    if arguments == ["--apercu"]:
        print("\n".join(lignes_des_fragments()) or "Aucun fragment en attente.")
    elif arguments == ["suivante"]:
        print(texte(suivante_preprod()))
    elif arguments == ["livraisons-possibles"]:
        print(texte(suivante_prod(False)), texte(suivante_prod(True)))
    elif len(arguments) == 3 and arguments[0] == "branche":
        print(f"{arguments[1]}/{arguments[2]}-v{texte(suivante_preprod())}")
    elif arguments[:1] == ["livraison"]:
        majeure = "--majeure" in arguments
        reste = [a for a in arguments[1:] if a != "--majeure"]
        livraison(majeure, reste[0] if reste else None)
    else:
        sys.exit(__doc__)
