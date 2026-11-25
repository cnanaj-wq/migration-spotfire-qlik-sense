"""Contrôle de cohérence du jeu de données : les tables doivent se recouper.

Quatre rapprochements, sur l'exercice 2026 (mois clôturés) :
1. le chiffre d'affaires du compte de résultat = la somme des ventes ;
2. le chiffre d'affaires par agence = la somme des ventes ;
3. les effets volume, prix et coûts d'achat = marge réelle - marge budget ;
4. la balance âgée = les créances clients du dernier mois clôturé.

Usage : python controles/verifier_donnees.py
Code de retour 0 si tout concorde, 1 sinon.
"""

import csv
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
EXERCICE = "2026"
TOLERANCE = 1.0  # euro : les fichiers sont arrondis au centime


def lire(nom):
    with open(DATA / (nom + ".csv"), encoding="utf-8-sig", newline="") as fichier:
        return list(csv.DictReader(fichier))


def somme(lignes, colonne):
    return sum(float(ligne[colonne] or 0) for ligne in lignes)


def clos(lignes):
    """Lignes réelles de l'exercice contrôlé (les prévisions sont exclues)."""
    return [
        ligne
        for ligne in lignes
        if ligne["Exercice"] == EXERCICE and ligne.get("Statut", "Réel") == "Réel"
    ]


def rapprochements():
    ventes = clos(lire("ventes"))
    agences = clos(lire("ventes_agences"))
    resultat = clos(lire("compte_resultat"))
    ecarts = [e for e in lire("ecarts_marge") if e["Exercice"] == EXERCICE]
    bfr = [b for b in lire("bfr") if b["Exercice"] == EXERCICE]
    dernier_mois = max(int(b["Mois"]) for b in bfr)

    ca_ventes = somme(ventes, "CA Réel")
    yield (
        "CA du compte de résultat = somme des ventes",
        somme([r for r in resultat if r["Ordre"] == "1"], "Réel"),
        ca_ventes,
    )
    yield ("CA par agence = somme des ventes", somme(agences, "CA Réel"), ca_ventes)
    yield (
        "Effets de marge = marge réelle - marge budget",
        somme([e for e in ecarts if e["Type"] == "Effet"], "Montant"),
        somme(ventes, "Marge brute Réel") - somme(ventes, "Marge brute Budget"),
    )
    yield (
        "Balance âgée = créances clients du mois %d" % dernier_mois,
        somme(lire("creances_clients"), "Montant TTC"),
        somme([b for b in bfr if int(b["Mois"]) == dernier_mois], "Créances clients"),
    )


def main():
    echecs = 0
    for libelle, obtenu, attendu in rapprochements():
        concorde = abs(obtenu - attendu) <= TOLERANCE
        echecs += not concorde
        print(
            "%s  %-50s %16.2f | %16.2f"
            % ("OK  " if concorde else "ECART", libelle, obtenu, attendu)
        )
    print("%d rapprochement(s) en écart" % echecs if echecs else "Tout concorde")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
