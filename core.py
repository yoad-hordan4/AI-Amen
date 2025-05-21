from openai import OpenAI
from dotenv import load_dotenv
import os
import requests
from datetime import date, datetime
import logging
import re
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  
ALLOWED_SOURCES = [
    "sefaria.org",
    "halachipedia.com",
    "shulchanaruch.org",
    "chabad.org",
    "asktherav.com",
    "halachayomit.co.il",
    "moreshet.co"
]

AFFILIATION_CONTEXTS = {
    "Chabad": "according to Chabad Hasidic halachic tradition",
    "Dati Leumi": "according to Dati Leumi (Religious Zionist) halachic perspectives",
    "Yeshivish": "according to Yeshivish (Litvish) halachic norms",
    "Hasidic": "according to general Hasidic halachic tradition",
    "Modern Orthodox": "according to Modern Orthodox halachic norms"
}


def estimate_confidence(answer: str) -> str:
    if any(phrase in answer.lower() for phrase in ["it depends", "possibly", "unclear", "some say", "might be"]):
        return "medium"
    elif len(answer) < 50 or "unsure" in answer.lower():
        return "low"
    else:
        return "high"


def extract_citations(text: str) -> tuple[list[str], list[str]]:
    urls = set()
    raw_urls = re.findall(r'https?://[^\s\)\]]+', text)

    for url in raw_urls:
        urls.add(url)

    # Known mentions
    if "sefaria" in text.lower():
        urls.add("https://www.sefaria.org")
    if "halachipedia" in text.lower():
        urls.add("https://www.halachipedia.com")
    if "שו\"ע" in text or "שולחן ערוך" in text:
        urls.add("https://www.sefaria.org/Shulchan_Aruch")

    urls = list(urls)

    def get_site_name(url):
        domain = urlparse(url).netloc.replace("www.", "")
        name = domain.split('.')[0].capitalize()
        if "shulchan" in url:
            return "Shulchan Aruch"
        return name

    names = [get_site_name(url) for url in urls]
    return urls, names


def hebrew_date():
    today = date.today()
    url = (
        f"https://www.hebcal.com/converter?cfg=json&date={today.year}-{today.month:02d}-{today.day:02d}&g2h=1"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Hebcal JSON: {e}")
        raise ValueError(f"Could not reach Hebcal API: {e}")
    data = resp.json()
    return data.get("hebrew_full") or data.get("hebrew")


def get_parsha_details(parsha_title_en: str) -> dict:
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
    today = date.today()
    for item in data.get("items", []):
        if item.get("category") == "parashat":
            try:
                item_date = datetime.fromisoformat(item["date"]).date()
            except Exception:
                continue
            if item_date >= today:
                title = item.get("title", "")
                hebrew = item.get("hebrew", "")
                return f"{title}{' – ' + hebrew if hebrew else ''}"
    raise ValueError("No upcoming parsha found")


def get_weekly_reading():
    try:
        raw = find_portion()
        title_en, _, title_he = raw.partition(" – ")
        details = get_parsha_details(title_en)
        return {"parsha": details}
    except Exception as e:
        return {"error": str(e)}


def get_halachic_answer(question: str, affiliation: str, lang: str = "en") -> dict:
    sources = ", ".join(ALLOWED_SOURCES)
    language_instruction = "Answer in English." if lang == "en" else "ענה בעברית."
    affiliation_line = AFFILIATION_CONTEXTS.get(affiliation, f"from a {affiliation} halachic perspective")

    try:
        prompt = (
            f"You are a halachic assistant. Use certified sources only from {sources}. "
            f"Answer from the {affiliation_line}. Be explicit, direct, and include views that are central to that community even if they differ from other traditions."
            f"{language_instruction} Provide a concise, bullet-pointed answer with clear citations.\n\n"
            f"Question: {question}"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a knowledgeable assistant in Jewish law."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.5
        )

        answer = response.choices[0].message.content.strip()
        source_urls, source_names = extract_citations(answer)

        return {
            "answer": answer,
            "sources": source_urls,
            "sources_names": source_names,
            "confidence": estimate_confidence(answer),
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "estimated_cost_usd": round(response.usage.prompt_tokens / 1_000_000 * 0.15 + response.usage.completion_tokens/1_000_000 * 0.6, 6)
            },
            "model": response.model
        }

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}
