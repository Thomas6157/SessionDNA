# SessionDNA

**From Ironman training to data science:** a personal project to import, explore and understand swimming, cycling and running sessions.

## Context

I am preparing for an Ironman in 2027. SessionDNA grew from a practical question: how can I use my own training data to understand the structure and variety of my sessions while developing my data science skills?

The project is a personal learning and development environment. It is not a validated coaching or medical system.

## Objectives

- Structure real activity data and inspect its quality.
- Explore sessions through descriptive statistics and visualisations.
- Investigate intervals, pauses and different training profiles.
- Progressively evaluate machine learning approaches with explicit limitations.

## Current status

| Area | Status |
| --- | --- |
| Activity import and preparation | Implemented locally; pipeline continues to evolve |
| Exploratory analysis and visualisation | Implemented for personal activity data |
| Session structure and pauses | Experimental analysis scripts |
| Machine learning | Early clustering and classification experiments; no final general validation |
| Local application | Dashboard, API and training/calendar components present in source |
| Public source snapshot | Personal data excluded; clean-environment execution not yet validated |

The project source goes beyond the initial exploratory notebook stage. That does not establish the reliability of its models or the completeness of a production application. No performance score is promoted here.

## Data and architecture

Activity files are decoded and transformed into analysis tables, summaries and visualisations. Separate scripts support session structure analysis, exploratory clustering and supervised modelling. A local application exposes selected analyses and personal training organisation features.

Raw activities, location traces, calendars, account sessions, personal preferences and generated models must remain outside a public repository.

## Technologies

Core data work: **Python, Pandas, NumPy, Matplotlib and scikit-learn**. The repository also contains local API and web-interface components. Dependencies should be described according to their actual use, rather than treating every installed package as a demonstrated skill.

## Project structure

```text
src/
  inspect_fit.py          # Inspect a FIT activity
  analyze_activities.py   # Activity analysis
  analyze_triathlon.py    # Multisport analysis
  detect_intervals.py     # Interval experiments
  detect_pauses.py        # Pause experiments
  cluster_activities.py   # Clustering experiments
  train_classifier.py    # Classification experiments
  train_sport_model.py    # Sport-session modelling
  update_triathlon.py     # Local update pipeline
  serve_sessiondna.py     # Local server
  triathlon_web/          # Web interface
data/                    # Private inputs and generated outputs; excluded
models/                  # Generated models; excluded
pyproject.toml
requirements.txt
```

## Local setup

The current project metadata specifies Python 3.13. Use a virtual environment and install the dependencies from the existing `requirements.txt`.

```sh
python -m venv .venv
# Windows PowerShell:
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
```

Activate the virtual environment before the installation command. The project’s existing Windows workflow uses `.\.venv\Scripts\Activate.ps1`.

To inspect an activity you own:

```sh
python src/inspect_fit.py --file "data/raw/example.fit" --no-show
```

The local application workflow is:

```sh
python src/update_triathlon.py
python src/serve_sessiondna.py
```

The source snapshot excludes personal planning preferences. src/planning_preferences.json must be supplied locally before building the dashboard. These application commands depend on local inputs and configuration. They are not presented as a verified public-demo installation. Read the script options before running data imports or synchronisation.

## Limitations and next steps

- Personal data comes from one athlete and is not representative of a wider population.
- Labels and small experimental samples limit what can be concluded about model performance.
- Prospective evaluation on new sessions remains necessary.
- A privacy-safe example dataset and clean-environment setup are needed for a reproducible public release.
- Generative AI extensions are exploratory ideas, not validated delivered features.

## Author

Thomas Anquetin — engineering student at ESILV, Data & Artificial Intelligence, GenIA track.

[LinkedIn](https://www.linkedin.com/in/thomas-anquetin-0660702a9/)
