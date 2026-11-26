<p align="center">
  <img src="img/entete.png" alt="Bandeau : migration d'un tableau de bord de contrôle de gestion de Spotfire vers Qlik Sense Cloud" width="100%" />
</p>

<h1 align="center">Migration BI : de Spotfire vers Qlik Sense Cloud</h1>

<p align="center">
  <b>Comment migrer un tableau de bord BI tout en préservant la fiabilité de ses indicateurs ?</b><br />
  Le même tableau de bord de contrôle de gestion, migré deux fois : à la main, puis par scripts Python.
</p>

<p align="center">
  <a href="README.md"><img src="img/langue-fr-actif.svg" alt="FR · Français (langue affichée)" height="36"></a>&nbsp;<a href="README.en.md"><img src="img/langue-us.svg" alt="EN · English" height="36"></a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/licence-MIT-1f3a5f" alt="Licence MIT" /></a>
  <a href="https://github.com/cnanaj-wq/migration-spotfire-qlik-sense/actions/workflows/controle.yml"><img src="https://github.com/cnanaj-wq/migration-spotfire-qlik-sense/actions/workflows/controle.yml/badge.svg" alt="Contrôle automatique" /></a>
  <img src="https://img.shields.io/badge/donn%C3%A9es-synth%C3%A9tiques-1f3a5f" alt="Données synthétiques" />
  <img src="https://img.shields.io/badge/Qlik%20Sense%20Cloud-5%20feuilles-009845" alt="Qlik Sense Cloud" />
  <img src="https://img.shields.io/badge/Python-3.12-3776ab?logo=python&logoColor=white" alt="Python 3.12" />
</p>

<p align="center">
  <a href="https://cnanaj-wq.github.io/migration-spotfire-qlik-sense/"><b>Découvrir le projet</b></a>
  &nbsp;·&nbsp; <a href="https://cnanaj-wq.github.io/migration-spotfire-qlik-sense/processus.html">Schéma interactif</a>
  &nbsp;·&nbsp; <a href="#3-résultats-obtenus">Résultats</a>
  &nbsp;·&nbsp; <a href="#7-démarrage-rapide">Reproduire</a>
  &nbsp;·&nbsp; <a href="#9-limites">Limites</a>
</p>

Ce projet explore deux approches de migration d'un tableau de bord de contrôle de gestion : une migration manuelle et une migration automatisée par scripts.

L'objectif est d'identifier ce qui peut être automatisé, ce qui doit être contrôlé et ce qui nécessite encore une intervention humaine.

## 1. Contexte métier

Orvane Distribution est une entreprise fictive qui souhaite migrer son tableau de bord de contrôle de gestion de Spotfire vers Qlik Sense Cloud.

Le tableau de bord couvre cinq domaines :

- Synthèse de direction
- Chiffre d'affaires et marge
- Performance des agences
- Écarts budgétaires et compte de résultat
- BFR et trésorerie

Le projet repose sur 14 892 lignes de données fictives réparties dans neuf tables CSV.

## 2. La solution en deux approches

### LAB 01 : migration manuelle

- Adaptation du modèle de données.
- Réécriture des expressions de calcul.
- Reconstruction des tableaux de bord.
- Mise en place de la sécurité par région.
- Comparaison des résultats entre les deux outils.

[Consulter les correspondances du LAB 01](qlik/correspondances.md)

### LAB 02 : migration automatisée

- Extraction des composants Spotfire.
- Conversion des expressions par règles.
- Reconstruction des objets via les API Qlik.
- Contrôle des résultats en SQL.
- Correction des écarts détectés.

[Consulter le LAB 02](lab02/README.md)

## 3. Résultats obtenus

| Indicateur | Résultat |
|---|---:|
| Feuilles migrées manuellement | 5 |
| Indicateurs comparés entre les deux outils (LAB 01) | 11 sur 11 identiques |
| Formules converties (LAB 02) | 103 sur 103 |
| Objets générés (LAB 02) | 39 sur 41 |
| Valeurs conformes au premier contrôle SQL | 518 sur 611 |
| Valeurs conformes après correction | 611 sur 611 |

Le premier contrôle SQL a permis de détecter une erreur de conversion affectant neuf indicateurs. Le contrôle admet un écart de 0,005 par valeur.

Les 41 objets du LAB 02 sont les 41 visuels lus dans le fichier Spotfire : 20 graphiques, tableaux et carte, et 21 cartes d'indicateur. Les scripts Spotfire, eux, en créent 25, parce qu'ils posent les 21 cartes en 5 rangées.

Cette expérimentation souligne un point essentiel : automatiser une migration ne suffit pas. Il faut également vérifier la fiabilité des résultats produits.

## 4. Aperçu avant et après migration

**Spotfire, l'application source**

![Capture Spotfire de la page Synthèse direction](img/spotfire/01_synthese_direction.png)

**Qlik Sense Cloud, l'application cible**

![Capture Qlik Sense de la feuille Synthèse direction](img/qlik/01_synthese_direction.png)

Les cinq pages, dans leurs trois versions (Spotfire, LAB 01, LAB 02), se parcourent sur [la page du projet](https://cnanaj-wq.github.io/migration-spotfire-qlik-sense/#ecrans).

## 5. Processus et architecture

Extraction → Conversion → Reconstruction → Contrôle SQL → Correction des écarts → Nouveau contrôle

[Consulter le schéma interactif](https://cnanaj-wq.github.io/migration-spotfire-qlik-sense/processus.html) · [Architecture et logigramme détaillés](docs/architecture.md)

## 6. Technologies utilisées

- Spotfire et IronPython
- Qlik Sense Cloud et API Qlik
- Python
- SQL
- Git et GitHub Actions

## 7. Démarrage rapide

Prérequis : Git et Python 3.12. Spotfire n'est nécessaire que pour ouvrir le tableau de bord.

```bash
git clone https://github.com/cnanaj-wq/migration-spotfire-qlik-sense.git
cd migration-spotfire-qlik-sense
pip install -r requirements.txt
python generer_donnees.py
python controles/verifier_donnees.py
```

Résultat attendu : les 9 tables de `data/` sont régénérées à l'identique, puis le contrôle affiche 4 lignes `OK` et `Tout concorde`.

## 8. Choisir sa prochaine étape

| Ressource | Description |
|---|---|
| [Architecture](docs/architecture.md) | Contenu du dépôt, architecture, logigramme, plan des dossiers |
| [Spotfire](docs/reproduire.md) | Reproduire l'application source |
| [Qlik Sense](qlik/correspondances.md) | Correspondances entre les deux outils |
| [LAB 02](lab02/README.md) | Migration automatisée |
| [Données](data/) | Jeu de données fictives |
| [Contrôles](controles/) | Vérification de la cohérence des données |
| [Paramètres](parametres/) | Hypothèses et règles métier |

### Plan du dépôt

```
data/, parametres/   le jeu de données fictif et ses hypothèses
spotfire/            l'application source et ses scripts de construction
qlik/                LAB 01 : script de chargement, feuilles, correspondances
lab02/               LAB 02 : extraction, conversion, génération, contrôle SQL
controles/           contrôle de cohérence des données
index.html, processus.html   la page du projet et son schéma interactif
docs/, img/          documentation, schémas et captures
```

## 9. Limites

- L'expérimentation porte sur un seul tableau de bord et des données fictives.
- Deux objets n'ont pas été reconstruits automatiquement.
- La conformité des valeurs contrôlées ne garantit pas leur équivalence dans tous les contextes de sélection.
- Le contrôle SQL compare Qlik Sense aux fichiers d'origine, pas à Spotfire directement.
- La mise en forme des visuels générés reste à affiner.
- La sécurité Qlik Sense a été testée sur deux profils.
- L'application Qlik Sense n'est pas fournie directement dans le dépôt.
- La restriction d'affichage Spotfire ne constitue pas un véritable contrôle d'accès aux données.

Ce projet est un démonstrateur technique, et non une solution de migration prête pour la production.

## Licence

Code sous [licence MIT](LICENSE). Pour proposer une correction : [CONTRIBUTING.md](CONTRIBUTING.md). Pour signaler un problème de sécurité : [SECURITY.md](SECURITY.md).

## Auteur

**Cédric NANA** · Consultant BI & Data

[GitHub](https://github.com/cnanaj-wq) · [Site professionnel](https://cedricnana.fr)
