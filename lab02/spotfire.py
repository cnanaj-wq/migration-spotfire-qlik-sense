"""Lecture d'une expression Spotfire : du texte à un arbre que les règles savent parcourir.

Une expression comme  Sum(If([Exercice] = 2026, [BFR])) / 1000 as [BFR réel]  devient
('bin', '/', ('appel', 'Sum', [...]), ('nombre', '1000')) avec son libellé « BFR réel ».
Aucune dépendance : le découpage et l'analyse tiennent dans ce fichier.
"""

import re

JETONS = re.compile(
    r"""\s*(?:
        (?P<nombre>\d+(?:\.\d+)?)
      | "(?P<texte>(?:[^"\\]|\\.)*)"
      | \[(?P<colonne>(?:[^\]]|\]\])*)\]
      | (?P<nom>[A-Za-zÀ-ÿ_][A-Za-zÀ-ÿ0-9_]*)
      | (?P<signe><=|>=|<>|!=|[-+*/(),=<>])
    )""",
    re.VERBOSE,
)
COMPARAISONS = ("=", "<>", "!=", "<=", ">=", "<", ">")


class NonConvertible(Exception):
    """L'expression sort de ce que les règles savent traiter : elle part à l'arbitrage."""


def decouper(texte):
    jetons, position, texte = [], 0, texte.strip()
    while position < len(texte):
        trouve = JETONS.match(texte, position)
        if not trouve:
            raise NonConvertible(
                "caractère non reconnu : %s" % texte[position : position + 15]
            )
        position = trouve.end()
        sorte = trouve.lastgroup
        valeur = trouve.group(sorte)
        if sorte == "nom" and valeur.lower() in ("and", "or", "as", "over", "nest"):
            sorte, valeur = "mot", valeur.lower()
        jetons.append((sorte, valeur))
    return jetons


class Analyse:
    def __init__(self, texte):
        self.jetons = decouper(texte)
        self.rang = 0

    def vu(self, sorte, valeur=None):
        if self.rang >= len(self.jetons):
            return False
        ici = self.jetons[self.rang]
        return ici[0] == sorte and (valeur is None or ici[1] == valeur)

    def prendre(self, sorte, valeur=None):
        if not self.vu(sorte, valeur):
            raise NonConvertible("écriture inattendue près du jeton %d" % self.rang)
        self.rang += 1
        return self.jetons[self.rang - 1][1]

    def fini(self):
        return self.rang >= len(self.jetons)

    def expression(self):
        gauche = self.et()
        while self.vu("mot", "or"):
            self.rang += 1
            gauche = ("bin", "or", gauche, self.et())
        return gauche

    def et(self):
        gauche = self.comparaison()
        while self.vu("mot", "and"):
            self.rang += 1
            gauche = ("bin", "and", gauche, self.comparaison())
        return gauche

    def comparaison(self):
        gauche = self.somme()
        if any(self.vu("signe", signe) for signe in COMPARAISONS):
            signe = self.prendre("signe")
            gauche = ("bin", "<>" if signe == "!=" else signe, gauche, self.somme())
        return gauche

    def somme(self):
        gauche = self.produit()
        while self.vu("signe", "+") or self.vu("signe", "-"):
            gauche = ("bin", self.prendre("signe"), gauche, self.produit())
        return gauche

    def produit(self):
        gauche = self.signe()
        while self.vu("signe", "*") or self.vu("signe", "/"):
            gauche = ("bin", self.prendre("signe"), gauche, self.signe())
        return gauche

    def signe(self):
        if self.vu("signe", "-"):
            self.rang += 1
            return ("moins", self.signe())
        return self.fenetre()

    def fenetre(self):
        noeud = self.terme()
        while self.vu("mot", "over"):
            self.rang += 1
            self.prendre("signe", "(")
            noeud = ("fenetre", noeud, self.expression())
            self.prendre("signe", ")")
        return noeud

    def terme(self):
        if self.vu("nombre"):
            return ("nombre", self.prendre("nombre"))
        if self.vu("texte"):
            return ("texte", self.prendre("texte"))
        if self.vu("colonne"):
            return ("colonne", self.prendre("colonne").replace("]]", "]"))
        if self.vu("signe", "("):
            self.rang += 1
            interne = self.expression()
            self.prendre("signe", ")")
            return ("groupe", interne)
        nom = self.prendre("nom")
        self.prendre("signe", "(")
        arguments = []
        while not self.vu("signe", ")"):
            arguments.append(self.expression())
            if not self.vu("signe", ")"):
                self.prendre("signe", ",")
        self.prendre("signe", ")")
        return ("appel", nom, arguments)


def lire_condition(texte):
    """La limitation de données d'un visuel, ou None s'il n'en a pas."""
    if not texte.strip():
        return None
    analyse = Analyse(texte)
    arbre = analyse.expression()
    if not analyse.fini():
        raise NonConvertible("limitation lue en partie seulement")
    return arbre


def lire_mesures(texte):
    """Les mesures d'un axe : une liste de (libellé, arbre)."""
    analyse, mesures = Analyse(texte), []
    while not analyse.fini():
        arbre, libelle = analyse.expression(), ""
        if analyse.vu("mot", "as"):
            analyse.rang += 1
            libelle = analyse.prendre("colonne")
        mesures.append((libelle, arbre))
        if not analyse.fini():
            analyse.prendre("signe", ",")
    return mesures


def lire_axe(texte):
    """Les colonnes d'un axe catégoriel : <[Région] NEST [Agence]> donne ['Région', 'Agence'].

    Renvoie None si le texte n'est pas un axe catégoriel (c'est alors une mesure).
    [Axis.Default.Names] désigne les noms des mesures : ce n'est pas une colonne.
    """
    texte = texte.strip()
    if not (texte.startswith("<") and texte.endswith(">")):
        return None
    colonnes = re.findall(r"\[((?:[^\]]|\]\])*)\]", texte[1:-1])
    return [c for c in colonnes if c != "Axis.Default.Names"]
