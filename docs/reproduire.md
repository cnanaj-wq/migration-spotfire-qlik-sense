# Reproduire le tableau de bord dans Spotfire

Testé avec Spotfire Industry Pro 15.1 (version d'essai), sous Windows.

## 1. Placer le dépôt

Les scripts sont lus dans `C:/Migration Spotfire To QlikSense/spotfire/scripts/`. Clone le dépôt dans `C:\Migration Spotfire To QlikSense`, ou adapte la constante `DOSSIER` en tête de [`construire_tout.py`](../spotfire/scripts/construire_tout.py) et le chemin du script lanceur (étape 3).

## 2. Ouvrir le document

Ouvre [`spotfire/controle_gestion_orvane.dxp`](../spotfire/). Les cinq onglets s'affichent tels qu'ils ont été enregistrés.

## 3. Reconstruire les onglets

1. Menu **Fichier > Propriétés du document**, onglet **Scripts**.
2. Sélectionne le script `lancer_script_du_depot`, puis **Éditer**.
3. Clique sur **Exécuter le script**.

Le lanceur exécute `construire_tout.py`, qui crée les cinq onglets à partir des scripts `01` à `05`, puis supprime les anciens. La construction prend une vingtaine de secondes.

## 4. Vérifier

Ouvre `spotfire/scripts/_avertissements.log` : il doit contenir `Aucun avertissement`. Sinon, chaque ligne nomme le réglage refusé par Spotfire et la raison.

## Utiliser le tableau de bord

- **Sélectionner** : clique sur un mois, une BU ou une agence. Les visuels des tables reliées se recalculent sur cette sélection, dans tous les onglets.
- **Désélectionner** : clique dans une zone vide d'un graphique ou sur le fond de la carte.

## Ce que font les scripts

| Script | Rôle |
|---|---|
| `construire_tout.py` | charte de couleurs, fonctions communes, relations entre tables, sélections, enchaînement des onglets |
| `01_synthese_direction.py` | tuiles de synthèse, CA mensuel, écart de marge par BU, EBITDA mensuel |
| `02_chiffre_affaires_marge.py` | CA par produit, écart par canal, indicateurs par BU, taux de marge |
| `03_carte_agences.py` | carte des agences, classement des écarts, détail par région |
| `04_ecarts_compte_resultat.py` | soldes, cascades de marge et d'EBITDA, compte de résultat |
| `05_bfr_tresorerie.py` | bandeau cash, DSO, BFR, trésorerie, balance âgée, créances échues |

`00_test_script.py` est un essai isolé, conservé pour vérifier qu'une installation de Spotfire autorise les scripts ; il n'est pas appelé par la construction.
