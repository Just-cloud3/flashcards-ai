import streamlit as st
from google import genai
from google.genai import types
import PyPDF2
import json
import csv
import html
from io import StringIO
from datetime import datetime, timedelta
import os
import re
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

# YouTube transcript support
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False

# Load environment variables
load_dotenv()

# ===========================
# CONSTANTS
# ===========================
GEMINI_MODEL = "gemini-2.0-flash"
DAILY_LIMIT = 20
SR_INTERVALS = {1: 1, 2: 1, 3: 3, 4: 7, 5: 14}  # difficulty -> days
MAX_PDF_CHARS = 10000
MAX_INPUT_CHARS = 50000
MAX_TRANSCRIPT_CHARS = 30000

# Page config
st.set_page_config(
    page_title="FlashCards AI - Lietuvių studentams",
    page_icon="📚",
    layout="wide"
)

# Custom CSS for flip cards (mobile-friendly with onclick JS)
st.markdown("""
<style>
.flip-card {
    background-color: transparent;
    width: 100%;
    min-height: 250px;
    perspective: 1000px;
    margin: 20px 0;
}
.flip-card-inner {
    position: relative;
    width: 100%;
    min-height: 250px;
    text-align: center;
    transition: transform 0.6s;
    transform-style: preserve-3d;
    cursor: pointer;
}
.flip-card-inner.flipped {
    transform: rotateY(180deg);
}
@media (hover: hover) {
    .flip-card:hover .flip-card-inner {
        transform: rotateY(180deg);
    }
}
.flip-card-front, .flip-card-back {
    position: absolute;
    width: 100%;
    min-height: 250px;
    -webkit-backface-visibility: hidden;
    backface-visibility: hidden;
    border-radius: 15px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    font-size: 1.2em;
}
.flip-card-front {
    background: linear-gradient(135deg, #4a5fd5 0%, #5e3a8a 100%);
    color: white;
}
.flip-card-back {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: white;
    transform: rotateY(180deg);
}
</style>
""", unsafe_allow_html=True)

# Dark Mode CSS (will be applied conditionally)
DARK_MODE_CSS = """
<style>
    .stApp { background-color: #0e1117 !important; }
    [data-testid="stSidebar"] { background-color: #161b22 !important; }
    .stMarkdown, .stText, p, span, label { color: #c9d1d9 !important; }
    h1, h2, h3, h4, h5, h6 { color: #f0f6fc !important; }
    .stTextInput input, .stTextArea textarea {
        background-color: #21262d !important; color: #c9d1d9 !important; border-color: #30363d !important;
    }
    .stSelectbox > div > div { background-color: #21262d !important; color: #c9d1d9 !important; }
    .stButton > button { background-color: #238636 !important; color: white !important; border: none !important; }
    .stButton > button:hover { background-color: #2ea043 !important; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important; }
    .streamlit-expanderHeader { background-color: #21262d !important; color: #c9d1d9 !important; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; }
    .stAlert { background-color: #21262d !important; }
    .flip-card-front { background: linear-gradient(135deg, #1a1f35 0%, #2d1f3d 100%) !important; }
    .flip-card-back { background: linear-gradient(135deg, #0d2818 0%, #1a3d2e 100%) !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #161b22 !important; }
    .stTabs [data-baseweb="tab"] { color: #8b949e !important; }
    .stTabs [aria-selected="true"] { color: #f0f6fc !important; }
    .stSlider > div > div { background-color: #30363d !important; }
    [data-testid="stFileUploader"] { background-color: #21262d !important; }
    hr { border-color: #30363d !important; }
</style>
"""

# Initialize session state
if 'flashcards' not in st.session_state:
    st.session_state.flashcards = []
if 'flashcards_count' not in st.session_state:
    st.session_state.flashcards_count = 0
if 'current_card' not in st.session_state:
    st.session_state.current_card = 0
if 'is_premium' not in st.session_state:
    st.session_state.is_premium = False
if 'study_cards' not in st.session_state:
    st.session_state.study_cards = {}
if 'show_answer' not in st.session_state:
    st.session_state.show_answer = False
if 'generating' not in st.session_state:
    st.session_state.generating = False
if 'generation_success' not in st.session_state:
    st.session_state.generation_success = 0
if 'last_youtube_url' not in st.session_state:
    st.session_state.last_youtube_url = ""

# ==========================
# GEMINI API SETUP
# ==========================

def get_gemini_client(api_key):
    """Configure and return Gemini client with timeout"""
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=30_000)
    )

# ==========================
# YOUTUBE FUNCTIONS
# ==========================

def extract_video_id(youtube_url):
    """Extract video ID from various YouTube URL formats"""
    # Validate YouTube domain first
    if not re.search(r'(youtube\.com|youtu\.be)', youtube_url):
        return None

    patterns = [
        r'(?:v=)([0-9A-Za-z_-]{11})',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})',
        r'(?:live\/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    return None

def get_youtube_transcript(video_id, languages=['lt', 'en']):
    """Fetch transcript from YouTube video"""
    if not YOUTUBE_AVAILABLE:
        return {'success': False, 'error': 'YouTube biblioteka neįdiegta'}

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = None
        detected_lang = None

        for lang in languages:
            try:
                transcript = transcript_list.find_transcript([lang])
                detected_lang = lang
                break
            except NoTranscriptFound:
                continue

        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
                detected_lang = 'en (auto)'
            except NoTranscriptFound:
                # Fallback: iterate available transcripts
                try:
                    for t in transcript_list:
                        transcript = t
                        detected_lang = t.language_code
                        break
                except StopIteration:
                    pass

        if not transcript:
            return {'success': False, 'error': 'Šiam video nėra subtitrų'}

        transcript_data = transcript.fetch()

        if not transcript_data:
            return {'success': False, 'error': 'Transkripcija tuščia'}

        full_text = " ".join([seg['text'] for seg in transcript_data])
        duration = transcript_data[-1]['start'] + transcript_data[-1]['duration']

        # Limit transcript length (like PDF)
        if len(full_text) > MAX_TRANSCRIPT_CHARS:
            full_text = full_text[:MAX_TRANSCRIPT_CHARS]

        return {
            'success': True,
            'text': full_text,
            'language': detected_lang,
            'duration': duration,
            'segments': len(transcript_data)
        }
    except TranscriptsDisabled:
        return {'success': False, 'error': 'Subtitrai išjungti šiam video'}
    except NoTranscriptFound:
        return {'success': False, 'error': 'Nerasta subtitrų'}
    except Exception as e:
        return {'success': False, 'error': f'Klaida gaunant subtitrus: {type(e).__name__}'}

def format_duration(seconds):
    """Convert seconds to MM:SS format"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"

# ==========================
# SPACED REPETITION
# ==========================

def calculate_next_review(difficulty):
    """Calculate next review date based on difficulty (1-5)"""
    interval_days = SR_INTERVALS.get(difficulty, 3)
    return (datetime.now() + timedelta(days=interval_days)).isoformat()

def add_cards_to_study(flashcards):
    """Add generated flashcards to study deck with SR metadata"""
    for i, card in enumerate(flashcards):
        card_id = f"card_{datetime.now().timestamp()}_{i}"
        if card_id not in st.session_state.study_cards:
            st.session_state.study_cards[card_id] = {
                "id": card_id,
                "question": card.get("klausimas", ""),
                "answer": card.get("atsakymas", ""),
                "next_review": datetime.now().isoformat(),
                "difficulty": 3,
                "times_reviewed": 0
            }

def get_today_cards():
    """Get cards that need review today"""
    today = datetime.now().date()
    return [
        card for card in st.session_state.study_cards.values()
        if datetime.fromisoformat(card["next_review"]).date() <= today
    ]

def update_card_difficulty(card_id, difficulty):
    """Update card difficulty and schedule next review"""
    if card_id in st.session_state.study_cards:
        card = st.session_state.study_cards[card_id]
        card["difficulty"] = difficulty
        card["times_reviewed"] = card.get("times_reviewed", 0) + 1
        card["next_review"] = calculate_next_review(difficulty)

# ==========================
# FLASHCARD GENERATION
# ==========================

def parse_flashcards_json(content):
    """Parse JSON flashcards from AI response with fallback"""
    # Strip markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    # Try direct parse first
    try:
        flashcards = json.loads(content.strip())
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            flashcards = json.loads(match.group())
        else:
            return []

    if not isinstance(flashcards, list):
        return []

    # Validate card structure
    return [
        card for card in flashcards
        if isinstance(card, dict) and 'klausimas' in card and 'atsakymas' in card
    ]

def generate_flashcards_from_text(text, num_cards=10, language="lietuvių", api_key=None):
    """Generate flashcards using Gemini API"""
    if not api_key:
        st.error("Įveskite Gemini API key!")
        return []

    try:
        client = get_gemini_client(api_key)

        prompt = f"""Tu esi ekspertas akademinis asistentas, besispecializuojantis aktyvaus prisiminimo (active recall) metodikoje.

METODIKA (Active Recall):
- VENK bendrų klausimų tipo "Kas yra X?"
- NAUDOK:
  * Priežastingumą: "Kodėl X įvyksta?"
  * Procesus: "Kokie pagrindiniai X etapai?"
  * Palyginimus: "Kuo skiriasi X nuo Y?"
  * Pritaikymą: "Kaip naudojamas X praktikoje?"

PAVYZDYS:
❌ Blogai: {{"klausimas": "Kas yra fotosintezė?", "atsakymas": "Procesas augaluose"}}
✅ Gerai: {{"klausimas": "Kokia pagrindinė fotosintezės funkcija augalams?", "atsakymas": "Paversti saulės energiją į cheminę (gliukozę) augimui."}}

UŽDUOTIS:
Sukurk {num_cards} flashcard'ų iš šio teksto {language} kalba.

TEKSTAS:
{text[:MAX_INPUT_CHARS]}

GRAŽINK TIK JSON ARRAY formatu (be jokio papildomo teksto):
[
  {{"klausimas": "...", "atsakymas": "..."}},
  {{"klausimas": "...", "atsakymas": "..."}}
]
"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        if not response.text:
            st.error("AI negrąžino atsakymo. Bandykite sutrumpinti tekstą.")
            return []

        return parse_flashcards_json(response.text)

    except Exception as e:
        error_type = type(e).__name__
        if "quota" in str(e).lower() or "429" in str(e):
            st.error("API kvotos limitas pasiektas. Palaukite kelias minutes.")
        elif "timeout" in str(e).lower():
            st.error("API užklausa užtruko per ilgai. Bandykite trumpesnį tekstą.")
        elif "invalid" in str(e).lower() and "key" in str(e).lower():
            st.error("Neteisingas API raktas. Patikrinkite ir bandykite dar kartą.")
        else:
            st.error(f"Klaida generuojant flashcard'us: {error_type}")
        return []

def save_generated_cards(cards):
    """Save generated cards to session state and trigger success"""
    if cards:
        st.session_state.flashcards = cards
        st.session_state.flashcards_count += len(cards)
        st.session_state.current_card = 0
        add_cards_to_study(cards)
        st.session_state.generation_success = len(cards)
        st.rerun()

# ==========================
# PDF EXTRACT
# ==========================

@st.cache_data
def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        clean_text = text.strip()
        if len(clean_text) < 50 and len(pdf_reader.pages) > 0:
            st.warning("Šis PDF atrodo skanuotas (be teksto sluoksnio). Naudokite Nuotraukos režimą.")
            return ""

        if len(text) > MAX_PDF_CHARS:
            truncated = text[:MAX_PDF_CHARS]
            last_period = truncated.rfind('.')
            if last_period > MAX_PDF_CHARS * 0.8:
                truncated = truncated[:last_period + 1]
            text = truncated
            st.warning(f"PDF tekstas apribotas iki ~{MAX_PDF_CHARS:,} simbolių")

        return text
    except Exception as e:
        st.error(f"Klaida skaitant PDF: {type(e).__name__}")
        return ""

# ==========================
# EXPORT FUNCTIONS
# ==========================

def export_to_anki_csv(flashcards):
    """Export flashcards to Anki-compatible CSV"""
    output = StringIO()
    writer = csv.writer(output, delimiter=';')
    for card in flashcards:
        writer.writerow([card['klausimas'], card['atsakymas']])
    return output.getvalue()

def export_to_quizlet_json(flashcards):
    """Export flashcards to Quizlet-compatible JSON"""
    quizlet_format = {
        "title": f"Flashcards - {datetime.now().strftime('%Y-%m-%d')}",
        "lang_terms": "lt",
        "lang_definitions": "lt",
        "terms": [
            {"term": card['klausimas'], "definition": card['atsakymas']}
            for card in flashcards
        ]
    }
    return json.dumps(quizlet_format, ensure_ascii=False, indent=2)

def export_to_txt(flashcards):
    """Export flashcards to simple TXT format"""
    output = ""
    for i, card in enumerate(flashcards, 1):
        output += f"{i}. {card['klausimas']}\n   → {card['atsakymas']}\n\n"
    return output

# ==========================
# UI LAYOUT
# ==========================

# Show success message from previous generation (survives st.rerun)
if st.session_state.generation_success > 0:
    st.balloons()
    st.success(f"Sukurta {st.session_state.generation_success} flashcard'ų!")
    st.session_state.generation_success = 0

# Header
st.title("📚 FlashCards AI")
st.markdown("**Automatiškai sukurk flashcard'us iš teksto ar PDF** | Powered by Gemini 2.0 Flash")

# Sidebar
with st.sidebar:
    theme = st.radio("Tema:", ["☀️ Šviesi", "🌙 Tamsi"], horizontal=True, label_visibility="collapsed")

    if theme == "🌙 Tamsi":
        st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)

    st.divider()
    st.header("Nustatymai")

    st.markdown("""**Kaip gauti Gemini API raktą:**
1. Eik į [aistudio.google.com](https://aistudio.google.com/apikey)
2. Prisijunk su Google paskyra
3. Sukurk naują API key
4. Įklijuok čia""")

    api_key = st.text_input(
        "Gemini API Key",
        value=os.getenv("GEMINI_API_KEY", ""),
        type="password",
        placeholder="AIza..."
    )

    st.divider()

    st.subheader("Jūsų limitas")
    remaining = max(0, DAILY_LIMIT - st.session_state.flashcards_count)
    progress = min(st.session_state.flashcards_count / DAILY_LIMIT, 1.0)
    st.progress(progress)
    st.caption(f"{st.session_state.flashcards_count}/{DAILY_LIMIT} flashcard'ų šiandien")

    if remaining == 0 and not st.session_state.is_premium:
        st.warning("Pasiekėte dienos limitą!")

    st.divider()
    st.caption("Made with ❤️ for LT students")
    st.caption(f"Powered by {GEMINI_MODEL}")

    with st.expander("Apie ir Privatumas"):
        st.caption("""
        **FlashCards AI v1.1**

        Šis įrankis naudoja dirbtinį intelektą medžiagai analizuoti.

        **Privatumas:**
        Jūsų įkelti failai ir tekstai nėra saugomi mūsų serveriuose.
        Jie siunčiami tik į Google Gemini API apdorojimui ir po to iškart ištrinami.
        """)

    st.markdown("---")
    st.markdown("Turite idėjų? [Susisiekite](mailto:petrovic222@gmail.com)")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["📝 Šaltinis", "🧠 Mokymasis", "🎴 Peržiūra", "💾 Eksportas"])

can_generate = st.session_state.flashcards_count < DAILY_LIMIT or st.session_state.is_premium

# ==================
# TAB 1: ŠALTINIS
# ==================
with tab1:
    st.header("Iš ko mokysimės šiandien?")

    source_type = st.radio(
        "Pasirinkite medžiagos tipą:",
        ["✍️ Tekstas", "📄 PDF Failas", "🎥 YouTube Video", "📸 Nuotrauka"],
        horizontal=True,
        label_visibility="collapsed"
    )

    st.divider()

    # ---- TEKSTAS ----
    if source_type == "✍️ Tekstas":
        col1, col2 = st.columns([3, 1])

        with col1:
            input_text = st.text_area(
                "Įklijuokite tekstą:",
                height=300,
                max_chars=MAX_INPUT_CHARS,
                placeholder="Kopijuokite paskaitų konspektą, vadovėlio skyrių ar savo užrašus..."
            )

        with col2:
            num_cards = st.slider("Kortelių kiekis:", 5, 20, 10, key="slider_text")
            language = st.selectbox("Kalba:", ["lietuvių", "anglų", "abi"])

            if st.button("🎯 Generuoti", type="primary", disabled=not input_text or not can_generate):
                if not api_key:
                    st.error("Įveskite Gemini API key!")
                else:
                    with st.spinner("Kuriami flashcard'ai..."):
                        cards = generate_flashcards_from_text(input_text, num_cards, language, api_key)
                        save_generated_cards(cards)

    # ---- PDF ----
    elif source_type == "📄 PDF Failas":
        uploaded_pdf = st.file_uploader(
            "Įkelkite PDF failą:",
            type=["pdf"],
            help="Veikia su tekstiniais PDF (ne skanuotomis nuotraukomis)"
        )

        if uploaded_pdf:
            with st.spinner("Skaitomas PDF..."):
                pdf_text = extract_text_from_pdf(uploaded_pdf)

            if pdf_text:
                st.info(f"Nuskaityta {len(pdf_text):,} simbolių")
                st.text_area("Peržiūra:", pdf_text[:500] + ("..." if len(pdf_text) > 500 else ""), height=150, disabled=True)

                num_cards_pdf = st.slider("Kortelių kiekis:", 5, 20, 10, key="slider_pdf")

                if st.button("🎯 Generuoti iš PDF", type="primary", disabled=not can_generate):
                    if not api_key:
                        st.error("Įveskite Gemini API key!")
                    else:
                        with st.spinner("Kuriami flashcard'ai iš PDF..."):
                            cards = generate_flashcards_from_text(pdf_text, num_cards_pdf, "lietuvių", api_key)
                            save_generated_cards(cards)

    # ---- YOUTUBE ----
    elif source_type == "🎥 YouTube Video":
        if not YOUTUBE_AVAILABLE:
            st.warning("YouTube funkcija neaktyvi. Įdiekite: `pip install youtube-transcript-api`")
        else:
            youtube_url = st.text_input(
                "YouTube nuoroda:",
                placeholder="https://www.youtube.com/watch?v=..."
            )

            # Clear old transcript if URL changed
            if youtube_url != st.session_state.last_youtube_url:
                st.session_state.last_youtube_url = youtube_url
                if 'youtube_transcript' in st.session_state:
                    del st.session_state.youtube_transcript

            if youtube_url:
                video_id = extract_video_id(youtube_url)

                if not video_id:
                    st.error("Neteisinga YouTube nuoroda")
                else:
                    st.image(f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg", width=400)

                    if st.button("🎬 Ekstraktuoti tekstą", type="primary"):
                        with st.spinner("Gaunami subtitrai..."):
                            result = get_youtube_transcript(video_id)

                        if result['success']:
                            st.session_state.youtube_transcript = result['text']
                            st.success(f"Ekstraktuota! Kalba: {result['language']}, Trukmė: {format_duration(result['duration'])}")
                        else:
                            st.error(result['error'])

            if 'youtube_transcript' in st.session_state:
                st.divider()
                transcript = st.session_state.youtube_transcript
                preview = transcript[:500] + ("..." if len(transcript) > 500 else "")
                st.text_area("Peržiūra:", preview, height=100, disabled=True)

                num_cards_yt = st.slider("Kortelių kiekis:", 5, 20, 10, key="slider_yt")

                if st.button("🎯 Generuoti iš YouTube", type="primary", disabled=not can_generate):
                    if not api_key:
                        st.error("Įveskite Gemini API key!")
                    else:
                        with st.spinner("Kuriami flashcard'ai..."):
                            cards = generate_flashcards_from_text(transcript, num_cards_yt, "lietuvių", api_key)
                            save_generated_cards(cards)

    # ---- NUOTRAUKA ----
    elif source_type == "📸 Nuotrauka":
        st.info("Nufotografuokite užrašus, lentą ar skaidrę ir įkelkite nuotrauką!")

        uploaded_image = st.file_uploader(
            "Įkelkite nuotrauką:",
            type=["jpg", "jpeg", "png", "webp"],
            help="Palaikomi formatai: JPG, PNG, WEBP"
        )

        if uploaded_image:
            image = Image.open(uploaded_image)
            st.image(image, caption="Jūsų nuotrauka", width=400)

            num_cards_img = st.slider("Kortelių kiekis:", 5, 20, 10, key="slider_img")

            if st.button("🎯 Generuoti iš nuotraukos", type="primary", disabled=not can_generate):
                if not api_key:
                    st.error("Įveskite Gemini API key!")
                else:
                    with st.spinner("Gemini analizuoja nuotrauką..."):
                        try:
                            client = get_gemini_client(api_key)

                            # Keep original format when possible
                            img_format = uploaded_image.type.split('/')[-1].upper()
                            if img_format == 'JPG':
                                img_format = 'JPEG'
                            if img_format not in ('JPEG', 'PNG', 'WEBP'):
                                img_format = 'PNG'

                            img_buffer = BytesIO()
                            image.save(img_buffer, format=img_format)
                            img_bytes = img_buffer.getvalue()

                            mime_type = f"image/{img_format.lower()}"
                            if img_format == 'JPEG':
                                mime_type = "image/jpeg"

                            prompt = f"""Tu esi ekspertas akademinis asistentas.

Išanalizuok šią nuotrauką (tai gali būti užrašai, lenta, skaidrė ar vadovėlis).
Sukurk {num_cards_img} flashcard'ų lietuvių kalba.

GRAŽINK TIK JSON ARRAY formatu:
[
  {{"klausimas": "...", "atsakymas": "..."}}
]"""

                            image_part = types.Part.from_bytes(
                                data=img_bytes,
                                mime_type=mime_type
                            )

                            response = client.models.generate_content(
                                model=GEMINI_MODEL,
                                contents=[prompt, image_part]
                            )

                            if not response.text:
                                st.error("Nepavyko atpažinti nuotraukos turinio. Bandykite aiškesnę nuotrauką.")
                            else:
                                cards = parse_flashcards_json(response.text)
                                if cards:
                                    save_generated_cards(cards)
                                else:
                                    st.error("Nepavyko sugeneruoti kortelių iš šios nuotraukos.")
                        except Exception as e:
                            error_type = type(e).__name__
                            if "timeout" in str(e).lower():
                                st.error("Užklausa užtruko per ilgai. Bandykite mažesnę nuotrauką.")
                            else:
                                st.error(f"Klaida analizuojant nuotrauką: {error_type}")

# ==================
# TAB 2: MOKYMASIS
# ==================
with tab2:
    st.header("🧠 Mokymasis (Spaced Repetition)")
    st.markdown("**Leitner sistema** - išmok efektyviau prisimenant tinkamu laiku!")

    today_cards = get_today_cards()
    total_study_cards = len(st.session_state.study_cards)

    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("Visos kortelės", total_study_cards)
    with col_stat2:
        st.metric("Šiandien kartoti", len(today_cards))
    with col_stat3:
        mastered = sum(1 for c in st.session_state.study_cards.values() if c.get('difficulty', 3) >= 4)
        st.metric("Įsisavintos", mastered)

    st.divider()

    if not st.session_state.study_cards:
        st.info("Pirmiausia sukurkite flashcard'us 'Šaltinis' tab'e!")

        st.subheader("Kaip veikia Spaced Repetition?")
        st.markdown("""
        1. **Sukurkite kortelę** - ji patenka į 1 dėžutę
        2. **Atsakykite teisingai** - kortelė pereina į kitą dėžutę (kartojimo intervalas ilgėja)
        3. **Atsakykite neteisingai** - kortelė grįžta į 1 dėžutę
        4. **5 dėžutė** = įsisavinta! (kartojama kas 14 dienų)
        """)
    elif not today_cards:
        st.success("Šiandien viskas pakartota! Grįžkite rytoj.")

        st.subheader("Jūsų progresas")
        for card_id, card_data in list(st.session_state.study_cards.items())[:5]:
            difficulty = card_data.get('difficulty', 3)
            st.markdown(f"**{html.escape(card_data['question'][:50])}...** - Dėžutė {difficulty}/5")
    else:
        card_data = today_cards[0]
        card_id = card_data['id']

        st.subheader(f"Kortelė {1}/{len(today_cards)}")

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea, #764ba2); padding: 30px; border-radius: 15px; color: white; margin: 20px 0;">
            <h3>{html.escape(card_data['question'])}</h3>
        </div>
        """, unsafe_allow_html=True)

        if st.button("👁️ Rodyti atsakymą", type="primary"):
            st.session_state.show_answer = True

        if st.session_state.show_answer:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #11998e, #38ef7d); padding: 30px; border-radius: 15px; color: white; margin: 20px 0;">
                <h3>{html.escape(card_data['answer'])}</h3>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("### Kaip sekėsi?")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("😰 Sunku", use_container_width=True):
                    update_card_difficulty(card_id, 1)
                    st.session_state.show_answer = False
                    st.rerun()

            with col2:
                if st.button("🤔 Vidutiniškai", use_container_width=True):
                    update_card_difficulty(card_id, 3)
                    st.session_state.show_answer = False
                    st.rerun()

            with col3:
                if st.button("😎 Lengva", use_container_width=True):
                    update_card_difficulty(card_id, 5)
                    st.session_state.show_answer = False
                    st.rerun()

# ==================
# TAB 3: PERŽIŪRA
# ==================
with tab3:
    st.header("🎴 Peržiūrėk flashcard'us")

    if not st.session_state.flashcards:
        st.info("Pirmiausia sukurkite flashcard'us 'Šaltinis' tab'e!")
    else:
        cards = st.session_state.flashcards
        total = len(cards)

        # Clamp current_card to valid range
        if st.session_state.current_card >= total:
            st.session_state.current_card = total - 1
        current = st.session_state.current_card

        st.progress((current + 1) / total)
        st.caption(f"Kortelė {current + 1} iš {total}")

        card = cards[current]
        q_escaped = html.escape(card['klausimas'])
        a_escaped = html.escape(card['atsakymas'])

        st.markdown(f"""
        <div class="flip-card" onclick="this.querySelector('.flip-card-inner').classList.toggle('flipped')">
            <div class="flip-card-inner">
                <div class="flip-card-front">
                    <p><strong>Klausimas:</strong><br>{q_escaped}</p>
                </div>
                <div class="flip-card-back">
                    <p><strong>Atsakymas:</strong><br>{a_escaped}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.caption("Desktop: užvesk pelę | Mobile: bakstelėk kortelę")

        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            if st.button("⬅️ Atgal", disabled=current == 0):
                st.session_state.current_card -= 1
                st.rerun()

        with col3:
            if st.button("Pirmyn ➡️", disabled=current == total - 1):
                st.session_state.current_card += 1
                st.rerun()

        st.divider()
        st.subheader("Redaguoti korteles")

        for i, c in enumerate(cards):
            label = f"**{i+1}. {html.escape(c['klausimas'][:50])}{'...' if len(c['klausimas']) > 50 else ''}**"
            with st.expander(label):
                new_q = st.text_input("Klausimas:", c['klausimas'], key=f"q_{i}")
                new_a = st.text_area("Atsakymas:", c['atsakymas'], key=f"a_{i}", height=100)

                if st.button("💾 Išsaugoti", key=f"save_{i}"):
                    st.session_state.flashcards[i] = {"klausimas": new_q, "atsakymas": new_a}
                    st.success("Išsaugota!")

# ==================
# TAB 4: EKSPORTAS
# ==================
with tab4:
    st.header("💾 Eksportuoti flashcard'us")

    if not st.session_state.flashcards:
        st.info("Pirmiausia sukurkite flashcard'us!")
    else:
        st.success(f"Turite {len(st.session_state.flashcards)} flashcard'ų paruoštų eksportui")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("Anki")
            st.caption("Importuokite į Anki programą")
            st.download_button(
                label="⬇️ CSV (Anki)",
                data=export_to_anki_csv(st.session_state.flashcards),
                file_name=f"flashcards_anki_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

        with col2:
            st.subheader("Quizlet")
            st.caption("Importuokite į Quizlet")
            st.download_button(
                label="⬇️ JSON (Quizlet)",
                data=export_to_quizlet_json(st.session_state.flashcards),
                file_name=f"flashcards_quizlet_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )

        with col3:
            st.subheader("Tekstas")
            st.caption("Paprastas TXT formatas")
            st.download_button(
                label="⬇️ TXT",
                data=export_to_txt(st.session_state.flashcards),
                file_name=f"flashcards_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )

        st.divider()
        st.subheader("Spausdinimui")

        html_table = """
        <style>
            @media print { .page-break { page-break-after: always; } }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            td, th { border: 1px solid #333; padding: 15px; }
            th { background-color: #667eea; color: white; }
        </style>
        <h2>Mano Kortelės</h2>
        <table>
            <tr><th>Klausimas</th><th>Atsakymas</th></tr>
        """
        for c in st.session_state.flashcards:
            html_table += f"<tr><td>{html.escape(c['klausimas'])}</td><td>{html.escape(c['atsakymas'])}</td></tr>"
        html_table += "</table>"

        st.download_button(
            "⬇️ Atsisiųsti HTML (Spausdinimui)",
            html_table,
            "korteles_print.html",
            "text/html"
        )
        st.caption("Atsisiuntę failą, atidarykite jį naršyklėje ir spauskite CTRL+P")

        st.divider()
        st.subheader("Peržiūra")
        for i, card in enumerate(st.session_state.flashcards, 1):
            st.markdown(f"**{i}. {html.escape(card['klausimas'])}**")
            st.caption(f"↳ {html.escape(card['atsakymas'])}")
