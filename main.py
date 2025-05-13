from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core import get_halachic_answer, get_weekly_reading
from fastapi.staticfiles import StaticFiles

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    weekly = get_weekly_reading().get("weekly_reading", "")
    return templates.TemplateResponse("form.html", {
        "request": request,
        "weekly_reading": weekly
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
        "weekly_reading": result.get("weekly_reading", "Error fetching weekly portion")
    })


