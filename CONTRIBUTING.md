# Contribuer

Les corrections et les idées sont les bienvenues.

## Signaler une anomalie ou proposer une idée

Ouvre une issue avec le modèle proposé. Indique ce que tu as lancé, ce que tu attendais et ce que tu as obtenu.

## Proposer une modification

1. Crée une branche à partir de `main`.
2. Lance les contrôles avant de pousser :

   ```powershell
   pip install -r requirements.txt
   ruff check .
   ruff format --check .
   python controles/verifier_donnees.py
   ```

3. Si tu modifies un script de `spotfire/scripts/`, reconstruis le tableau de bord dans Spotfire (voir [docs/reproduire.md](docs/reproduire.md)) et vérifie que `_avertissements.log` contient « Aucun avertissement ».
4. Ouvre une pull request qui explique le pourquoi du changement.

## Règles

- Aucune donnée personnelle, aucun secret, aucun fichier d'application volumineux.
- Les données restent fictives : aucun nom d'entreprise ou de client réel.
- Tout chiffre ajouté à la documentation doit pouvoir être recalculé par une commande du dépôt.
