# Sécurité par région : chaque profil ne voit que les régions que lui donne data/securite.csv
# (la même table servira au Section Access de Qlik Sense).
# Exécuté par construire_tout.py, une fois les cinq onglets créés.
#
# Portée : c'est une restriction d'affichage, pas un contrôle d'accès. Dans un document
# Spotfire ouvert sur un poste, les données sont embarquées et l'auteur peut retirer la
# restriction. Un vrai cloisonnement demande Spotfire Server, qui filtre les lignes à la
# source selon l'utilisateur connecté.
#
# Pour voir le tableau de bord comme un autre profil : changer UTILISATEUR, reconstruire.
UTILISATEUR = "daf@orvane.example"
FICHIER_SECURITE = DOSSIER + "../../data/securite.csv"
COLONNE = "Région"


def regions_autorisees(utilisateur):
    """Liste des régions du profil ; None s'il voit tout ; [] s'il est inconnu."""
    lignes = io.open(FICHIER_SECURITE, encoding="utf-8").read().splitlines()
    regions = []
    for ligne in lignes[1:]:
        champs = ligne.split(",")
        if len(champs) >= 5 and champs[1] == utilisateur:
            regions.append(champs[4])
    return None if "*" in regions else regions


def condition(regions):
    # un profil absent de la table ne voit aucune ligne, comme dans un Section Access
    if not regions:
        return "1 = 0"
    return " or ".join('[%s] = "%s"' % (COLONNE, region) for region in regions)


def blocs_a_securiser(visuel):
    """Comme blocs_de_donnees, carte comprise : elle aussi montre des régions."""
    from Spotfire.Dxp.Application.Visuals import Visualization
    from Spotfire.Dxp.Application.Visuals.Maps import MapChart

    if visuel.As[MapChart]() is not None:
        return [visuel.As[Visualization]().Data]
    return blocs_de_donnees(visuel)


def restreindre(donnees, clause):
    # les tables sans région (compte de résultat, BFR, trésorerie) restent entières
    if not donnees.DataTableReference.Columns.Contains(COLONNE):
        return
    actuelle = donnees.WhereClauseExpression
    donnees.WhereClauseExpression = (
        "(%s) and (%s)" % (actuelle, clause) if actuelle else clause
    )


REGIONS = regions_autorisees(UTILISATEUR)
if REGIONS is not None:
    for page in Document.Pages:
        for visuel in page.Visuals:
            essayer(
                "sécurité " + visuel.Title,
                lambda v=visuel: [
                    restreindre(d, condition(REGIONS)) for d in blocs_a_securiser(v)
                ],
            )

journal_securite = io.open(DOSSIER + "_securite.log", "w", encoding="utf-8")
journal_securite.write(
    "%s : %s"
    % (
        UTILISATEUR,
        "toutes les régions"
        if REGIONS is None
        else (", ".join(REGIONS) or "aucune région (profil inconnu)"),
    )
)
journal_securite.close()
