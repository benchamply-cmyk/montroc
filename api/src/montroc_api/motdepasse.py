"""Mot de passe facultatif, en plus du lien magique : empreinte scrypt (bibliothèque standard), salée.

Format stocké : ``scrypt$n$r$p$sel$empreinte`` (sel et empreinte en base64). Le mot de passe lui-même
n'est jamais gardé.
"""

import base64
import hashlib
import hmac
import secrets

N, R, P = 2**14, 8, 1
# Comparée quand le compte n'existe pas ou n'a pas de mot de passe : la réponse prend le même temps.
_LEURRE = None


def _calculer(mot_de_passe: str, sel: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(mot_de_passe.encode(), salt=sel, n=n, r=r, p=p, maxmem=64 * 1024 * 1024, dklen=32)


def chiffrer(mot_de_passe: str) -> str:
    sel = secrets.token_bytes(16)
    b64 = base64.b64encode
    return f"scrypt${N}${R}${P}${b64(sel).decode()}${b64(_calculer(mot_de_passe, sel, N, R, P)).decode()}"


def verifier(mot_de_passe: str, stocke: str | None) -> bool:
    global _LEURRE
    if not stocke:
        _LEURRE = _LEURRE or chiffrer(secrets.token_urlsafe(12))
        stocke, valide = _LEURRE, False
    else:
        valide = True
    try:
        _, n, r, p, sel, attendu = stocke.split("$")
        calcule = _calculer(mot_de_passe, base64.b64decode(sel), int(n), int(r), int(p))
    except ValueError:
        return False
    return hmac.compare_digest(calcule, base64.b64decode(attendu)) and valide
