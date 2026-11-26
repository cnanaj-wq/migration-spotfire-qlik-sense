# De Spotfire à Qlik Sense : correspondances

Ce qui change entre les deux outils, sur ce tableau de bord. Chaque expression Qlik de ce
document a été exécutée dans l'application et son résultat comparé à celui de Spotfire.

## Le modèle

| Sujet | Spotfire | Qlik Sense |
|---|---|---|
| Tables | 9 tables indépendantes, une par fichier | 1 table de faits, 5 tables de dimensions, 1 table isolée (seuils) |
| Liens entre tables | relations déclarées par script, en étoile autour des ventes, sur le mois | association automatique par les champs de même nom |
| Exercice et mois | colonnes présentes dans chaque table | calendrier unique, relié aux faits par la date |
| Propagation d'une sélection | à régler visuel par visuel (marquage et limitation) | native, sur tout le modèle |
| Ventes par produit et par agence | deux tables, mêmes noms de colonnes | mêmes lignes de faits, mesures de la maille agence préfixées « Agence » |
| Créances clients | table à part, ne suit pas le mois sélectionné | rattachées au dernier mois clos (octobre 2026) |

Conséquence de la table de faits unique : une région sélectionnée écarte les lignes sans
région. Le compte de résultat, le BFR et la trésorerie, qui n'existent qu'au niveau groupe
ou BU, n'affichent alors plus rien. Dans Spotfire, ils restaient affichés au niveau groupe.

## Les expressions

| Indicateur | Spotfire | Qlik Sense |
|---|---|---|
| CA réel, cumul 2026 | `Sum(If([Exercice] = 2026 and [Mois] <= 10, [CA Réel]))` | `Sum({<Exercice={2026}, [Mois clos]={1}>} [CA Réel])` |
| Écart de marge au budget | `Sum(If(…, [Marge brute Réel])) - Sum(If(…, [Marge brute Budget]))` | `Sum({<Exercice={2026}, [Mois clos]={1}>} [Marge brute Réel]) - Sum({<Exercice={2026}, [Mois clos]={1}>} [Marge brute Budget])` |
| EBITDA (solde du compte de résultat) | `Sum(If([Ordre] <= 7, [Réel]))` | `Sum({<Exercice={2026}, [Mois clos]={1}, [Ordre rubrique]={"<=7"}>} [CR Réel])` |
| Résultat d'exploitation | `Sum(If([Ordre] <= 8, [Réel]))` | même expression avec `[Ordre rubrique]={"<=8"}` |
| Trésorerie de fin de mois | `Sum(If([Exercice] = 2026, [Trésorerie fin de mois]))` filtrée sur le dernier mois | `Sum({<Exercice={2026}, Mois={10}>} [Trésorerie fin de mois])` |
| CA d'un périmètre de régions | clause de limitation ajoutée à chaque visuel | `Sum({<…, Région={'Sud-Est','Sud-Ouest'}>} [CA Réel])`, ou simple sélection |

La condition écrite dans un `If` côté Spotfire devient un ensemble (`{<…>}`) côté Qlik :
le filtre sort de l'agrégation et se lit avant elle.

## La sécurité par région

Les deux outils lisent la même table, `data/securite.csv`.

| Sujet | Spotfire | Qlik Sense |
|---|---|---|
| Mécanisme | clause de limitation ajoutée à chaque visuel par script | `Section Access` dans le script de chargement |
| Portée | affichage : les données restent dans le document | données : les lignes hors périmètre sont retirées à l'ouverture |
| Utilisateur | choisi à la main dans le script | reconnu à sa connexion, par son adresse e-mail |
| Données sans région (compte de résultat, BFR, trésorerie) | visibles par tous les profils | réservées aux profils « * » |
| Profil absent de la table | aucune ligne affichée | accès refusé |

Chaque ligne de faits porte un champ `PERIMETRE` : sa région, ou `GROUPE` quand la donnée
n'existe qu'au niveau du groupe. Un profil « * » reçoit tous les périmètres, groupe compris.

Avant de charger, remplacer `A_REMPLACER_PAR_TON_EMAIL_QLIK` dans la variable
`vAdministrateur` du script : sans l'adresse de la personne qui recharge, l'application se
ferme à son propre auteur.

Contrôle fait sur une copie de l'application, en se connectant avec le profil « Direction de
zone Sud » : deux régions visibles (Sud-Est, Sud-Ouest), 9 agences, chiffre d'affaires cumulé
de 26 283 259,77, compte de résultat vide. Avec le profil administrateur, les totaux
ci-dessous sont inchangés.

## Contrôle des totaux

Cumul 2026 à fin octobre, sans sélection.

| Indicateur | Spotfire et fichiers source | Qlik Sense |
|---|---|---|
| CA réel | 74 215 646,71 | 74 215 646,71 |
| CA budget | 73 426 115,16 | 73 426 115,16 |
| Écart de marge brute au budget | −1 072 496,42 | −1 072 496,42 |
| Somme des trois effets (volume, prix, coûts) | −1 072 496,42 | −1 072 496,42 |
| CA réel à la maille agence | 74 215 646,71 | 74 215 646,71 |
| EBITDA réel | 5 312 k€ | 5 311 850,59 |
| Résultat d'exploitation budget | 5 102 k€ | 5 101 584,68 |
| Encours clients au 31/10/2026 | 14 591 985,68 | 14 591 985,68 |
| Trésorerie fin octobre | 17,4 M€ | 17 430 100,69 |
| BFR fin octobre | 13,3 M€ | 13 253 640,82 |
| CA réel Sud-Est et Sud-Ouest | 26,3 M€ | 26 283 259,77 |

Lignes chargées : 14 877 dans la table de faits, soit les 14 892 lignes des fichiers moins
les 5 lignes de seuils et les 10 lignes de sécurité. Calendrier : 36 mois.

## Ce qui a demandé une correction

- **Décimales.** Les fichiers écrivent les décimales avec un point. Le script fixe
  `DecimalSep='.'` pour que les montants soient lus comme des nombres.
- **Calendrier.** Un `LOAD DISTINCT` placé sous un chargement précédent ne dédoublonne pas
  le résultat : le calendrier contenait 14 877 lignes au lieu de 36. Les dates distinctes
  passent maintenant par une table temporaire.
