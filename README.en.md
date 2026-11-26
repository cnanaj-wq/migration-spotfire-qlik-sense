<p align="center">
  <img src="img/entete.png" alt="Banner: migration of a management control dashboard from Spotfire to Qlik Sense Cloud" width="100%" />
</p>

<h1 align="center">BI migration: from Spotfire to Qlik Sense Cloud</h1>

<p align="center">
  <b>How do you migrate a BI dashboard while keeping its indicators reliable?</b><br />
  The same management control dashboard, migrated twice: by hand then with Python scripts.
</p>

<p align="center">
  <a href="README.md"><img src="img/langue-fr.svg" alt="FR · Français" height="36"></a>&nbsp;<a href="README.en.md"><img src="img/langue-us-actif.svg" alt="EN · English (displayed language)" height="36"></a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/licence-MIT-1f3a5f" alt="MIT license" /></a>
  <a href="https://github.com/cnanaj-wq/migration-spotfire-qlik-sense/actions/workflows/controle.yml"><img src="https://github.com/cnanaj-wq/migration-spotfire-qlik-sense/actions/workflows/controle.yml/badge.svg" alt="Automated check" /></a>
  <img src="https://img.shields.io/badge/synthetic-data-1f3a5f" alt="Synthetic data" />
  <img src="https://img.shields.io/badge/Qlik%20Sense%20Cloud-5%20sheets-009845" alt="Qlik Sense Cloud" />
  <img src="https://img.shields.io/badge/Python-3.12-3776ab?logo=python&logoColor=white" alt="Python 3.12" />
</p>

<p align="center">
  <a href="https://cnanaj-wq.github.io/migration-spotfire-qlik-sense/"><b>Discover the project</b></a> (in French)
  &nbsp;·&nbsp; <a href="https://cnanaj-wq.github.io/migration-spotfire-qlik-sense/processus.html">Interactive diagram</a>
  &nbsp;·&nbsp; <a href="#3-results">Results</a>
  &nbsp;·&nbsp; <a href="#7-quick-start">Reproduce</a>
  &nbsp;·&nbsp; <a href="#9-limitations">Limitations</a>
</p>

This project explores two ways of migrating a management control dashboard: a manual migration and a migration automated with scripts.

The goal is to identify what can be automated, what must be checked, and what still needs a person.

## 1. Business context

Orvane Distribution is a fictional company that wants to move its management control dashboard from Spotfire to Qlik Sense Cloud.

The dashboard covers five areas:

- Executive summary
- Revenue and margin
- Branch performance
- Budget variances and income statement
- Working capital and cash

The project relies on 14,892 rows of fictional data spread over nine CSV tables. The dashboard, the data columns and the scripts are in French.

## 2. The solution in two approaches

### LAB 01: manual migration

- Adapting the data model.
- Rewriting the calculation expressions.
- Rebuilding the dashboards.
- Setting up security by region.
- Comparing results between the two tools.

[Read the LAB 01 mappings](qlik/correspondances.md) (in French)

### LAB 02: automated migration

- Extracting the Spotfire components.
- Converting expressions with rules.
- Rebuilding objects through the Qlik Sense APIs.
- Checking results in SQL.
- Fixing the gaps found.

[Read LAB 02](lab02/README.md) (in French)

## 3. Results

| Indicator | Result |
|---|---:|
| Sheets migrated by hand | 5 |
| Indicators compared between the two tools (LAB 01) | 11 of 11 identical |
| Formulas converted (LAB 02) | 103 of 103 |
| Objects generated (LAB 02) | 39 of 41 |
| Values matching at the first SQL check | 518 of 611 |
| Values matching after the fix | 611 of 611 |

The first SQL check exposed a conversion error that affected nine indicators. The check allows a gap of 0.005 per value.

The 41 objects of LAB 02 are the 41 visuals read from the Spotfire file: 20 charts, tables and map, and 21 KPI cards. The Spotfire scripts create 25, because they lay the 21 cards out in 5 rows.

This experiment makes one point: automating a migration is not enough. The results it produces must also be verified.

## 4. Before and after the migration

**Spotfire, the source application**

![Spotfire screenshot of the Executive summary page](img/spotfire/01_synthese_direction.png)

**Qlik Sense Cloud, the target application**

![Qlik Sense screenshot of the Executive summary sheet](img/qlik/01_synthese_direction.png)

All five pages, in their three versions (Spotfire, LAB 01, LAB 02), can be browsed on [the project page](https://cnanaj-wq.github.io/migration-spotfire-qlik-sense/#ecrans).

## 5. Process and architecture

Extraction → Conversion → Rebuild → SQL check → Fixing the gaps → New check

[Open the interactive diagram](https://cnanaj-wq.github.io/migration-spotfire-qlik-sense/processus.html) · [Detailed architecture and flowchart](docs/architecture.en.md)

## 6. Technologies

- Spotfire and IronPython
- Qlik Sense Cloud and the Qlik Sense APIs
- Python
- SQL
- Git and GitHub Actions

## 7. Quick start

Prerequisites: Git and Python 3.12. Spotfire is only needed to open the dashboard.

```bash
git clone https://github.com/cnanaj-wq/migration-spotfire-qlik-sense.git
cd migration-spotfire-qlik-sense
pip install -r requirements.txt
python generer_donnees.py
python controles/verifier_donnees.py
```

Expected result: the 9 tables in `data/` are regenerated identically, then the check prints 4 `OK` lines and `Tout concorde` ("everything reconciles").

## 8. Choose your next step

| Resource | Description |
|---|---|
| [Architecture](docs/architecture.en.md) | Repository content, architecture, flowchart, folder map |
| [Spotfire](docs/reproduire.md) | Reproduce the source application (in French) |
| [Qlik Sense](qlik/correspondances.md) | Mappings between the two tools (in French) |
| [LAB 02](lab02/README.md) | Automated migration (in French) |
| [Data](data/) | Fictional dataset |
| [Checks](controles/) | Data consistency check |
| [Parameters](parametres/) | Assumptions and business rules |

### Repository map

```
data/, parametres/   the fictional dataset and its assumptions
spotfire/            the source application and its build scripts
qlik/                LAB 01: load script, sheets, mappings
lab02/               LAB 02: extraction, conversion, generation, SQL check
controles/           data consistency check
index.html, processus.html   the project page and its interactive diagram
docs/, img/          documentation, diagrams and screenshots
```

## 9. Limitations

- The project covers one dashboard built on fictional data. It consists of two technical demonstrators.
- Business validation is an essential step before any move to production.

## License

Code under the [MIT license](LICENSE). To propose a fix: [CONTRIBUTING.md](CONTRIBUTING.md). To report a security issue: [SECURITY.md](SECURITY.md).

## Author

**Cédric NANA** — Expert BI & Data | Analytics & AI Automation

[GitHub](https://github.com/cnanaj-wq) · [Professional website](https://cedricnana.fr)
