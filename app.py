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

# Load environment variables IMMEDIATELY
load_dotenv()
from PIL import Image
from io import BytesIO

# Supabase integration
try:
    from supabase_client import (
        sign_in_with_email, sign_up_with_email, sign_out,
        save_flashcard_set, load_user_flashcards, update_card_progress,
        get_cards_for_review, delete_flashcard_set,
        export_user_data, delete_user_account,
        get_user_premium_status, set_user_premium_status, get_user_profile
    )
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Stripe integration
try:
    from stripe_integration import (
        create_checkout_session, verify_stripe_session,
        cancel_subscription, get_subscription_status
    )
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False

# YouTube transcript support
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled, NoTranscriptFound,
        VideoUnavailable, IpBlocked, RequestBlocked
    )
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False

# ===========================
# CONSTANTS
# ===========================
GEMINI_MODEL = "gemini-2.0-flash"
DAILY_LIMIT = 20
SR_INTERVALS = {1: 1, 2: 1, 3: 3, 4: 7, 5: 14}  # difficulty -> days

# Character limits
MAX_PDF_CHARS_FREE = 50000
MAX_INPUT_CHARS_FREE = 50000
MAX_TRANSCRIPT_CHARS_FREE = 50000
MAX_PREMIUM_CHARS = 200000   # 💎 Premium: viso skyriaus ar knygos lygis

def get_limit(limit_type):
    """Return limit based on premium status"""
    is_premium = st.session_state.get('is_premium', False)
    if limit_type == 'chars':
        return MAX_PREMIUM_CHARS if is_premium else MAX_INPUT_CHARS_FREE
    if limit_type == 'daily':
        return 500 if is_premium else DAILY_LIMIT
    return 0

# Page config
st.set_page_config(
    page_title="FlashCards AI - Lietuvių studentams",
    page_icon="📚",
    layout="wide"
)

# Custom CSS — mobile-first responsive design
st.markdown("""
<style>
/* ===== FLIP CARDS ===== */
.flip-card {
    background-color: transparent;
    width: 100%;
    min-height: 200px;
    perspective: 1000px;
    margin: 16px 0;
}
.flip-card-inner {
    position: relative;
    width: 100%;
    min-height: 200px;
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
    min-height: 200px;
    -webkit-backface-visibility: hidden;
    backface-visibility: hidden;
    border-radius: 15px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    font-size: 1.1em;
    line-height: 1.5;
    word-wrap: break-word;
    overflow-wrap: break-word;
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

/* ===== STUDY CARDS (Mokymasis tab) ===== */
.study-card {
    padding: 24px 20px;
    border-radius: 15px;
    color: white;
    margin: 12px 0;
    word-wrap: break-word;
    overflow-wrap: break-word;
    line-height: 1.5;
}
.study-card h3 {
    margin: 0;
    font-size: 1.2em;
    line-height: 1.4;
}
.study-card-q { background: linear-gradient(135deg, #667eea, #764ba2); }
.study-card-a { background: linear-gradient(135deg, #11998e, #38ef7d); }

/* ===== MOBILE OPTIMIZATIONS ===== */
@media (max-width: 768px) {
    /* Bigger touch targets */
    .stButton > button {
        min-height: 48px !important;
        font-size: 1rem !important;
        padding: 10px 16px !important;
    }

    /* Tabs: scrollable, bigger touch area */
    .stTabs [data-baseweb="tab"] {
        padding: 12px 8px !important;
        font-size: 0.85rem !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0 !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
    }

    /* Wider inputs */
    .stTextInput input, .stTextArea textarea {
        font-size: 16px !important; /* prevents iOS zoom on focus */
    }

    /* Smaller flip cards on mobile */
    .flip-card, .flip-card-inner, .flip-card-front, .flip-card-back {
        min-height: 180px;
    }
    .flip-card-front, .flip-card-back {
        padding: 16px;
        font-size: 1em;
    }

    /* Study cards responsive */
    .study-card {
        padding: 20px 16px;
    }
    .study-card h3 {
        font-size: 1.05em;
    }

    /* Metrics compact */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
    }

    /* File uploader - bigger drag area */
    [data-testid="stFileUploader"] {
        min-height: 100px;
    }
    [data-testid="stFileUploader"] section {
        padding: 20px !important;
    }

    /* Radio buttons (source type) - wrap nicely */
    .stRadio > div {
        flex-wrap: wrap !important;
        gap: 4px !important;
    }
    .stRadio > div > label {
        padding: 8px 12px !important;
        font-size: 0.9rem !important;
    }

    /* Header text */
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }

    /* Expander touch target */
    .streamlit-expanderHeader {
        min-height: 44px !important;
        font-size: 0.95rem !important;
    }
}

/* Extra small screens (iPhone SE, etc) */
@media (max-width: 380px) {
    .flip-card, .flip-card-inner, .flip-card-front, .flip-card-back {
        min-height: 160px;
    }
    .flip-card-front, .flip-card-back {
        padding: 12px;
        font-size: 0.9em;
    }
    .study-card { padding: 16px 12px; }
    .study-card h3 { font-size: 1em; }
    h1 { font-size: 1.4rem !important; }
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
    .flip-card-front, .study-card-q { background: linear-gradient(135deg, #1a1f35 0%, #2d1f3d 100%) !important; }
    .flip-card-back, .study-card-a { background: linear-gradient(135deg, #0d2818 0%, #1a3d2e 100%) !important; }
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
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []
if 'chat_card_context' not in st.session_state:
    st.session_state.chat_card_context = None
if 'user' not in st.session_state:
    st.session_state.user = None
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = 'login'

# Handle Stripe Redirect (after successful payment)
if STRIPE_AVAILABLE and 'session_id' in st.query_params:
    session_id = st.query_params['session_id']
    # Prevent replay: check if already processed
    if session_id != st.session_state.get('processed_session_id'):
        payment = verify_stripe_session(session_id)
        if payment:
            if st.session_state.user and SUPABASE_AVAILABLE:
                set_user_premium_status(
                    st.session_state.user['id'],
                    True,
                    subscription_id=payment.get('subscription_id'),
                    stripe_customer_id=payment.get('customer_id')
                )
                st.session_state.is_premium = True
                st.session_state.subscription_id = payment.get('subscription_id')
                st.session_state.processed_session_id = session_id
                st.success("Sveikiname! Dabar esate Premium narys!")
                st.query_params.clear()
            else:
                # Save payment info so it can be activated after login
                st.session_state.pending_payment = payment
                st.warning("Apmokėjimas sėkmingas! Prisijunkite, kad Premium būtų aktyvuotas.")
    else:
        st.query_params.clear()

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
    """Extract 11-character YouTube video ID (FOOLPROOF VERSION)"""
    if not youtube_url:
        return None
        
    # Standard 11-character regex for YouTube IDs
    id_pattern = r'([0-9A-Za-z_-]{11})'
    
    # Try common URL patterns first
    patterns = [
        r'v=' + id_pattern,
        r'embed/' + id_pattern,
        r'youtu\.be/' + id_pattern,
        r'shorts/' + id_pattern
    ]
    
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
            
    # Final fallback: just look for ANY 11-char string that looks like an ID
    # avoiding common words and domain parts
    potential_ids = re.findall(id_pattern, youtube_url)
    for pid in potential_ids:
        if pid not in ['youtube', 'watch', 'embed', 'shorts']:
            return pid
            
    return None

def get_youtube_transcript(video_id, languages=['lt', 'en']):
    """Fetch transcript from YouTube video (v1.2 API)"""
    if not YOUTUBE_AVAILABLE:
        return {'success': False, 'error': 'YouTube funkcija šiuo metu neprieinama'}

    try:
        api = YouTubeTranscriptApi()
        result = api.fetch(video_id, languages=languages)

        if not result.snippets:
            return {'success': False, 'error': 'Šiam video nėra subtitrų'}

        full_text = " ".join([s.text for s in result.snippets])
        last = result.snippets[-1]
        duration = last.start + last.duration

        # Limit transcript length
        if len(full_text) > MAX_TRANSCRIPT_CHARS_FREE:
            full_text = full_text[:MAX_TRANSCRIPT_CHARS_FREE]

        return {
            'success': True,
            'text': full_text,
            'language': result.language_code,
            'duration': duration,
            'segments': len(result.snippets)
        }
    except TranscriptsDisabled:
        return {'success': False, 'error': 'Subtitrai išjungti šiam video'}
    except NoTranscriptFound:
        # Fallback: try just English
        try:
            api = YouTubeTranscriptApi()
            result = api.fetch(video_id, languages=['en'])
            full_text = " ".join([s.text for s in result.snippets])
            return {
                'success': True,
                'text': full_text,
                'language': 'en (auto)',
                'duration': result.snippets[-1].start + result.snippets[-1].duration if result.snippets else 0,
                'segments': len(result.snippets)
            }
        except Exception:
            return {'success': False, 'error': 'Šiam video nerasta jokių subtitrų'}
    except VideoUnavailable:
        return {'success': False, 'error': 'Video neprieinamas. Gali būti privatus arba ištrintas.'}
    except (IpBlocked, RequestBlocked):
        return {
            'success': False,
            'error': "YouTube subtitrai neprieinami iš serverio. Patarimas: atidarykite video, įjunkite subtitrus (CC), nukopijuokite tekstą ir įklijuokite į Tekstas skiltį."
        }
    except Exception:
        return {'success': False, 'error': 'Nepavyko gauti subtitrų. Pabandykite kitą video.'}

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

def sync_flashcards_from_supabase(user_id):
    """Sync data from Supabase to local session state"""
    result = load_user_flashcards(user_id)
    if result['success']:
        # Update flashcards list
        st.session_state.flashcards = result['cards']
        
        # Update study_cards for Leitner system
        new_study_cards = {}
        for card in result['cards']:
            # Use database ID as key
            card_id = card.get('id')
            if card_id:
                new_study_cards[card_id] = {
                    "id": card_id,
                    "question": card.get("klausimas", ""),
                    "answer": card.get("atsakymas", ""),
                    "next_review": card.get("next_review", datetime.now().isoformat()),
                    "difficulty": card.get("difficulty", 3),
                    "times_reviewed": card.get("times_reviewed", 0)
                }
        st.session_state.study_cards = new_study_cards
        return True
    return False

def add_cards_to_study(flashcards, db_ids=None):
    """Add generated flashcards to study deck with SR metadata.
    Uses database IDs when available so Supabase sync works correctly."""
    for i, card in enumerate(flashcards):
        # Use database ID if available, otherwise generate local ID
        if db_ids and i < len(db_ids):
            card_id = str(db_ids[i])
        else:
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

        # Sync with Supabase only if card has a DB ID (not local card_* format)
        if st.session_state.user and SUPABASE_AVAILABLE and not card_id.startswith("card_"):
            update_card_progress(card_id, difficulty)

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
        st.error("Pirmiausia įveskite API raktą nustatymuose (kairėje).")
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
{text[:get_limit('chars')]}

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
            st.error("Nepavyko apdoroti teksto. Pabandykite su trumpesniu tekstu.")
            return []

        return parse_flashcards_json(response.text)

    except Exception as e:
        err = str(e).lower()
        if "quota" in err or "429" in err:
            st.error("Serveris šiuo metu užimtas. Palaukite minutę ir bandykite dar kartą.")
        elif "timeout" in err:
            st.error("Užtruko per ilgai. Pabandykite su trumpesniu tekstu.")
        elif "invalid" in err and "key" in err:
            st.error("Neteisingas API raktas. Patikrinkite nustatymuose ir bandykite dar kartą.")
        else:
            st.error("Nepavyko sukurti kortelių. Bandykite dar kartą arba su kitu tekstu.")
        return []

def save_generated_cards(cards):
    """Save generated cards to session state and trigger success"""
    if cards:
        db_card_ids = []

        # Save to Supabase if logged in
        if st.session_state.user and SUPABASE_AVAILABLE:
            with st.spinner("Išsaugoma..."):
                set_name = f"Rinkinys {datetime.now().strftime('%m-%d %H:%M')}"
                result = save_flashcard_set(st.session_state.user['id'], set_name, cards)
                if result.get('success'):
                    db_card_ids = result.get('card_ids', [])

        st.session_state.flashcards = cards
        st.session_state.flashcards_count += len(cards)
        st.session_state.current_card = 0
        add_cards_to_study(cards, db_card_ids)
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
            st.warning("Atrodo, kad šis PDF yra skanuotas vaizdas. Pabandykite naudoti Nuotraukos režimą.")
            return ""

        if len(text) > MAX_PDF_CHARS_FREE:
            truncated = text[:MAX_PDF_CHARS_FREE]
            last_period = truncated.rfind('.')
            if last_period > MAX_PDF_CHARS_FREE * 0.8:
                truncated = truncated[:last_period + 1]
            text = truncated
            st.info("Nuskaitytas maksimalus teksto kiekis iš PDF.")

        return text
    except Exception:
        st.error("Nepavyko nuskaityti PDF. Patikrinkite, ar failas neapribotas slaptažodžiu.")
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
    st.success(f"Paruošta {st.session_state.generation_success} kortelių! Galite pradėti mokytis.")
    st.session_state.generation_success = 0

# Header
st.title("📚 FlashCards AI")
st.markdown("**Mokykis greičiau ir protingiau** — sukurk korteles iš bet kokios medžiagos per kelias sekundes")

# Sidebar
with st.sidebar:
    theme = st.radio("Tema:", ["☀️ Šviesi", "🌙 Tamsi"], horizontal=True, label_visibility="collapsed")

    if theme == "🌙 Tamsi":
        st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)

    st.divider()
    
    # ==================
    # AUTHENTICATION UI
    # ==================
    if SUPABASE_AVAILABLE:
        st.header("👤 Paskyra")
        
        if st.session_state.user:
            # User is logged in
            st.success(f"Sveiki, {st.session_state.user['email']}!")
            st.caption("Jūsų kortelės saugomos automatiškai")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Atnaujinti", use_container_width=True):
                    if sync_flashcards_from_supabase(st.session_state.user['id']):
                        st.success("Atnaujinta!")
                        st.rerun()
                    else:
                        st.error("Nepavyko atnaujinti. Bandykite dar kartą.")
            with col2:
                if st.button("🚪 Atsijungti", use_container_width=True):
                    sign_out()
                    st.session_state.user = None
                    st.session_state.flashcards = []
                    st.session_state.study_cards = {}
                    st.rerun()

            # BDAR: Data export + Account deletion
            with st.expander("🔒 Mano duomenys ir privatumas"):
                st.caption("Jūs turite visišką kontrolę savo duomenims:")

                # Data export (Art. 20) - direct download button
                export_result = export_user_data(
                    st.session_state.user['id'],
                    st.session_state.user['email']
                )
                if export_result.get('success'):
                    st.download_button(
                        "📥 Eksportuoti mano duomenis",
                        json.dumps(export_result['data'], ensure_ascii=False, indent=2, default=str),
                        f"mano_duomenys_{datetime.now().strftime('%Y%m%d')}.json",
                        "application/json",
                        use_container_width=True
                    )

                st.divider()

                # Account deletion (Art. 17)
                st.markdown("**Ištrinti paskyrą**")
                st.caption("Tai negrįžtamas veiksmas — visos kortelės ir paskyra bus ištrinti.")
                delete_confirm = st.text_input(
                    "Įveskite DELETE kad patvirtintumėte:",
                    key="delete_confirm",
                    placeholder="DELETE"
                )
                if st.button("🗑️ Ištrinti paskyrą visam laikui", type="primary", use_container_width=True):
                    if delete_confirm == "DELETE":
                        with st.spinner("Trinami duomenys..."):
                            result = delete_user_account(st.session_state.user['id'])
                            if result['success']:
                                st.session_state.user = None
                                st.session_state.is_premium = False
                                st.session_state.flashcards = []
                                st.session_state.study_cards = {}
                                st.success("Paskyra ir visi duomenys ištrinti.")
                                st.rerun()
                            else:
                                st.error("Kažkas nepavyko. Parašykite mums ir padėsime.")
                    else:
                        st.warning("Įveskite DELETE kad patvirtintumėte")

            st.divider()
            
            # Premium Section
            if not st.session_state.is_premium and STRIPE_AVAILABLE:
                st.markdown("### 💎 Premium planas")
                st.markdown("**€3.99/mėn**")
                st.write("- Neriboti kortelių kūrimai")
                st.write("- Ilgesni tekstai ir dideli failai")
                st.write("- Greitesnis apdorojimas")

                if st.button("💎 Tapti Premium", type="primary", use_container_width=True):
                    result = create_checkout_session(st.session_state.user['email'])
                    if result and isinstance(result, dict) and result.get('url'):
                        st.session_state.checkout_url = result['url']
                    else:
                        st.error("Nepavyko prisijungti prie mokėjimo sistemos. Bandykite vėliau.")

                if 'checkout_url' in st.session_state:
                    st.info("Viskas paruošta!")
                    st.link_button("💳 Pereiti prie apmokėjimo", st.session_state.checkout_url, use_container_width=True)
                    st.caption("Apmokėjus būsite automatiškai grąžinti atgal.")

            elif st.session_state.is_premium:
                st.success("💎 Premium narys")
                # Subscription management
                sub_id = st.session_state.get('subscription_id')
                if sub_id and STRIPE_AVAILABLE:
                    sub_info = get_subscription_status(sub_id)
                    if sub_info:
                        if sub_info.get('cancel_at_period_end'):
                            end_ts = sub_info.get('current_period_end', 0)
                            end_date = datetime.fromtimestamp(end_ts).strftime('%Y-%m-%d') if end_ts else '?'
                            st.caption(f"Premium galios iki {end_date}")
                        else:
                            if st.button("Atšaukti prenumeratą", use_container_width=True):
                                result = cancel_subscription(sub_id)
                                if result.get('success'):
                                    end_ts = result.get('cancel_at', 0)
                                    end_date = datetime.fromtimestamp(end_ts).strftime('%Y-%m-%d') if end_ts else '?'
                                    st.info(f"Prenumerata atšaukta. Premium galios iki {end_date}")
                                else:
                                    st.error("Kažkas nepavyko. Parašykite mums ir padėsime.")
        else:
            # Login/Signup forms
            st.write("---")
            auth_tab = st.radio("Paskyros veiksmas:", ["Prisijungti", "Registruotis"], horizontal=True, label_visibility="collapsed")
            
            email = st.text_input("El. paštas", key="auth_email", placeholder="studentas@email.com")
            password = st.text_input("Slaptažodis", type="password", key="auth_pass", placeholder="••••••••")
            
            if auth_tab == "Prisijungti":
                if st.button("🔐 Prisijungti", use_container_width=True):
                    if email and password:
                        result = sign_in_with_email(email, password)
                        if result['success']:
                            st.session_state.user = {
                                'id': str(result['user'].id),
                                'email': result['user'].email
                            }
                            # Load profile (premium, subscription)
                            if SUPABASE_AVAILABLE:
                                profile = get_user_profile(st.session_state.user['id'])
                                st.session_state.is_premium = profile.get('is_premium', False)
                                st.session_state.subscription_id = profile.get('subscription_id')

                            # Activate pending payment (paid before login)
                            if 'pending_payment' in st.session_state and SUPABASE_AVAILABLE:
                                pp = st.session_state.pending_payment
                                set_user_premium_status(
                                    st.session_state.user['id'], True,
                                    subscription_id=pp.get('subscription_id'),
                                    stripe_customer_id=pp.get('customer_id')
                                )
                                st.session_state.is_premium = True
                                st.session_state.subscription_id = pp.get('subscription_id')
                                del st.session_state.pending_payment

                            # Load user's flashcards and study history
                            sync_flashcards_from_supabase(st.session_state.user['id'])
                            st.success("Sveiki sugrįžę!")
                            st.rerun()
                        else:
                            err = result.get('error', '').lower()
                            if "email not confirmed" in err:
                                st.error("El. paštas dar nepatvirtintas. Patikrinkite savo pašto dėžutę (ir Spam aplanką).")
                            elif "invalid login credentials" in err:
                                st.error("Neteisingas el. paštas arba slaptažodis. Bandykite dar kartą.")
                            else:
                                st.error("Prisijungti nepavyko. Patikrinkite duomenis ir bandykite dar kartą.")
                    else:
                        st.warning("Įveskite el. paštą ir slaptažodį")
            else:
                gdpr_consent = st.checkbox(
                    "Sutinku su [Privatumo politika](#privatumo-politika) ir duomenų tvarkymu (BDAR)",
                    key="gdpr_consent"
                )
                if st.button("📝 Registruotis", use_container_width=True):
                    if not gdpr_consent:
                        st.warning("Privalote sutikti su privatumo politika")
                    elif not email or not password:
                        st.warning("Įveskite el. paštą ir slaptažodį")
                    elif len(password) < 6:
                        st.warning("Slaptažodis per trumpas (min 6 simboliai)")
                    else:
                        result = sign_up_with_email(email, password)
                        if result['success']:
                            st.success("Registracija sėkminga! Patikrinkite el. paštą ir patvirtinkite paskyrą.")
                        else:
                            st.error("Registracija nepavyko. Galbūt šis el. paštas jau užregistruotas?")

            st.caption("💡 Prisijungę kortelės bus pasiekiamos iš bet kurio įrenginio")
    
    st.divider()
    st.header("Nustatymai")

    st.markdown("""**Kaip pradėti naudoti?**
1. Eik į [aistudio.google.com](https://aistudio.google.com/apikey)
2. Prisijunk su Google paskyra
3. Paspausk 'Create API key'
4. Nukopijuok ir įklijuok čia""")

    api_key = st.text_input(
        "API raktas",
        value=os.getenv("GEMINI_API_KEY", ""),
        type="password",
        placeholder="Įklijuokite raktą čia..."
    )

    st.divider()

    st.subheader("Šiandienos progresas")
    current_limit = get_limit('daily')
    remaining = max(0, current_limit - st.session_state.flashcards_count)
    progress = min(st.session_state.flashcards_count / current_limit, 1.0)
    st.progress(progress)
    st.caption(f"Sukurta {st.session_state.flashcards_count} iš {current_limit} kortelių")

    if remaining == 0 and not st.session_state.is_premium:
        st.warning("Dienos limitas pasiektas. Tapkite Premium nariu ir kurkite neribotai!")

    st.divider()
    st.caption("Sukurta su ❤️ Lietuvos studentams")

    with st.expander("Privatumo politika (BDAR)"):
        st.markdown("""
<a name="privatumo-politika"></a>
**FlashCards AI — Privatumo politika**
*Atnaujinta: 2025-02-07*

**1. Duomenų valdytojas**
FlashCards AI, el. paštas: petrovic222@gmail.com

**2. Kokie duomenys renkami**
- **Paskyros duomenys:** el. pašto adresas, užšifruotas slaptažodis
- **Mokymosi duomenys:** jūsų sukurtos kortelės (klausimai/atsakymai), mokymosi progresas
- **Laikini duomenys:** įkelti tekstai, PDF, nuotraukos (apdorojami ir iškart ištrinami)

**3. Duomenų tvarkymo tikslai ir pagrindas**
- Paskyros sukūrimas ir autentifikacija — *sutikimas (BDAR 6 str. 1 d. a)*
- Kortelių saugojimas ir sinchronizavimas — *sutarties vykdymas (BDAR 6 str. 1 d. b)*
- AI turinio generavimas — *sutarties vykdymas (BDAR 6 str. 1 d. b)*

**4. Trečiosios šalys (duomenų tvarkytojai)**
| Paslauga | Paskirtis | Vieta |
|---|---|---|
| **Supabase** (supabase.com) | Duomenų saugojimas, autentifikacija | EU/US |
| **Google Gemini API** | AI turinio generavimas | US |
| **Streamlit Cloud** | Programos talpinimas | US |

Įkelti tekstai, PDF ir nuotraukos siunčiami į Google Gemini API tik apdorojimui — jie **nesaugomi** mūsų serveriuose.

**5. Duomenų saugojimo terminas**
- Paskyros duomenys: kol paskyra aktyvi arba kol paprašysite ištrinti
- Kortelės: kol paskyra aktyvi arba kol ištrinsite
- Laikini duomenys (tekstai, PDF, nuotraukos): ištrinami iškart po apdorojimo

**6. Jūsų teisės pagal BDAR**
- **Teisė susipažinti** (15 str.) — galite peržiūrėti savo duomenis
- **Teisė ištaisyti** (16 str.) — galite redaguoti korteles
- **Teisė ištrinti** (17 str.) — galite ištrinti paskyrą ir visus duomenis
- **Teisė į duomenų perkeliamumą** (20 str.) — galite eksportuoti duomenis JSON formatu
- **Teisė atšaukti sutikimą** — bet kada galite ištrinti paskyrą

Šias teises galite įgyvendinti per programos sąsają (Paskyra → Mano duomenys) arba rašydami el. paštu.

**7. Slapukai**
Ši programa nenaudoja slapukų (cookies). Sesijos duomenys saugomi tik serverio atmintyje ir ištrinami uždarius naršyklę.

**8. Skundai**
Turite teisę pateikti skundą Valstybinei duomenų apsaugos inspekcijai (vdai.lrv.lt).
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("Turite klausimų ar idėjų? [Parašykite mums](mailto:petrovic222@gmail.com)")

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Naujos kortelės", "🧠 Mokymasis", "🎴 Peržiūra", "💾 Atsisiuntimas", "💬 Paklausti AI"])

can_generate = st.session_state.flashcards_count < get_limit('daily')

# ==================
# TAB 1: ŠALTINIS
# ==================
with tab1:
    st.header("Iš ko norite sukurti korteles?")

    source_type = st.radio(
        "Pasirinkite medžiagos tipą:",
        ["✍️ Tekstas", "📄 PDF Failas", "🎥 YouTube Video", "📸 Nuotrauka"],
        horizontal=True,
        label_visibility="collapsed"
    )

    st.divider()

    # ---- TEKSTAS ----
    if source_type == "✍️ Tekstas":
        input_text = st.text_area(
            "Įklijuokite tekstą:",
            height=250,
            max_chars=get_limit('chars'),
            placeholder="Kopijuokite paskaitų konspektą, vadovėlio skyrių ar savo užrašus..."
        )

        col_opt1, col_opt2, col_opt3 = st.columns([2, 2, 3])
        with col_opt1:
            num_cards = st.slider("Kiekis:", 5, 20, 10, key="slider_text")
        with col_opt2:
            language = st.selectbox("Kalba:", ["lietuvių", "anglų", "abi"])
        with col_opt3:
            st.write("")  # spacing
            if st.button("🎯 Generuoti korteles", type="primary", disabled=not input_text or not can_generate, use_container_width=True):
                if not api_key:
                    st.error("Pirmiausia įveskite API raktą nustatymuose (kairėje).")
                else:
                    with st.spinner("Kuriamos kortelės..."):
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
                st.info(f"PDF nuskaitytas sėkmingai ({len(pdf_text):,} simbolių)")
                st.text_area("Peržiūra:", pdf_text[:500] + ("..." if len(pdf_text) > 500 else ""), height=150, disabled=True)

                num_cards_pdf = st.slider("Kortelių kiekis:", 5, 20, 10, key="slider_pdf")

                if st.button("🎯 Generuoti iš PDF", type="primary", disabled=not can_generate, use_container_width=True):
                    if not api_key:
                        st.error("Pirmiausia įveskite API raktą nustatymuose (kairėje).")
                    else:
                        with st.spinner("Kuriamos kortelės iš PDF..."):
                            cards = generate_flashcards_from_text(pdf_text, num_cards_pdf, "lietuvių", api_key)
                            save_generated_cards(cards)

    # ---- YOUTUBE ----
    elif source_type == "🎥 YouTube Video":
        if not YOUTUBE_AVAILABLE:
            st.warning("YouTube funkcija šiuo metu neprieinama.")
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
                    st.image(f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg", use_container_width=True)

                    if st.button("🎬 Gauti subtitrus", type="primary", use_container_width=True):
                        with st.spinner("Skaitomi subtitrai..."):
                            result = get_youtube_transcript(video_id)

                        if result['success']:
                            st.session_state.youtube_transcript = result['text']
                            st.success(f"Subtitrai nuskaityti! Kalba: {result['language']}, trukmė: {format_duration(result['duration'])}")
                        else:
                            st.error(result['error'])

            if 'youtube_transcript' in st.session_state:
                st.divider()
                transcript = st.session_state.youtube_transcript
                preview = transcript[:500] + ("..." if len(transcript) > 500 else "")
                st.text_area("Peržiūra:", preview, height=100, disabled=True)

                num_cards_yt = st.slider("Kortelių kiekis:", 5, 20, 10, key="slider_yt")

                if st.button("🎯 Generuoti iš YouTube", type="primary", disabled=not can_generate, use_container_width=True):
                    if not api_key:
                        st.error("Pirmiausia įveskite API raktą nustatymuose (kairėje).")
                    else:
                        with st.spinner("Kuriamos kortelės..."):
                            cards = generate_flashcards_from_text(transcript, num_cards_yt, "lietuvių", api_key)
                            save_generated_cards(cards)

    # ---- NUOTRAUKA ----
    elif source_type == "📸 Nuotrauka":
        st.info("Nufotografuokite savo užrašus, lentą ar skaidrę — AI viską atpažins!")

        uploaded_image = st.file_uploader(
            "Įkelkite nuotrauką:",
            type=["jpg", "jpeg", "png", "webp"],
            help="Palaikomi formatai: JPG, PNG, WEBP"
        )

        if uploaded_image:
            image = Image.open(uploaded_image)
            st.image(image, caption="Įkelta nuotrauka", use_container_width=True)

            num_cards_img = st.slider("Kortelių kiekis:", 5, 20, 10, key="slider_img")

            if st.button("🎯 Generuoti iš nuotraukos", type="primary", disabled=not can_generate, use_container_width=True):
                if not api_key:
                    st.error("Pirmiausia įveskite API raktą nustatymuose (kairėje).")
                else:
                    with st.spinner("Analizuojama nuotrauka..."):
                        try:
                            client = get_gemini_client(api_key)

                            # Keep original format when possible
                            img_format = uploaded_image.type.split('/')[-1].upper()
                            if img_format == 'JPG':
                                img_format = 'JPEG'
                            if img_format not in ('JPEG', 'PNG', 'WEBP'):
                                img_format = 'PNG'

                            # Resize image if too large (max 1600px width/height)
                            # This helps avoid ClientError and speeds up processing
                            max_size = 1600
                            if image.width > max_size or image.height > max_size:
                                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                                st.caption("Nuotrauka optimizuota greitesniam apdorojimui")

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
                                st.error("Nepavyko atpažinti nuotraukos turinio. Pabandykite aiškesnę nuotrauką.")
                            else:
                                cards = parse_flashcards_json(response.text)
                                if cards:
                                    save_generated_cards(cards)
                                else:
                                    st.error("Nepavyko sukurti kortelių iš šios nuotraukos. Pabandykite kitą.")
                        except Exception as e:
                            if "timeout" in str(e).lower():
                                st.error("Užtruko per ilgai. Pabandykite mažesnę nuotrauką.")
                            else:
                                st.error("Nepavyko apdoroti nuotraukos. Bandykite dar kartą.")

# ==================
# TAB 2: MOKYMASIS
# ==================
with tab2:
    st.header("🧠 Mokymasis")
    st.markdown("**Kartok protingai** — sistema parinks, kurias korteles laikas pakartoti")

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
        st.info("Kol kas neturite kortelių. Sukurkite jas 'Naujos kortelės' skiltyje!")

        st.subheader("Kaip tai veikia?")
        st.markdown("""
        1. **Sukuriate korteles** — jos iškart patenka į mokymosi planą
        2. **Atsakote teisingai** — kortelė rodoma vis rečiau (nes jau mokate!)
        3. **Atsakote neteisingai** — kortelė grįžta kartoti dažniau
        4. **Įsisavinote** — kortelė kartojama tik kas 2 savaites
        """)
    elif not today_cards:
        st.success("Puiku! Šiandien viskas pakartota. Grįžkite rytoj!")

        st.subheader("Jūsų progresas")
        for card_id, card_data in list(st.session_state.study_cards.items())[:5]:
            difficulty = card_data.get('difficulty', 3)
            level = ["", "Naujas", "Pradžia", "Vidutinis", "Gerai moku", "Įsisavinta"][min(difficulty, 5)]
            st.markdown(f"**{html.escape(card_data['question'][:50])}...** — {level}")
    else:
        card_data = today_cards[0]
        card_id = card_data['id']

        st.subheader(f"Kortelė {1}/{len(today_cards)}")

        st.markdown(f"""
        <div class="study-card study-card-q">
            <h3>{html.escape(card_data['question'])}</h3>
        </div>
        """, unsafe_allow_html=True)

        if st.button("👁️ Rodyti atsakymą", type="primary", use_container_width=True):
            st.session_state.show_answer = True

        if st.session_state.show_answer:
            st.markdown(f"""
            <div class="study-card study-card-a">
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
    st.header("🎴 Jūsų kortelės")

    if not st.session_state.flashcards:
        st.info("Kol kas neturite kortelių. Sukurkite jas 'Naujos kortelės' skiltyje!")
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

        st.caption("Spauskite ant kortelės, kad pamatytumėte atsakymą")

        # TTS Audio - stored in session_state so it persists across reruns
        col_audio1, col_audio2 = st.columns(2)
        with col_audio1:
            if st.button("🔊 Klausyti klausimo", key="tts_q", use_container_width=True):
                try:
                    from gtts import gTTS
                    tts = gTTS(text=card['klausimas'], lang='lt')
                    audio_buffer = BytesIO()
                    tts.write_to_fp(audio_buffer)
                    st.session_state.tts_audio = audio_buffer.getvalue()
                    st.session_state.tts_card_idx = current
                except ImportError:
                    st.warning("Garso funkcija šiuo metu neprieinama.")
                except Exception:
                    st.error("Nepavyko paleisti garso. Bandykite dar kartą.")

        with col_audio2:
            if st.button("🔊 Klausyti atsakymo", key="tts_a", use_container_width=True):
                try:
                    from gtts import gTTS
                    tts = gTTS(text=card['atsakymas'], lang='lt')
                    audio_buffer = BytesIO()
                    tts.write_to_fp(audio_buffer)
                    st.session_state.tts_audio = audio_buffer.getvalue()
                    st.session_state.tts_card_idx = current
                except ImportError:
                    st.warning("Garso funkcija šiuo metu neprieinama.")
                except Exception:
                    st.error("Nepavyko paleisti garso. Bandykite dar kartą.")

        # Persistent audio player - stays visible until card changes
        if 'tts_audio' in st.session_state and st.session_state.get('tts_card_idx') == current:
            st.audio(st.session_state.tts_audio, format='audio/mp3')

        col_nav1, col_nav2 = st.columns(2)

        with col_nav1:
            if st.button("⬅️ Atgal", disabled=current == 0, use_container_width=True):
                st.session_state.current_card -= 1
                st.session_state.pop('tts_audio', None)
                st.rerun()

        with col_nav2:
            if st.button("Pirmyn ➡️", disabled=current == total - 1, use_container_width=True):
                st.session_state.current_card += 1
                st.session_state.pop('tts_audio', None)
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
    st.header("💾 Atsisiųsti korteles")

    if not st.session_state.flashcards:
        st.info("Kol kas neturite kortelių. Sukurkite jas ir galėsite atsisiųsti!")
    else:
        st.success(f"Turite {len(st.session_state.flashcards)} kortelių — galite atsisiųsti bet kuriuo formatu")

        col_dl1, col_dl2 = st.columns(2)

        with col_dl1:
            st.download_button(
                label="⬇️ Anki (CSV)",
                data=export_to_anki_csv(st.session_state.flashcards),
                file_name=f"flashcards_anki_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.download_button(
                label="⬇️ Quizlet (JSON)",
                data=export_to_quizlet_json(st.session_state.flashcards),
                file_name=f"flashcards_quizlet_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )

        with col_dl2:
            st.download_button(
                label="⬇️ Tekstas (TXT)",
                data=export_to_txt(st.session_state.flashcards),
                file_name=f"flashcards_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True
            )

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
                "⬇️ Spausdinimui (HTML)",
                html_table,
                "korteles_print.html",
                "text/html",
                use_container_width=True
            )

        st.divider()
        st.subheader("Peržiūra")
        for i, card in enumerate(st.session_state.flashcards, 1):
            st.markdown(f"**{i}. {html.escape(card['klausimas'])}**")
            st.caption(f"↳ {html.escape(card['atsakymas'])}")

# ==================
# TAB 5: AI TUTOR CHAT
# ==================
with tab5:
    st.header("💬 Paklausk AI — paaiškinsiu!")

    if not st.session_state.flashcards:
        st.info("Kol kas neturite kortelių. Sukurkite jas ir galėsite klausti AI apie bet kurią temą!")
    elif not api_key:
        st.warning("Norint kalbėtis su AI, reikia API rakto. Įveskite jį nustatymuose (kairėje).")
    else:
        # Card selector
        card_options = [f"{i+1}. {c['klausimas'][:50]}..." for i, c in enumerate(st.session_state.flashcards)]
        selected_idx = st.selectbox(
            "Pasirinkite kortelę, apie kurią norite klausti:",
            range(len(card_options)),
            format_func=lambda x: card_options[x]
        )
        
        selected_card = st.session_state.flashcards[selected_idx]
        
        # Show selected card context
        st.markdown(f"""
        <div class="study-card study-card-q" style="padding: 16px;">
            <strong>❓ {html.escape(selected_card['klausimas'])}</strong><br>
            <span style="opacity: 0.9;">✅ {html.escape(selected_card['atsakymas'])}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Reset chat if card changed
        if st.session_state.chat_card_context != selected_idx:
            st.session_state.chat_messages = []
            st.session_state.chat_card_context = selected_idx
        
        st.divider()
        
        # Display chat history
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])
        
        # Chat input
        user_question = st.chat_input("Paklauskite ko nors apie šią temą...")
        
        if user_question:
            # Add user message
            st.session_state.chat_messages.append({"role": "user", "content": user_question})
            st.chat_message("user").write(user_question)
            
            # Generate AI response
            with st.spinner("Ruošiu atsakymą..."):
                try:
                    client = get_gemini_client(api_key)
                    
                    # Build context from card + chat history
                    chat_history = "\n".join([
                        f"{'Studentas' if m['role'] == 'user' else 'AI Tutor'}: {m['content']}"
                        for m in st.session_state.chat_messages[:-1]  # Exclude current question
                    ])
                    
                    prompt = f"""Tu esi draugiškas AI tutorius, padedantis studentams suprasti medžiagą.

KONTEKSTAS (flashcard):
Klausimas: {selected_card['klausimas']}
Atsakymas: {selected_card['atsakymas']}

{"ANKSTESNIS POKALBIS:" + chr(10) + chat_history if chat_history else ""}

STUDENTO KLAUSIMAS: {user_question}

TAISYKLĖS:
1. Atsakyk lietuviškai, draugiškai ir aiškiai
2. Naudok analogijas ir pavyzdžius
3. Jei klausimas ne apie temą - mandagiai grąžink prie temos
4. Būk glaustus (2-4 sakiniai)
5. Naudok emoji kad būtų įdomiau 🎓

ATSAKYMAS:"""

                    response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=prompt
                    )
                    
                    ai_response = response.text.strip() if response.text else "Hmm, nepavyko parengti atsakymo. Pabandykite paklausti kitaip!"
                    
                    st.session_state.chat_messages.append({"role": "assistant", "content": ai_response})
                    st.chat_message("assistant").write(ai_response)
                    
                except Exception as e:
                    error_msg = "Nepavyko gauti atsakymo. Bandykite dar kartą."
                    if "quota" in str(e).lower() or "429" in str(e):
                        error_msg = "Serveris šiuo metu užimtas. Palaukite minutę ir bandykite dar kartą."
                    st.error(error_msg)
        
        # Clear chat button
        if st.session_state.chat_messages:
            if st.button("🗑️ Išvalyti pokalbį"):
                st.session_state.chat_messages = []
                st.rerun()

