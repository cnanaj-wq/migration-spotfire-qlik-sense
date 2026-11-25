<p align="center">
  <img src="img/entete.png" alt="Banner: migrating a management control dashboard from Spotfire to Qlik Sense Cloud" width="100%" />
</p>

<h1 align="center">Migrating a management control dashboard<br />from Spotfire to Qlik Sense</h1>

<p align="center">
  A 5-tab Spotfire dashboard, built entirely from versioned scripts,
  on a fictional 14,892-row dataset, as the starting point for a migration to Qlik Sense Cloud.
</p>

<p align="center">
  <a href="README.md"><img src="img/langue-fr.svg" alt="FR · Français" height="36"></a>&nbsp;<a href="README.en.md"><img src="img/langue-us-actif.svg" alt="EN · English (current language)" height="36"></a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-1f3a5f" alt="MIT license" /></a>
  <a href="https://github.com/cnanaj-wq/migration-spotfire-qlik-sense/actions/workflows/controle.yml"><img src="https://github.com/cnanaj-wq/migration-spotfire-qlik-sense/actions/workflows/controle.yml/badge.svg" alt="Automated check" /></a>
  <img src="https://img.shields.io/badge/data-synthetic-1f3a5f" alt="Synthetic data" />
  <img src="https://img.shields.io/badge/Qlik%20Sense%20Cloud-upcoming-a7b1bd" alt="Qlik Sense Cloud: upcoming" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Spotfire-15.1-3a4cf0" alt="Spotfire 15.1" />
  <img src="https://img.shields.io/badge/IronPython-scripts%20Spotfire-1f3a5f" alt="IronPython" />
  <img src="https://img.shields.io/badge/Python-3.12-3776ab?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/Ruff-lint%20%2B%20format-d7ff64?logo=ruff&logoColor=black" alt="Ruff" />
  <img src="https://img.shields.io/badge/openpyxl-Excel-1d6f42" alt="openpyxl" />
  <img src="https://img.shields.io/badge/Pillow-images-8c6bb1" alt="Pillow" />
  <img src="https://img.shields.io/badge/Git-version%20control-f05032?logo=git&logoColor=white" alt="Git" />
  <img src="https://img.shields.io/badge/GitHub%20Actions-CI-2088ff?logo=githubactions&logoColor=white" alt="GitHub Actions" />
  <img src="https://img.shields.io/badge/Mermaid-diagrams-ff3670?logo=mermaid&logoColor=white" alt="Mermaid" />
  <img src="https://img.shields.io/badge/VS%20Code-editor-007acc" alt="VS Code" />
</p>

<p align="center">
  <a href="#quick-start"><b>Quick start</b></a>
  &nbsp;·&nbsp; <a href="#architecture">Architecture</a>
  &nbsp;·&nbsp; <a href="docs/reproduire.md">Rebuild in Spotfire (French)</a>
  &nbsp;·&nbsp; <a href="#limitations">Limitations</a>
  &nbsp;·&nbsp; <a href="CHANGELOG.md">Changelog (French)</a>
</p>

## Quick start

Prerequisite: Python 3.12. Spotfire is only needed to open the dashboard.

```powershell
git clone https://github.com/cnanaj-wq/migration-spotfire-qlik-sense.git
cd migration-spotfire-qlik-sense
pip install -r requirements.txt
python generer_donnees.py
python controles/verifier_donnees.py
```

Expected result: the 9 files in `data/` are regenerated identically, then the check prints 4 `OK` lines and `Tout concorde` ("everything reconciles").

## Choose your next step

| You want to… | Go here |
|---|---|
| Open the dashboard in Spotfire | [docs/reproduire.md](docs/reproduire.md) |
| Read how a tab is built | [`spotfire/scripts/`](spotfire/scripts/) |
| Understand the dataset | [`generer_donnees.py`](generer_donnees.py) |
| Change the assumptions (budget, security, thresholds) | [`parametres/parametres.xlsx`](parametres/) |
| Check that the tables reconcile | [`controles/verifier_donnees.py`](controles/verifier_donnees.py) |

## Why this project

Migrating a dashboard from one tool to another is more than redrawing charts: the two engines do not compute or select data the same way. Showing that on a complete case required a realistic starting application that can be rebuilt and holds no confidential data.

This repository holds that application: the steering of a fictional company, Orvane Distribution, as seen by its management control team. It answers four questions: which indicators drift, where, why, and which lever to act on.

## What is inside

| Item | Count | Where |
|---|---|---|
| Dashboard tabs | 5 | [`spotfire/controle_gestion_orvane.dxp`](spotfire/) |
| Visuals (including 5 rows of 21 KPI tiles) | 25 | [`spotfire/scripts/`](spotfire/scripts/) |
| IronPython build scripts | 6 | [`spotfire/scripts/`](spotfire/scripts/) |
| Data tables (CSV) | 9 | [`data/`](data/) |
| Data rows | 14,892 | [`data/`](data/) |
| Reconciliation checks | 4 | [`controles/verifier_donnees.py`](controles/verifier_donnees.py) |

The five tabs:

| Tab | What it shows |
|---|---|
| Executive summary | Revenue, gross margin, margin rate, EBITDA and working capital: actual, gap to budget, gap to prior year |
| Revenue and margin | Revenue by product, gap by channel, indicators by business unit, monthly margin rate |
| Branch map | 24 branches on a map, ranking of revenue gaps in value |
| Variances and income statement | Volume, price and purchase cost effects, income statement with intermediate balances |
| Working capital, cash and aged balance | Working capital, DSO, DIO, DPO against target, cash, overdue receivables |

The dashboard, the data columns and the scripts are in French.

## Preview

The starting application in Spotfire, "Executive summary" tab. Screenshots of the application migrated to Qlik Sense will be added alongside.

<p align="center">
  <img src="img/spotfire/01_synthese_direction.png" alt="Spotfire screenshot of the tab : Executive summary" width="100%" />
</p>

<details>
<summary>See the other four tabs</summary>

**Revenue and margin**

<img src="img/spotfire/02_chiffre_affaires_marge.png" alt="Spotfire screenshot of the tab : Revenue and margin" width="100%" />

**Branch map**

<img src="img/spotfire/03_carte_agences.png" alt="Spotfire screenshot of the tab : Branch map" width="100%" />

**Variances and income statement**

<img src="img/spotfire/04_ecarts_compte_resultat.png" alt="Spotfire screenshot of the tab : Variances and income statement" width="100%" />

**Working capital, cash and aged balance**

<img src="img/spotfire/05_bfr_tresorerie.png" alt="Spotfire screenshot of the tab : Working capital, cash and aged balance" width="100%" />

</details>

## Architecture

```mermaid
flowchart LR
  P[parametres.xlsx<br/>assumptions, security, thresholds] --> G[generer_donnees.py]
  G --> D[data/<br/>9 CSV tables + 1 workbook]
  D --> C[controles/verifier_donnees.py<br/>4 reconciliations]
  D --> S[Spotfire<br/>controle_gestion_orvane.dxp]
  I[spotfire/scripts/<br/>6 IronPython scripts] --> S
  S -. upcoming migration .-> Q[Qlik Sense Cloud]
```

The dashboard is not drawn by hand. A launcher script, stored in the Spotfire document, runs [`construire_tout.py`](spotfire/scripts/construire_tout.py), which recreates the five tabs from the scripts in this repository. Every change to a visual is therefore a code change, reviewed and versioned.

## Results

Year-to-date figures at the end of October 2026, read in the dashboard and reconciled with the files in `data/`:

| Indicator | Actual | Budget | Gap |
|---|---|---|---|
| Revenue | 74,216 k€ | 73,426 k€ | +790 k€ |
| Gross margin | 21,858 k€ | 22,930 k€ | −1,072 k€ |
| EBITDA | 5,312 k€ | 6,550 k€ | −1,238 k€ |
| Operating income | 3,863 k€ | 5,102 k€ | −1,238 k€ |

The scenario is deliberate: the company sells more than planned, but its margin deteriorates. To recompute revenue and the margin gap: `python controles/verifier_donnees.py`.

## Repository map

```
generer_donnees.py      generates the fictional dataset from the parameters
creer_parametres.py     creates the initial parameter workbook (once)
parametres/             assumptions, security by region, alert thresholds
data/                   9 CSV tables and the same content as an Excel workbook
controles/              consistency check across tables
spotfire/               the Spotfire document and its build scripts
docs/                   Spotfire how-to, banner script
img/                    README visuals and screenshots
```

## Limitations

- **The migration to Qlik Sense is not done yet.** The repository currently holds the starting application. The Qlik model, expressions and sheets will follow.
- **Security by region is not enforced in Spotfire.** The `securite` table is ready for Qlik Section Access; the Spotfire trial used here cannot test it.
- **The build cannot run outside Spotfire.** IronPython scripts only run inside Spotfire; the repository's automated check only verifies their syntax.

## What is new

- **2026-11-25**: 5-tab Spotfire dashboard, dynamic selections across tables, data consistency check.

Full history: [CHANGELOG.md](CHANGELOG.md).

## Contributing, security, license

[Contributing](CONTRIBUTING.md) · [Report a security issue](SECURITY.md) · [MIT](LICENSE) license.

Spotfire and Qlik are trademarks of their respective owners. This repository is independent of these vendors.

## Author

**Cédric NANA** · BI & Data consultant · [GitHub](https://github.com/cnanaj-wq)

Personal experiment on synthetic data.
