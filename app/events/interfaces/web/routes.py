from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import HTMLResponse

from app.domain.results import load_results_from_json
from app.web.templates import templates

router = APIRouter()


@router.get("/events/", response_class=HTMLResponse)
async def events(request: Request):
    return templates.TemplateResponse(
        request=request, name="events.html", context={"selected": "events"}
    )


@router.get("/events/{year}/{round_num}", response_class=HTMLResponse)
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
                "photos_url": "https://mattbristow.photoshelter.com/gallery-collection/ROUND-5-Betteshanger-Park-18-01-2026/C0000eTX6kiUv_i8",
                "status": "completed"
            }
        }
    }

    event = events_data.get(year, {}).get(round_num)
    if not event:
        return templates.TemplateResponse(
            request=request, name="events.html", context={"selected": "events", "error": "Event not found"}
        )

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
