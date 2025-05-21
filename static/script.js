const lang = document.documentElement.lang;

const button_labels_english = [
  "Get Answer",
  "Ask the Rav",
  "Reveal the Psak",
  "Let My Question Go",
  "Torah, Take the Wheel",
  "Smite Me with Truth",
  "Seal the Verdict"
];

const button_labels_hebrew = [
  "קבל תשובה",
  "שאל את הרב",
  "גלה את הפסק",
  "שחרר את השאלה שלי",
  "תורה, קחי את ההגה",
  "הכיני אותי עם אמת",
  "חתום את הפסק"
];

const randomIndex = Math.floor(Math.random() * button_labels_english.length);
document.getElementById("rand-button").textContent =
  lang === "he" ? button_labels_hebrew[randomIndex] : button_labels_english[randomIndex];

document.getElementById('start-btn').addEventListener('click', () => {
  toggle('welcome-screen', false);
  toggle('affiliation-screen', true);
});
const affiliationTranslations = {
    "Modern Orthodox": { en: "Modern Orthodox", he: "אורתודוקסיה מודרנית" },
    "Yeshivish": { en: "Yeshivish", he: "בני ישיבה" },
    "Hasidic": { en: "Hasidic", he: "חסידי" },
    "Chabad": { en: "Hasidic - Chabad", he: "חב״ד" },
    "Dati Leumi": { en: "Dati Leumi", he: "דתי לאומי" }
};
  
document.getElementById('affiliation-next-btn').addEventListener('click', () => {
    const aff = document.getElementById('affiliation-select').value;
    const translated = affiliationTranslations[aff]?.[lang] || aff;
  
    document.getElementById('summary-affiliation-display').textContent = translated;
    document.getElementById('community').value = aff;
  
    toggle('affiliation-screen', false);
    toggle('practice-screen', true);
});

document.querySelectorAll('.practice-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const practice = btn.textContent;
    document.getElementById('summary-practice').textContent = practice;
    document.getElementById('practice').value = practice;
    toggle('practice-screen', false);
    toggle('app-screen', true);
  });
});

const form = document.getElementById('halacha-form');
form.addEventListener('submit', async e => {
  e.preventDefault();
  toggle('loading', true);
  document.getElementById('get-answer-btn').disabled = true;
  toggle('result', false);

  const res = await fetch('/api/ask', { method: 'POST', body: new FormData(form) });
  const html = await res.text();
  document.getElementById('result').innerHTML = html;
  toggle('loading', false);
  toggle('result', true);
  document.getElementById('get-answer-btn').disabled = false;
});

document.getElementById('user_question').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
  }
});

function toggle(id, show) {
  document.getElementById(id).classList.toggle('hidden', !show);
}
