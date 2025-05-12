from openai import OpenAI
from dotenv import load_dotenv
import os
import re
import requests
from bs4 import BeautifulSoup

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

def find_portion():
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
        # This is a placeholder. You would replace this with actual logic to get the weekly reading.
        weekly_reading = "This week's Torah portion is: " + find_portion()
        return {"weekly_reading": weekly_reading}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}
