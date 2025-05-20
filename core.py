from openai import OpenAI
from dotenv import load_dotenv
import os
import requests
from datetime import date
from dateutil.parser import isoparse
import requests
import logging
from datetime import date, datetime
import re
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # Use env variable instead of hardcoded key
ALLOWED_SOURCES = ["sefaria.org", "halachipedia.com", "shulchanaruch.org"]


def estimate_confidence(answer: str) -> str:
    if any(phrase in answer.lower() for phrase in ["it depends", "possibly", "unclear", "some say", "might be"]):
        return "medium"
    elif len(answer) < 50 or "unsure" in answer.lower():
        return "low"
    else:
        return "high"

def extract_citations(text: str) -> list:
    sources = set()

    # Look for actual URLs in the response
    urls = re.findall(r'https?://[^\s\)\]]+', text)
    for url in urls:
        if "halachipedia" in url:
            sources.add("https://www.halachipedia.com")
        elif "sefaria" in url:
            sources.add("https://www.sefaria.org")
        elif "shulchanaruch" in url or "shulchan_aruch" in url:
            sources.add("https://www.sefaria.org/Shulchan_Aruch")

    # Keyword triggers
    text_lower = text.lower()
    if "halachipedia" in text_lower or "הלכתפדיה" in text:
        sources.add("https://www.halachipedia.com")
    if "sefaria" in text_lower or "ספריא" in text:
        sources.add("https://www.sefaria.org")
    if "shulchan aruch" in text_lower or "שו\"ע" in text or "שולחן ערוך" in text:
        sources.add("https://www.sefaria.org/Shulchan_Aruch")

    return list(sources)



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

def hebrew_date():
    """
    Convert today's Gregorian date to Hebrew date using Hebcal API.
    Returns the Hebrew date string (e.g. "כ"ו אייר תשפ"ה").
    """
    # Get today's date components
    today = date.today()
    greg_year = today.year
    greg_month = today.month
    greg_day = today.day

    # Build URL with f-string and zero-padded month/day
    url = (
        f"https://www.hebcal.com/converter"
        f"?cfg=json"
        f"&date={greg_year}-{greg_month:02d}-{greg_day:02d}"
        f"&g2h=1"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Hebcal JSON: {e}")
        raise ValueError(f"Could not reach Hebcal API: {e}")

    data = resp.json()
    # The API returns the Hebrew date in the 'hebrew' and 'hebrew_full' fields
    hebrew = data.get("hebrew_full") or data.get("hebrew")
    if not hebrew:
        logger.error(f"No 'hebrew' field in Hebcal response: {data}")
        raise ValueError("Hebcal response missing Hebrew date")

    return hebrew



def get_halachic_answer(question: str, affiliation: str) -> dict:
    sources = ", ".join(ALLOWED_SOURCES)
    try:
        prompt = (
            f"You are a halachic assistant. Use certified sources only from {sources}. "
            f"Answer **only** from the {affiliation} perspective and **do not** mention or compare other customs. "
            "Provide a concise, bullet-pointed answer with clear citations.\n\n"
            f"Question: {question}"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Updated to your preferred model
            messages=[
                {"role": "system", "content": "You are a knowledgeable assistant in Jewish law."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
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


def get_weekly_reading():
    try:
        raw = find_portion()
        title_en, _, title_he = raw.partition(" – ")
        details = get_parsha_details(title_en)
        return {"parsha": details}
    except Exception as e:
        return {"error": str(e)}

def get_parsha_details(parsha_title_en: str) -> dict:
    # strip off the "Parashat " prefix, if present
    slug = parsha_title_en.replace("Parashat ", "")
    url = f"https://www.sefaria.org/api/index/{slug}"
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    return {
        "title_en": data.get("title", parsha_title_en),
        "title_he": data.get("heTitle", ""),
        "summary": data.get("summary", ""),
        "sefaria_url": f"https://www.sefaria.org/texts/Torah%2BPortions%2F{slug}"
    }