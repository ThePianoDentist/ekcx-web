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
                "status": "completed"
            },
            2: {
                "name": "Round 2: Dover (Duke of York)",
                "date": "October 19, 2025",
                "location": "Dover",
                "british_cycling_url": "https://www.britishcycling.org.uk/events/details/327079/East-Kent-Cyclo-Cross-League-Round-2-ActivCyclesCross-#results",
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
    
    # Build results sections for completed rounds using local Excel files
    results_sections = []
    try:
        if year == 2025 and round_num in (1, 2):
            results_dir = Path(__file__).parent / 'results' / str(year) / str(round_num)
            if results_dir.exists():
                # Columns to include, ignore any licence fields if present
                preferred_cols = [
                    ('Pos', 'Position'),
                    ('Last Name', 'Last Name'),
                    ('First Name', 'First Name'),
                    ('Team', 'Team'),
                    ('Category', 'Category'),
                ]
                for excel_path in sorted(results_dir.glob('*.xlsx')):
                    try:
                        df = pd.read_excel(excel_path)
                    except Exception:
                        continue
                    # Filter columns and rename for display
                    keep = []
                    col_map = {}
                    for src, disp in preferred_cols:
                        if src in df.columns:
                            keep.append(src)
                            col_map[src] = disp
                    if not keep:
                        continue
                    df = df[keep].rename(columns=col_map)
                    # Create HTML table without index
                    table_html = df.to_html(index=False, border=0, classes='event-results-table')
                    # Title from file name (strip extension)
                    section_title = excel_path.stem
                    results_sections.append({'title': section_title, 'html': table_html})
    except Exception:
        # Fail silently for results; page should still render
        results_sections = []

    context = {
        "selected": "events",
        "event_name": event["name"],
        "event_date": event["date"],
        "event_location": event["location"],
        "british_cycling_url": event.get("british_cycling_url"),
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
