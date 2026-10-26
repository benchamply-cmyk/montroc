"""Réglages lus dans les variables d'environnement (ou un fichier ``.env``)."""

from functools import lru_cache
from typing import Literal
from urllib.parse import unquote, urlsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # postgresql+psycopg://utilisateur:mot_de_passe@hote:5432/base
    database_url: str = "postgresql+psycopg://montroc:montroc@localhost:5432/montroc"
    # Origines autorisées à appeler l'API depuis un navigateur, séparées par des virgules.
    cors_origins: str = "http://localhost:8000,https://troctroc.fr,https://www.troctroc.fr"
    # Aperçus Netlify des pull requests (deploy-preview-29--troctroc.netlify.app, *.champly.fr) : sans eux,
    # la connexion échoue sur l'aperçu, le navigateur bloquant la réponse de l'API.
    cors_regex: str = r"https://([a-z0-9-]+--)?troctroc\.netlify\.app|https://[a-z0-9-]+\.champly\.fr"
    environnement: str = "local"
    # Adresse du site, pour les liens dans les e-mails (lien magique, « une boucle vous attend »…).
    site_url: str = "https://troctroc.fr"

    # E-mails sortants. Render gratuit bloque les ports SMTP : en production, on passe par l'API HTTPS
    # de Brevo (BREVO_API_KEY). Le SMTP (OVH) reste possible sur une offre Render payante ou en local.
    # Sans l'un ni l'autre, les e-mails sont écrits dans le journal : pratique en local et dans les tests.
    brevo_api_key: str = ""
    smtp_hote: str = "ssl0.ovh.net"
    smtp_port: int = 465
    smtp_utilisateur: str = ""
    smtp_mot_de_passe: str = ""
    email_expediteur: str = "TrocTroc <bonjour@troctroc.fr>"
    # Pré-production : tous les e-mails partent à cette adresse (le vrai destinataire en tête du sujet),
    # pour ne jamais écrire aux membres depuis une copie de la base. Vide en production.
    courriels_vers: str = ""
    # Pré-production : false coupe les SMS (ils sont seulement écrits dans le journal).
    sms_actifs: bool = True
    # Nom affiché comme expéditeur des SMS (Brevo, 11 caractères au plus, lettres et chiffres).
    sms_expediteur: str = "TrocTroc"

    # Photos : la variable CLOUDINARY_URL du tableau de bord Cloudinary (cloudinary://clé:secret@nom).
    cloudinary_url: str = ""

    # E-mails des comptes qui ont accès à la modération, séparés par des virgules.
    moderateurs: str = ""
    # Secret partagé avec la tâche planifiée GitHub Actions qui appelle /taches/… (rappels, math trade).
    taches_secret: str = ""
    # Les boucles se décident au Grand Troc du dimanche. Mettre à true pour laisser aussi chacun proposer
    # tout de suite une boucle parmi ses suggestions (POST /echanges), comme avant le Grand Troc.
    echanges_a_la_demande: bool = False
    # Ce que le math trade du Grand Troc maximise : « esperance », les objets échangés *attendus* (chaque boucle
    # compte pour sa longueur × la chance que tous acceptent : une boucle de 4 incertaine cède la place à une boucle
    # de 3 plus sûre qui lui dispute un objet) ; « echanges », le plus d'objets proposés, comme avant.
    objectif_grand_troc: Literal["echanges", "esperance"] = "esperance"
    # Nombre maximum de boucles (donc d'objets reçus) par personne au même Grand Troc, repêchage compris :
    # un gros déposant ne prend pas tout le dimanche pendant que d'autres n'ont rien. 0 : pas de plafond.
    plafond_echanges_grand_troc: int = Field(default=3, ge=0, le=20)
    # Combien d'objets un membre peut recevoir au même Grand Troc grâce à ses « J'aime » du Match : ils comptent
    # ensemble comme un seul souhait, classé après ses souhaits déclarés.
    coups_de_coeur_par_grand_troc: int = Field(default=1, ge=1, le=5)
    # Lieu de dépôt affiché aux participants d'un échange accepté (adresse, horaires) : celui par défaut.
    point_de_depot: str = ""
    # Un lieu de dépôt par ville ou quartier, séparés par des « ; » : « zone = lieu ». Un échange prend celui de la
    # zone de la plupart de ses participants (« Marseille » vaut aussi pour « Marseille 6e »), sinon POINT_DE_DEPOT.
    # Ex. : « Marseille 6e = Ressourcerie, rue des Trois-Rois, 13006 Marseille ; Aix-en-Provence = Café, … ».
    points_de_depot: str = ""
    # Lieux publics conseillés pour la remise en main propre, même format : « zone = lieu ; … ».
    # Ex. : « Marseille 6e = Place Jean-Jaurès, devant la médiathèque ; Aix-en-Provence = Cours Mirabeau ».
    lieux_de_rencontre: str = ""

    # Troc Premium (voir premium.py). Liens de paiement Stripe (Payment Links) par formule et durée, séparés par
    # des « ; » : « plus_mois = https://buy.stripe.com/… ; plus_an = … ; pass = … ». Sans lien, la formule
    # s'affiche sans bouton de paiement (essai gratuit seulement).
    stripe_liens: str = ""
    # Secret de signature du webhook Stripe (whsec_…), pour /premium/stripe.
    stripe_webhook_secret: str = ""
    # Portail client Stripe : changer de carte ou résilier en trois clics.
    stripe_portail: str = ""
    # Encart publicitaire montré aux membres sans formule « sans publicité » : « texte | lien ». Vide : aucun.
    encart_publicite: str = ""
    # Durée de l'essai gratuit de Premium Plus, une fois par compte (0 : pas d'essai).
    jours_essai_premium: int = Field(default=30, ge=0, le=90)

    @property
    def database_url_normalisee(self) -> str:
        """Neon, Render ou Heroku donnent souvent ``postgres://`` : SQLAlchemy veut le pilote explicite."""
        url = self.database_url
        for prefixe in ("postgres://", "postgresql://"):
            if url.startswith(prefixe):
                return "postgresql+psycopg://" + url[len(prefixe) :]
        return url

    @property
    def smtp_configure(self) -> bool:
        return bool(self.smtp_utilisateur and self.smtp_mot_de_passe)

    @property
    def envoi_configure(self) -> bool:
        return bool(self.brevo_api_key) or self.smtp_configure

    @property
    def cloudinary(self) -> tuple[str, str, str] | None:
        """(nom du cloud, clé, secret) lus dans CLOUDINARY_URL, ou None si les photos ne sont pas configurées."""
        url = urlsplit(self.cloudinary_url)
        if url.scheme != "cloudinary" or not (url.hostname and url.username and url.password):
            return None
        return url.hostname, unquote(url.username), unquote(url.password)

    @property
    def liste_moderateurs(self) -> set[str]:
        return {e.strip().lower() for e in self.moderateurs.split(",") if e.strip()}

    @property
    def liste_points_de_depot(self) -> list[tuple[str, str]]:
        """(zone en minuscules, lieu) pour chaque entrée de POINTS_DE_DEPOT, dans l'ordre."""
        return _liste_par_zone(self.points_de_depot)

    @property
    def liste_lieux_de_rencontre(self) -> list[tuple[str, str]]:
        return _liste_par_zone(self.lieux_de_rencontre)

    @property
    def liens_stripe(self) -> dict[str, str]:
        """{formule_duree : lien de paiement} lus dans STRIPE_LIENS."""
        liens = {}
        for entree in self.stripe_liens.split(";"):
            cle, egal, url = entree.partition("=")
            if egal and cle.strip() and url.strip().startswith("https://"):
                liens[cle.strip()] = url.strip()
        return liens

    @property
    def liste_cors(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def _liste_par_zone(valeur: str) -> list[tuple[str, str]]:
    """« zone = lieu ; … » → [(zone en minuscules, lieu)], dans l'ordre."""
    lieux = []
    for entree in valeur.split(";"):
        zone, egal, lieu = entree.partition("=")
        if egal and zone.strip() and lieu.strip():
            lieux.append((" ".join(zone.split()).lower(), lieu.strip()))
    return lieux


@lru_cache
def get_settings() -> Settings:
    return Settings()
