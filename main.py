from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core import get_halachic_answer, get_weekly_reading, hebrew_date
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import requests

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def redirect_to_language():
    return RedirectResponse(url="/lang")


@app.get("/lang", response_class=HTMLResponse)
async def select_language(request: Request):
    return templates.TemplateResponse("language_select.html", {"request": request})


@app.get("/form", response_class=HTMLResponse)
async def get_form(request: Request, lang: str = "en"):
    result = get_weekly_reading()
    hd = hebrew_date()
    template = "form.html" if lang == "en" else "form_he.html"

    return templates.TemplateResponse(template, {
        "request": request,
        "parsha": result.get("parsha"),
        "error": result.get("error"),
        "hebrew_date": hd,
        "lang": lang
    })


@app.post("/api/ask", response_class=HTMLResponse)
async def api_ask_halacha(request: Request, user_question: str = Form(...), community: str = Form(...)):
    # Process the form data and get the answer
    result = get_halachic_answer(user_question, community)
    # Return just the result part to update on the page
    return templates.TemplateResponse("answer_section.html", {
        "request": request,
        "answer": result["answer"],
        "sources": result["sources"],
        "confidence": result["confidence"]
    })

@app.post("/api/weekly", response_class=HTMLResponse)
async def api_get_weekly(request: Request):
    result = get_weekly_reading()
    return templates.TemplateResponse("weekly_section.html", {
    "request": request,
    "parsha": result.get("parsha"),
    "error": result.get("error")
})
    
@app.get("/lang", response_class=HTMLResponse)
async def select_language(request: Request):
    return templates.TemplateResponse("language_select.html", {"request": request})



