from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import RedirectResponse, HTMLResponse, FileResponse
from starlette.templating import Jinja2Templates
from pathlib import Path
import pandas as pd

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/")
async def main_route(request: Request):
    return templates.TemplateResponse(
        request=request, name="home.html", context={"selected": "home"}
    )

favicon_path = 'favicon.ico'


@app.get('/static/images/ekcx.jpg', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)


@app.get("/events/", response_class=HTMLResponse)
async def events(request: Request):
    return templates.TemplateResponse(
        request=request, name="events.html", context={"selected": "events"}
    )

@app.get("/events/{year}/{round_num}", response_class=HTMLResponse)
async def event_detail(request: Request, year: int, round_num: int):
    # Event data - could be moved to a database or config file later
    events_data = {
        2025: {
            1: {
                "name": "Round 1: Sandwich",
                "date": "September 14, 2025",
                "location": "Sandwich",
                "british_cycling_url": "https://www.britishcycling.org.uk/events/details/323235/East-Kent-Cyclo-Cross-League-Round-1-SandwichTechCross---Tim-Mountford-Memorial",
                "photos_url": "https://mattbristow.photoshelter.com/gallery-collection/Round-1-Sandwich-Tech-14-09-2025/C0000NswQ1d1LX.o",
                "status": "completed"
            },
            2: {
                "name": "Round 2: Dover (Duke of York)",
                "date": "October 19, 2025",
                "location": "Dover",
                "british_cycling_url": "https://www.britishcycling.org.uk/events/details/327079/East-Kent-Cyclo-Cross-League-Round-2-ActivCyclesCross-#results",
                "photos_url": "https://mattbristow.photoshelter.com/gallery-collection/Round-2-Duke-of-Yorks-Royal-Military-School-19-10-2025/C0000P8dCh6I3wG0",
                "status": "completed"
            },
            3: {
                "name": "Round 3: Ramsgate (St Lawrence College Cross)",
                "date": "November 16, 2025",
                "location": "Ramsgate",
                "british_cycling_url": "https://www.britishcycling.org.uk/events/details/328116/East-Kent-Cylco-Cross-League-Round-3-StLawrenceCollegeCross",
                "status": "upcoming"
            },
            4: {
                "name": "Round 4: Betteshanger",
                "date": "December 7, 2025",
                "location": "Betteshanger Country Park, Deal",
                "british_cycling_url": "https://www.britishcycling.org.uk/events/details/328600/East-Kent-Cyclo-Cross-League-Round-4-CondorCyclesCross",
                "status": "upcoming"
            },
            5: {
                "name": "Round 5: TBA",
                "date": "January 18, 2026",
                "location": "TBA",
                "british_cycling_url": "https://www.britishcycling.org.uk/events?q=East+Kent+Cyclo+Cross+Round+5",
                "status": "upcoming"
            }
        }
    }
    
    event = events_data.get(year, {}).get(round_num)
    if not event:
        return templates.TemplateResponse(
            request=request, name="events.html", context={"selected": "events", "error": "Event not found"}
        )
    
    # Build results sections for completed rounds using local CSV/Excel files
    results_sections = []
    try:
        if year == 2025 and round_num in (1, 2):
            results_dir = Path(__file__).parent / 'results' / str(year) / str(round_num)
            if results_dir.exists():
                # Columns to include in display (dynamic, include laps if present)
                base_cols = [
                    ('Pos', 'Position'),
                    ('Position', 'Position'),
                    ('Last Name', 'Last Name'),
                    ('Surname', 'Last Name'),
                    ('First Name', 'First Name'),
                    ('Forename', 'First Name'),
                    ('Team', 'Team'),
                    ('Club', 'Team'),
                    ('Category', 'Category'),
                    ('Time', 'Time'),
                    ('Gap', 'Gap'),
                ]
                lap_cols = [(f'Lap {i}', f'Lap {i}') for i in range(1, 20)]
                preferred_cols = base_cols + lap_cols

                # Helper: clean and reduce columns, dropping licence-like fields
                def clean_results_df(df: pd.DataFrame) -> pd.DataFrame:
                    # Remove CrossMgr footer rows if present
                    def row_contains_footer(row) -> bool:
                        for val in row:
                            if isinstance(val, str) and 'Powered by CrossMgr' in val:
                                return True
                        return False

                    if not df.empty:
                        df = df[~df.apply(row_contains_footer, axis=1)]

                    # Drop any licence columns
                    drops = [c for c in df.columns if str(c).strip().lower() in ("licence", "license", "bc licence", "bc license", "bc_licence", "bc_license") or "licen" in str(c).strip().lower()]
                    if drops:
                        df = df.drop(columns=drops)

                    # Build keep columns dynamically in desired order
                    keep = []
                    col_map = {}
                    for src, disp in preferred_cols:
                        if src in df.columns and src not in keep:
                            keep.append(src)
                            col_map[src] = disp

                    if not keep:
                        return pd.DataFrame()

                    # Reduce to kept columns and rename
                    df = df[keep].rename(columns=col_map)

                    # Drop rows that are fully empty across kept columns
                    df = df.dropna(how='all')

                    # Render NaNs as blanks for non-empty rows
                    df = df.where(df.notna(), '')

                    return df

                def map_filename_to_title(stem: str) -> str:
                    name = stem.lower()
                    if 'elite female' in name or 'elite women' in name:
                        return 'Elite Female'
                    if 'elite open' in name or 'senior open' in name:
                        return 'Elite Open'
                    if 'under 12' in name or 'u12' in name:
                        return 'Under 12'
                    if 'under 16' in name or 'u16' in name:
                        return 'Youth U16/U14'
                    if 'v40' in name or 'm40' in name:
                        return 'Veteran 40 Open'
                    if 'v50' in name or 'm50' in name:
                        return 'Veteran 50 Open'
                    return stem

                # Gather files (CSV and XLSX)
                files = list(results_dir.glob('*.csv')) + list(results_dir.glob('*.CSV')) + list(results_dir.glob('*.xlsx'))
                for path in sorted(files):
                    df = pd.DataFrame()
                    try:
                        if path.suffix.lower() == '.csv':
                            # Try common encodings
                            for enc in (None, 'utf-8', 'utf-8-sig', 'latin-1'):
                                try:
                                    if enc is None:
                                        df = pd.read_csv(path)
                                    else:
                                        df = pd.read_csv(path, encoding=enc)
                                    break
                                except Exception:
                                    df = pd.DataFrame()
                            if df.empty:
                                continue
                        else:
                            # Excel files have headers at row 5 (0-indexed: row 4 is header row, row 5 is data start)
                            df = pd.read_excel(path, header=5)
                    except Exception:
                        continue

                    df = clean_results_df(df)
                    if df.empty:
                        continue

                    table_html = df.to_html(index=False, border=0, classes='event-results-table', na_rep='')
                    section_title = map_filename_to_title(path.stem)
                    results_sections.append({'title': section_title, 'html': table_html})
    except Exception as e:
        # Fail silently for results; page should still render
        # Uncomment the line below for debugging if needed:
        # import logging; logging.error(f"Error loading results: {e}")
        results_sections = []

    context = {
        "selected": "events",
        "event_name": event["name"],
        "event_date": event["date"],
        "event_location": event["location"],
        "british_cycling_url": event.get("british_cycling_url"),
        "photos_url": event.get("photos_url"),
        "status": event["status"],
        "results_sections": results_sections,
    }
    
    return templates.TemplateResponse(
        request=request, name="event_detail.html", context=context
    )

@app.get("/standings/{year}/{category}", response_class=HTMLResponse)
async def standings(request: Request, category: str, year: int):
    year = year or 2025
    return templates.TemplateResponse(
        request=request, name="standings.html", context={"category": category, "year": year, "selected": "standings"}
    )

@app.get("/rules", response_class=HTMLResponse)
async def rules(request: Request):
    return templates.TemplateResponse(
        request=request, name="rules.html", context={"selected": "standings"}
    )

@app.get("/faq", response_class=HTMLResponse)
async def faq(request: Request):
    return templates.TemplateResponse(
        request=request, name="faq.html", context={"selected": "standings"}
    )

@app.get("/info", response_class=HTMLResponse)
@app.get("/info/{section}", response_class=HTMLResponse)
async def info(request: Request, section: str = "rules"):
    section = section if section in ("rules", "faq") else "rules"
    return templates.TemplateResponse(
        request=request,
        name="info.html",
        context={"selected": "info", "section": section}
    )

@app.get("/media/", response_class=HTMLResponse)
async def media(request: Request):
    return templates.TemplateResponse(
        request=request, name="media.html", context={"selected": "media"}
    )

@app.get("/privacy/", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse(
        request=request, name="privacy.html", context={"selected": "home"}
    )

@app.get("/betteshangerparkchallenges/", response_class=HTMLResponse)
async def cycling_challenges(request: Request):
    return templates.TemplateResponse(
        request=request, name="betteshangerparkchallenges.html", context={"selected": "cycling"}
    )
