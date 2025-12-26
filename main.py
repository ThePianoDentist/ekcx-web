from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import RedirectResponse, HTMLResponse, FileResponse
from starlette.templating import Jinja2Templates
from pathlib import Path
import pandas as pd
from app.domain.results import load_results_from_json

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
                "photos_url": "https://mattbristow.photoshelter.com/gallery-collection/Round-3-St-Lawrence-College-16112025/C0000BxUK_zBe8W0",
                "status": "completed"
            },
            4: {
                "name": "Round 4: #CondorCyclesCross at Betteshanger Country Park",
                "date": "December 7, 2025",
                "location": "Betteshanger Country Park, Deal",
                "british_cycling_url": "https://www.britishcycling.org.uk/events/details/328600/East-Kent-Cyclo-Cross-League-Round-4-CondorCyclesCross",
                "photos_url": "https://mattbristow.photoshelter.com/gallery-collection/Round-4-Betteshanger-Park-07-12-2025/C00004TRC4XcNqG8",
                "status": "completed"
            },
            5: {
                "name": "Round 5: #BetteshangerCross at Betteshanger Country Park",
                "date": "January 18, 2026",
                "location": "Betteshanger Country Park, Deal",
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
    
    # Load precomputed results sections from JSON instead of extracting per request
    results_sections = load_results_from_json(year, round_num) or []

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
