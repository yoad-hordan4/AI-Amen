from openai import OpenAI
from dotenv import load_dotenv
import os
import requests
from datetime import date
from dateutil.parser import isoparse
from bs4 import BeautifulSoup

import requests
import logging
from datetime import date, datetime
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # Use env variable instead of hardcoded key

def estimate_confidence(answer: str) -> str:
    if any(phrase in answer.lower() for phrase in ["it depends", "possibly", "unclear", "some say", "might be"]):
        return "medium"
    elif len(answer) < 50 or "unsure" in answer.lower():
        return "low"
    else:
        return "high"

def extract_citations(text: str) -> list:
    # Example: capture known source URLs or titles
    sources = []
    if "halachipedia" in text.lower():
        sources.append("halachipedia.com")
    if "sefaria" in text.lower():
        sources.append("sefaria.org")
    if "shulchan aruch" in text.lower():
        sources.append("sefaria.org (Shulchan Aruch)")
    return list(set(sources))

def find_portion():
    url = (
        "https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&min=on&mod=on&nx=on"
        "&year=now&month=x&ss=on&mf=on&c=on&geo=geoname&geonameid=3448439&M=on&s=on"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Hebcal JSON: {e}")
        raise ValueError(f"Could not reach Hebcal API ({e})")

    data = resp.json()
    items = data.get("items")
    if not items:
        logger.error(f"No 'items' in Hebcal response: {data}")
        raise ValueError("Hebcal response malformed")

    today = date.today()
    for item in items:
        if item.get("category") == "parashat":
            # Parse ISO date without external libraries
            try:
                item_date = datetime.fromisoformat(item["date"]).date()
            except Exception:
                logger.warning(f"Skipping unparsable date: {item.get('date')}")
                continue

            if item_date >= today:
                title = item.get("title", "")
                hebrew = item.get("hebrew", "")
                return f"{title}{' – ' + hebrew if hebrew else ''}"

    raise ValueError("No upcoming parsha found in Hebcal data")


def get_halachic_answer(question: str, affiliation: str) -> dict:
    try:
        prompt = (
            f"You are a halachic assistant. Use certified sources like Halachipedia and Sefaria. "
            f"Answer the following question from a {affiliation} perspective. "
            f"Provide a concise answer with clear citations, and try to use bullet points where helpful.\n\n"
            f"Question: {question}"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Updated to your preferred model
            messages=[
                {"role": "system", "content": "You are a knowledgeable assistant in Jewish law."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.5
        )

        answer = response.choices[0].message.content.strip()

        return {
            "answer": answer,
            "sources": extract_citations(answer),
            "confidence": estimate_confidence(answer),
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "estimated_cost_usd": round(response.usage.prompt_tokens / 1_000_000 * 0.15 + response.usage.completion_tokens/1_000_000 * 0.6, 6)  # For gpt-4o-mini input
            },
            "model": response.model
        }

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

#def find_portion():
    url = "https://aish.com/weekly-torah-portion"
    response = requests.get(url)
    if response.status_code == 200:
        print("Successfully fetched the webpage!")
    else:
        print(f"Failed to fetch the webpage. Status code: {response.status_code}")
        exit()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    parsha = soup.find('h3', class_="parsha-name")
    if parsha:
        parsha_web = parsha.get_text(strip=True)
        return parsha_web
    else:
        return "Portion not found"


def get_weekly_reading():
    try:
        portion = find_portion()
        return {"weekly_reading": f"This week’s Torah portion is: {portion}"}
    except ValueError as ve:
        return {"error": str(ve)}
    except Exception:
        logger.exception("Unexpected error in get_weekly_reading")
        return {"error": "Unexpected error fetching weekly portion"}


