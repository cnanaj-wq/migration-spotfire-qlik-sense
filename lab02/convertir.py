"""Étape 2 : convertit par règles chaque expression Spotfire en expression Qlik Sense.

Usage : python lab02/convertir.py
Part de sorties/inventaire.json. Pour chaque mesure, le script écrit deux traductions de la
même expression Spotfire : l'expression Qlik Sense (pour l'application) et une requête SQL sur les
fichiers sources (pour le contrôle). Les noms de champs Qlik Sense sont lus dans qlik/chargement.qvs.
Ce qu'aucune règle ne couvre n'est pas deviné : c'est listé « à arbitrer », avec la raison.
Résultat : sorties/conversions.json
"""

import collections
import json
import pathlib
import re

from spotfire import NonConvertible, lire_axe, lire_condition, lire_mesures

DOSSIER = pathlib.Path(__file__).parent
RACINE = DOSSIER.parent
SORTIES = DOSSIER / "sorties"
AGREGATS = {"sum": "Sum", "avg": "Avg", "max": "Max", "min": "Min", "count": "Count"}
AXES_MESURE = ("Y", "Color", "Comparative", "Measure", "Size")
INVERSE = {"<": ">", ">": "<", "<=": ">=", ">=": "<=", "=": "=", "<>": "<>"}


def lire_modele(script):
    """Ce que le script de chargement Qlik Sense fait de chaque colonne de chaque fichier source."""
    texte = "\n".join(
        re.sub(r"(^|\s)//.*$", "", ligne) for ligne in script.splitlines()
    )
    par_fichier, champs = collections.defaultdict(dict), set()
    for instruction in texte.split(";"):
        trouve = re.search(
            r"\bLOAD\b(?:\s+DISTINCT)?(.*?)\b(FROM|RESIDENT)\b(.*)", instruction, re.S
        )
        if not trouve:
            continue
        fichier = re.search(r"\)([\w-]+)\.csv", trouve.group(3))
        for element in re.split(r",(?![^()]*\))", trouve.group(1)):
            source, _, alias = re.sub(r"\s+", " ", element).strip().rpartition(" as ")
            source, alias = (source or alias).strip(), alias.strip().strip("[]")
            champs.add(alias)
            if fichier and "(" not in source and "'" not in source:
                par_fichier[fichier.group(1)][source.strip("[]")] = alias
    return par_fichier, champs


class Contexte:
    """Ce qu'il faut savoir du visuel pour traduire une de ses expressions."""

    def __init__(self, table, modele, regles, limitation, indicateur=False, axe_x=None):
        self.table, self.regles = table, regles
        self.par_fichier, self.champs = modele
        self.indicateur, self.axe_x = indicateur, axe_x
        self.colonnes = lire_entete(table)
        if table not in self.par_fichier:
            raise NonConvertible("table « %s » non chargée dans le modèle Qlik Sense" % table)
        self.limitation = lire_condition(limitation)
        self.conditions = conditions(self.limitation) if self.limitation else []
        self.appliquees = set()

    def source(self, colonne):
        """La colonne du fichier source derrière une colonne Spotfire (colonnes calculées)."""
        colonne = self.regles["colonnes_calculees"].get(colonne, colonne)
        if colonne not in self.colonnes:
            raise NonConvertible(
                "colonne « %s » absente du fichier %s.csv" % (colonne, self.table)
            )
        return colonne

    def champ(self, colonne):
        """Le champ Qlik Sense qui porte cette colonne."""
        source = self.source(colonne)
        champ = self.par_fichier[self.table].get(source)
        if champ is None and source in self.champs:
            champ = source  # champ construit par le script (calendrier)
        if champ is None:
            raise NonConvertible(
                "colonne « %s » sans champ dans le modèle Qlik Sense" % colonne
            )
        if champ != colonne:
            self.appliquees.add("champ renommé d'après le script de chargement")
        return champ if re.fullmatch(r"\w+", champ) else "[%s]" % champ


def lire_entete(table):
    fichier = RACINE / "data" / (table + ".csv")
    if not fichier.exists():
        return []
    return fichier.open(encoding="utf-8-sig").readline().strip().split(",")


def nu(arbre):
    while arbre[0] == "groupe":
        arbre = arbre[1]
    return arbre


def conditions(arbre):
    """Une suite de « colonne comparée à une valeur » reliées par and, ou rien."""
    arbre = nu(arbre)
    if arbre[0] == "bin" and arbre[1] == "and":
        return conditions(arbre[2]) + conditions(arbre[3])
    if arbre[0] == "bin" and arbre[1] in INVERSE:
        gauche, droite, signe = nu(arbre[2]), nu(arbre[3]), arbre[1]
        if droite[0] == "colonne":
            gauche, droite, signe = droite, gauche, INVERSE[signe]
        if (
            gauche[0] == "colonne"
            and droite[0] in ("nombre", "texte")
            and signe != "<>"
        ):
            return [(gauche[1], signe, droite)]
    raise NonConvertible("condition sans règle de conversion en ensemble")


def contient(arbre, sorte):
    if not isinstance(arbre, tuple):
        return (
            any(contient(e, sorte) for e in arbre) if isinstance(arbre, list) else False
        )
    return arbre[0] == sorte or any(contient(e, sorte) for e in arbre[1:])


def cumul_sur_axe(arbre, ctx):
    """Sum(...) OVER (AllPrevious([Axis.X])) dans une carte KPI : cumul lu à son dernier point."""
    portee = nu(arbre[2])
    if ctx.indicateur and portee == ("appel", "AllPrevious", [("colonne", "Axis.X")]):
        ctx.appliquees.add("cumul sur l'axe, lu au dernier point : total de la période")
        return arbre[1]
    raise NonConvertible("fenêtre OVER sans règle")


def filtre_de_si(appel, argument, ctx):
    """Sum(If(condition, colonne)) : la condition sort de l'agrégat."""
    argument = nu(argument)
    if argument[0] == "appel" and argument[1].lower() == "if":
        parties = argument[2]
        sans_sinon = len(parties) == 2 or (
            len(parties) == 3 and appel == "sum" and nu(parties[2]) == ("nombre", "0")
        )
        if sans_sinon:
            try:
                return conditions(parties[0]), parties[1]
            except NonConvertible:
                pass
    return [], argument


# --- vers Qlik Sense -------------------------------------------------------------------------


def element(signe, valeur):
    if valeur[0] == "texte":
        return "{'%s'}" % valeur[1].replace("'", "''")
    return "{%s}" % valeur[1] if signe == "=" else '{"%s%s"}' % (signe, valeur[1])


def ensemble(filtres, ctx, dernier_point):
    """Le filtre du visuel et celui du If, écrits en analyse d'ensembles."""
    par_champ = collections.OrderedDict()
    for colonne, signe, valeur in filtres:
        par_champ.setdefault(ctx.champ(colonne), []).append(element(signe, valeur))
    if dernier_point:
        champ = ctx.champ(ctx.axe_x)
        du_visuel = (
            collections.OrderedDict()
        )  # le dernier point se lit sur la limitation seule
        for colonne, signe, valeur in ctx.conditions:
            du_visuel.setdefault(ctx.champ(colonne), []).append(element(signe, valeur))
        limite = ", ".join("%s=%s" % (c, "*".join(e)) for c, e in du_visuel.items())
        dernier = "{$(=Max(%s%s))}" % ("{<%s>} " % limite if limite else "", champ)
        par_champ.setdefault(champ, []).append(dernier)
        ctx.appliquees.add("carte KPI sans cumul : valeur du dernier point de l'axe")
    if not par_champ:
        return ""
    return "{<%s>} " % ", ".join(
        "%s=%s" % (c, "*".join(e)) for c, e in par_champ.items()
    )


def qlik(arbre, ctx, dernier_point=False, dans_agregat=False):
    def suite(noeud, agregat=dans_agregat):
        return qlik(noeud, ctx, dernier_point, agregat)

    sorte = arbre[0]
    if sorte == "nombre":
        return arbre[1]
    if sorte == "texte":
        return "'%s'" % arbre[1].replace("'", "''")
    if sorte == "colonne":
        if not dans_agregat:
            raise NonConvertible("colonne « %s » hors agrégation" % arbre[1])
        return ctx.champ(arbre[1])
    if sorte == "groupe":
        return "(%s)" % suite(arbre[1])
    if sorte == "moins":
        return "-" + suite(arbre[1])
    if sorte == "bin":
        return "%s %s %s" % (suite(arbre[2]), arbre[1], suite(arbre[3]))
    if sorte == "fenetre":
        return suite(cumul_sur_axe(arbre, ctx))
    nom, arguments = arbre[1].lower(), arbre[2]
    if nom in AGREGATS:
        if dans_agregat or len(arguments) != 1:
            raise NonConvertible("agrégation imbriquée")
        du_si, argument = filtre_de_si(nom, arguments[0], ctx)
        if du_si:
            ctx.appliquees.add("condition du If sortie de l'agrégat, en ensemble")
        if ctx.conditions:
            ctx.appliquees.add("limitation du visuel écrite en ensemble")
        filtre = ensemble(ctx.conditions + du_si, ctx, dernier_point)
        return "%s(%s%s)" % (AGREGATS[nom], filtre, suite(argument, True))
    if nom == "real" and len(arguments) == 1:
        ctx.appliquees.add("Real() retiré : Qlik Sense n'a pas de type entier à convertir")
        return suite(arguments[0])
    if nom == "integer" and len(arguments) == 1:
        interne = nu(arguments[0])
        if interne[0] == "appel" and interne[1].lower() == "round":
            ctx.appliquees.add("Integer(Round(x)) devient Round(x) : déjà entier")
            return suite(interne)
        ctx.appliquees.add("Integer(x) devient Sign(x) * Floor(Fabs(x)) : troncature")
        valeur = suite(arguments[0])
        return "(Sign(%s) * Floor(Fabs(%s)))" % (valeur, valeur)
    if nom == "abs" and len(arguments) == 1:
        ctx.appliquees.add("Abs() devient Fabs()")
        return "Fabs(%s)" % suite(arguments[0])
    if nom == "round" and len(arguments) in (1, 2):
        decimales = int(nu(arguments[1])[1]) if len(arguments) == 2 else 0
        if decimales == 0:
            return "Round(%s)" % suite(arguments[0])
        ctx.appliquees.add("Round(x, n décimales) devient Round(x, pas)")
        return "Round(%s, %s)" % (
            suite(arguments[0]),
            "0." + "0" * (decimales - 1) + "1",
        )
    if nom == "if" and len(arguments) in (2, 3):
        return "If(%s)" % ", ".join(suite(a) for a in arguments)
    raise NonConvertible("fonction %s() sans règle" % arbre[1])


# --- vers SQL (contrôle sur les fichiers sources) --------------------------------------------


def sql(arbre, ctx):
    sorte = arbre[0]
    if sorte == "nombre":
        return arbre[1] if "." in arbre[1] else arbre[1] + ".0"
    if sorte == "texte":
        return "'%s'" % arbre[1].replace("'", "''")
    if sorte == "colonne":
        return '"%s"' % ctx.source(arbre[1])
    if sorte == "groupe":
        return "(%s)" % sql(arbre[1], ctx)
    if sorte == "moins":
        return "-" + sql(arbre[1], ctx)
    if sorte == "bin":
        return "%s %s %s" % (sql(arbre[2], ctx), arbre[1].upper(), sql(arbre[3], ctx))
    if sorte == "fenetre":
        return sql(cumul_sur_axe(arbre, ctx), ctx)
    nom, arguments = arbre[1].lower(), [sql(a, ctx) for a in arbre[2]]
    if nom in AGREGATS:
        return "%s(%s)" % (nom.upper(), arguments[0])
    if nom == "real":
        return "CAST(%s AS REAL)" % arguments[0]
    if nom == "integer":
        return "CAST(%s AS INTEGER)" % arguments[0]
    if nom == "abs":
        return "ABS(%s)" % arguments[0]
    if nom == "round":
        return "ROUND(%s)" % ", ".join(arguments)
    if nom == "if":
        sinon = " ELSE %s" % arguments[2] if len(arguments) == 3 else ""
        return "CASE WHEN %s THEN %s%s END" % (arguments[0], arguments[1], sinon)
    raise NonConvertible("fonction %s() sans règle" % arbre[1])


def requete(expression, dimensions, ctx, dernier_point):
    ou = sql(ctx.limitation, ctx) if ctx.limitation else ""
    filtres = [ou] if ou else []
    if dernier_point:
        axe = '"%s"' % ctx.source(ctx.axe_x)
        interne = 'SELECT MAX(%s) FROM "%s"%s' % (
            axe,
            ctx.table,
            " WHERE " + ou if ou else "",
        )
        filtres.append("%s = (%s)" % (axe, interne))
    colonnes = ['"%s"' % d["source"] for d in dimensions]
    texte = 'SELECT %s FROM "%s"' % (", ".join(colonnes + [expression]), ctx.table)
    if filtres:
        texte += " WHERE " + " AND ".join(filtres)
    if colonnes:
        texte += " GROUP BY " + ", ".join(colonnes)
    return texte


# --- un visuel -------------------------------------------------------------------------------


def role(cle):
    return cle.rsplit(".", 1)[-1].replace("Axis", "")


def convertir_visuel(visuel, modele, regles, indicateur=False):
    fiche = {k: visuel[k] for k in ("titre", "type", "table", "limitation")}
    fiche.update(dimensions=[], mesures=[])
    axes = {
        role(c): t
        for c, t in visuel["expressions"].items()
        if role(c) != "WhereClauseExpression"
    }
    axe_x = (lire_axe(axes.get("X", "")) or [None])[0] if indicateur else None
    try:
        ctx = Contexte(
            visuel["table"], modele, regles, visuel["limitation"], indicateur, axe_x
        )
        for nom, texte in axes.items():
            colonnes = lire_axe(texte)
            if colonnes is None or (indicateur and nom == "X"):
                continue
            for colonne in colonnes:
                dimension = {
                    "axe": nom,
                    "spotfire": colonne,
                    "source": ctx.source(colonne),
                }
                dimension["qlik"] = ctx.champ(colonne)
                if colonne not in [d["spotfire"] for d in fiche["dimensions"]]:
                    fiche["dimensions"].append(dimension)
    except NonConvertible as raison:
        fiche["arbitrage"] = str(raison)
        return fiche
    carte = "Map" in visuel["type"]
    for nom, texte in axes.items():
        if lire_axe(texte) is not None:
            continue
        if carte and nom in ("X", "Y"):
            fiche.setdefault("coordonnees", {})[nom] = ctx.champ(texte.strip("[]"))
            continue
        if nom not in AXES_MESURE:
            fiche["mesures"].append(
                {"axe": nom, "spotfire": texte, "arbitrage": "axe sans règle"}
            )
            continue
        try:
            lues = lire_mesures(texte)
        except NonConvertible as raison:
            fiche["mesures"].append(
                {"axe": nom, "spotfire": texte, "arbitrage": str(raison)}
            )
            continue
        for libelle, arbre in lues:
            mesure = {
                "axe": nom,
                "libelle": libelle,
                "spotfire": texte if len(lues) == 1 else "",
            }
            ctx.appliquees = set()
            dernier = bool(indicateur and axe_x and not contient(arbre, "fenetre"))
            try:
                mesure["qlik"] = qlik(arbre, ctx, dernier)
                mesure["sql"] = requete(
                    sql(arbre, ctx), fiche["dimensions"], ctx, dernier
                )
                mesure["regles"] = sorted(ctx.appliquees)
            except NonConvertible as raison:
                mesure["arbitrage"] = str(raison)
            fiche["mesures"].append(mesure)
    return fiche


def main():
    inventaire = json.loads((SORTIES / "inventaire.json").read_text(encoding="utf-8"))
    regles = json.loads((DOSSIER / "regles.json").read_text(encoding="utf-8"))
    modele = lire_modele(
        (RACINE / "qlik" / "chargement.qvs").read_text(encoding="utf-8")
    )
    pages = []
    for page in inventaire["pages"]:
        visuels = []
        for visuel in page["visuels"]:
            if "indicateurs" in visuel:
                for carte in visuel["indicateurs"]:
                    fiche = convertir_visuel(
                        dict(carte, type="Kpi"), modele, regles, True
                    )
                    visuels.append(dict(fiche, groupe=visuel["titre"]))
            else:
                visuels.append(convertir_visuel(visuel, modele, regles))
        pages.append({"titre": page["titre"], "visuels": visuels})
    (SORTIES / "conversions.json").write_text(
        json.dumps(pages, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    visuels = [v for p in pages for v in p["visuels"]]
    mesures = [m for v in visuels for m in v["mesures"]]
    faites = [m for m in mesures if "qlik" in m]
    print("%d visuels, %d expressions de mesure" % (len(visuels), len(mesures)))
    print(
        "converties par règles : %d ; à arbitrer : %d"
        % (len(faites), len(mesures) - len(faites))
    )
    raisons = collections.Counter(m["arbitrage"] for m in mesures if "arbitrage" in m)
    raisons.update(
        "visuel entier : " + v["arbitrage"] for v in visuels if "arbitrage" in v
    )
    for raison, nombre in raisons.most_common():
        print("  à arbitrer (%d) : %s" % (nombre, raison))
    for regle, nombre in collections.Counter(
        r for m in faites for r in m["regles"]
    ).most_common():
        print("  règle (%d) : %s" % (nombre, regle))


if __name__ == "__main__":
    main()
