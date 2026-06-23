# Ops Briefing

Pilot accident-prevention briefing demo for Part 121 / Part 135 style jet operations.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m src.seed
uvicorn src.main:app --reload
```

Open `http://127.0.0.1:8000` and search `KE629`.

## API

`GET /api/briefing/{flight_number}`

The backend uses Aviationstack when `AVIATIONSTACK_API_KEY` is set. If the flight API or NOAA weather API is unavailable, the app falls back to local route data and route-based threat matching.

## Demo Notes

`sample_events.json` contains clearly marked sample/demo events for prevention-briefing behavior. They are not official accident records unless a source URL says otherwise.

## GitHub Pages Static Site

The `docs/` folder contains a static GitHub Pages version that runs without FastAPI.

```powershell
uv run --with-requirements requirements.txt python tools\export_static_site_data.py
git add docs tools\export_static_site_data.py
git commit -m "Update static GitHub Pages briefing"
git push
```

In GitHub repository settings, enable Pages with:

- Source: Deploy from a branch
- Branch: `main`
- Folder: `/docs`

The public URL will be:

`https://outinletter.github.io/pilotbriefing/`
