# Auckland University Bus Patronage Dashboard
GISCI 343 Assignment 2 — Jessica Courtney (JCOU608)

## What it does
Shows which bus routes serve the Auckland University campus and how patronage varies by route, region and time period using 2024 AT data.

## Setup

1. Install dependencies:
```bash
uv pip install -r requirements.txt
```

2. Run the preprocessing script once:
```bash
python preprocess.py
```

3. Start the app:
```bash
shiny run --reload app.py
```

## Data
- AT patronage CSV (2024) — [AT Data Sources](https://at.govt.nz/about-us/at-data-sources/)
- Bus routes and stops — AT GIS Open Data

## Deployment
```bash
pip install shinylive
shinylive export . site
```
Push `site/` to `gh-pages` branch.

Live app: https://jcourtney-uoa.github.io/Public_Transport/