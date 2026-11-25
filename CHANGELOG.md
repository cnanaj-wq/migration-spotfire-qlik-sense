# Journal des changements

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Versions : [SemVer](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté
- Jeu de données fictif de contrôle de gestion (société Orvane Distribution) : 9 tables CSV générées par `generer_donnees.py` à partir du classeur `parametres/parametres.xlsx`.
- Tableau de bord Spotfire de 5 onglets, construit par 6 scripts IronPython : synthèse direction, chiffre d'affaires et marge, carte des agences, écarts et compte de résultat, BFR et trésorerie.
- Sélections dynamiques : un clic sur un mois ou une agence recalcule les visuels des tables mensuelles reliées.
- Compte de résultat avec soldes intermédiaires (marge brute, EBITDA, résultat d'exploitation) mis en évidence et écart au budget en %.
- Bandeau cash : BFR, DSO, DIO, DPO, cycle de conversion, trésorerie disponible ; tuile des créances échues à plus de 90 jours.
- Contrôle de cohérence `controles/verifier_donnees.py` : 4 rapprochements entre les tables.
- Contrôle automatique : syntaxe et mise en forme des scripts, régénération et cohérence des données.

### À venir
- Migration du modèle, des expressions et des visualisations vers Qlik Sense Cloud, avec Section Access par région.
