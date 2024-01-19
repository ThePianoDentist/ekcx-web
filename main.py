from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def main_route():
  return RedirectResponse(url='/static/index.html')
  #return {"message": "Hey, It is me Goku"}