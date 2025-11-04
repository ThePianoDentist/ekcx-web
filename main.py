from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import RedirectResponse, HTMLResponse, FileResponse
from starlette.templating import Jinja2Templates

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
                "british_cycling_url": "https://www.britishcycling.org.uk/events?q=East+Kent+Cyclo+Cross+Round+1+Sandwich",
                "status": "completed"
            },
            2: {
                "name": "Round 2: Duke Of York (Dover)",
                "date": "October 19, 2025",
                "location": "Dover",
                "british_cycling_url": "https://www.britishcycling.org.uk/events?q=East+Kent+Cyclo+Cross+Round+2+Duke+Of+York",
                "status": "completed"
            },
            3: {
                "name": "Round 3: Ramsgate",
                "date": "TBA",
                "location": "Ramsgate",
                "british_cycling_url": "https://www.britishcycling.org.uk/events?q=East+Kent+Cyclo+Cross+Round+3+Ramsgate",
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
                "date": "TBA",
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
    
    context = {
        "selected": "events",
        "event_name": event["name"],
        "event_date": event["date"],
        "event_location": event["location"],
        "british_cycling_url": event.get("british_cycling_url"),
        "status": event["status"]
    }
    
    return templates.TemplateResponse(
        request=request, name="event_detail.html", context=context
    )

@app.get("/standings/{year}/{category}", response_class=HTMLResponse)
async def standings(request: Request, category: str, year: int):
    year = year or 2024
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

@app.get("/media/", response_class=HTMLResponse)
async def media(request: Request):
    return templates.TemplateResponse(
        request=request, name="media.html", context={"selected": "media"}
    )

@app.get("/forum/", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse(
        request=request, name="forum.html", context={"selected": "forum"}
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
