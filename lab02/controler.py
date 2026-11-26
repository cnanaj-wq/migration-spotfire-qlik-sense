"""Étape 4 : contrôle en SQL chaque valeur que Qlik Sense affichera.

Usage : python lab02/controler.py <identifiant de l'application Qlik>
Pour chaque mesure convertie, deux calculs indépendants de la même expression Spotfire :
- la requête SQL, exécutée sur les fichiers de data/ (base SQLite en mémoire) ;
- l'expression Qlik, exécutée dans l'application par l'outil en ligne de commande « qlik ».
Les deux résultats sont comparés point par point : une valeur par mesure et par valeur de
dimension (par BU, par mois, par agence...). Résultat : sorties/controle.md
"""

import csv
import json
import pathlib
import sqlite3
import subprocess
import sys

DOSSIER = pathlib.Path(__file__).parent
RACINE = DOSSIER.parent
SORTIES = DOSSIER / "sorties"
TOLERANCE = 0.005


def nombre(texte):
    for sorte in (int, float):
        try:
            return sorte(texte)
        except ValueError:
            pass
    return texte


def ouvrir_sources():
    """Charge chaque fichier de data/ dans une table SQLite du même nom."""
    base = sqlite3.connect(":memory:")
    for fichier in sorted((RACINE / "data").glob("*.csv")):
        with fichier.open(encoding="utf-8-sig", newline="") as flux:
            lignes = list(csv.reader(flux))
        colonnes = ", ".join('"%s"' % c for c in lignes[0])
        base.execute('CREATE TABLE "%s" (%s)' % (fichier.stem, colonnes))
        base.executemany(
            'INSERT INTO "%s" VALUES (%s)'
            % (fichier.stem, ", ".join("?" * len(lignes[0]))),
            [[nombre(v) for v in ligne] for ligne in lignes[1:]],
        )
    return base


def cle(valeurs):
    return tuple(
        str(int(v)) if isinstance(v, float) and v == int(v) else str(v) for v in valeurs
    )


def evaluer(application, expressions, dimensions):
    """Les valeurs de plusieurs expressions Qlik, par combinaison de dimensions."""
    commande = ["qlik", "app", "eval", *expressions]
    if dimensions:
        commande += ["by", *dimensions]
    commande += ["--rows", "5000", "--json", "--app", application]
    sortie = subprocess.run(
        commande, capture_output=True, text=True, encoding="utf-8", timeout=180
    )
    if sortie.returncode != 0:
        raise RuntimeError((sortie.stderr or sortie.stdout).strip()[:300])
    resultats = [{} for _ in expressions]
    for page in json.loads(sortie.stdout):
        for ligne in page["qMatrix"]:
            axes, valeurs = ligne[: len(dimensions)], ligne[len(dimensions) :]
            if any(a.get("qText", "-") == "-" for a in axes):
                continue  # lignes d'une autre source, sans valeur pour cet axe
            for rang, cellule in enumerate(valeurs):
                valeur = cellule.get("qNum")
                if not isinstance(valeur, (int, float)):
                    valeur = nombre(
                        cellule.get("qText", "-").replace(",", ".").replace(" ", "")
                    )
                    valeur = None if isinstance(valeur, str) else float(valeur)
                resultats[rang][cle(a["qText"] for a in axes)] = valeur
    return resultats


def comparer(attendus, obtenus):
    """Nombre de points contrôlés, et liste des écarts."""
    ecarts = []
    for point, attendu in attendus.items():
        obtenu = obtenus.get(point)
        if attendu is None and not obtenu:
            continue
        if attendu is None or obtenu is None or abs(attendu - obtenu) > TOLERANCE:
            ecarts.append((point, attendu, obtenu))
    return len(attendus), ecarts


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    application = sys.argv[1]
    base = ouvrir_sources()
    pages = json.loads((SORTIES / "conversions.json").read_text(encoding="utf-8"))
    texte = ["# Contrôle SQL des conversions", ""]
    texte += [
        "| Page | Visuel | Mesures | Points contrôlés | Conformes |",
        "|---|---|---|---|---|",
    ]
    total_mesures = total_points = total_conformes = mesures_conformes = 0
    detail = []
    for page in pages:
        for visuel in page["visuels"]:
            mesures = [m for m in visuel["mesures"] if "qlik" in m]
            if not mesures:
                continue
            dimensions = [d["qlik"] for d in visuel["dimensions"]]
            obtenus = evaluer(application, [m["qlik"] for m in mesures], dimensions)
            points = conformes = 0
            for mesure, valeurs in zip(mesures, obtenus):
                lignes = base.execute(mesure["sql"]).fetchall()
                attendus = {cle(ligne[:-1]): ligne[-1] for ligne in lignes}
                nombre_points, ecarts = comparer(attendus, valeurs)
                points += nombre_points
                conformes += nombre_points - len(ecarts)
                mesures_conformes += not ecarts
                for point, attendu, obtenu in ecarts[:5]:
                    detail.append(
                        "- %s / %s %s : SQL %s, Qlik %s"
                        % (
                            visuel["titre"],
                            mesure.get("libelle") or mesure["axe"],
                            point,
                            attendu,
                            obtenu,
                        )
                    )
            texte.append(
                "| %s | %s | %d | %d | %d |"
                % (page["titre"], visuel["titre"], len(mesures), points, conformes)
            )
            total_mesures += len(mesures)
            total_points += points
            total_conformes += conformes
    bilan = (
        "%d mesures, %d points contrôlés, %d conformes (tolérance %s). Mesures sans aucun écart : %d."
        % (
            total_mesures,
            total_points,
            total_conformes,
            TOLERANCE,
            mesures_conformes,
        )
    )
    texte += ["", bilan, ""]
    if detail:
        texte += ["## Écarts", ""] + detail + [""]
    (SORTIES / "controle.md").write_text("\n".join(texte), encoding="utf-8")
    print("\n".join(texte[-(len(detail) + 6) :]) if detail else bilan)


if __name__ == "__main__":
    main()
