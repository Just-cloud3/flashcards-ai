import streamlit as st
import time
import random
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
from streamlit_js_eval import streamlit_js_eval

# Supabase integration
try:
    from supabase_client import (
        sign_in_with_email, sign_up_with_email, sign_out,
        save_flashcard_set, load_user_flashcards, update_card_progress,
        get_cards_for_review, delete_flashcard_set,
        export_user_data, delete_user_account,
        get_user_premium_status, set_user_premium_status, get_user_profile,
        make_set_public, get_public_sets, clone_public_set, get_user_sets,
        change_password, change_email, update_display_name, reset_password,
        update_streak, get_streak
    )
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Stripe integration
try:
    from stripe_integration import (
        create_checkout_session, verify_stripe_session,
        cancel_subscription, get_subscription_status,
        create_billing_portal
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

# Admin
ADMIN_EMAILS = {"petrovic222@gmail.com"}

def is_admin():
    """Check if current user is admin"""
    user = st.session_state.get('user')
    return user and user.get('email', '').lower() in ADMIN_EMAILS

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
    page_title="QUANTUM — Išmanus mokymasis",
    page_icon="⚛️",
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
    margin-bottom: 2rem;
}

/* Glassmorphism Containers */
div[data-testid="stExpander"], .stChatMessage, .stTabs [data-baseweb="tab"] {
    background: var(--glass) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    backdrop-filter: blur(12px);
}

/* Custom Primary Buttons */
button[kind="primary"] {
    background: linear-gradient(135deg, #00f2ff, #0060ff) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px;
    box-shadow: 0 4px 20px rgba(0, 242, 255, 0.2) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

button[kind="primary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0, 242, 255, 0.4) !important;
}

/* Tabs UI */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: transparent;
}

.stTabs [data-baseweb="tab"] {
    padding: 10px 20px !important;
    color: #8b949e !important;
}

.stTabs [aria-selected="true"] {
    background: rgba(0, 242, 255, 0.1) !important;
    color: #00f2ff !important;
    border-bottom: 2px solid #00f2ff !important;
}

/* Metric & Alerts */
[data-testid="stMetricValue"] { color: #00f2ff !important; }
.stAlert { border-radius: 12px !important; border: 1px solid var(--border) !important; }

/* Flip Cards Premium */
.flip-card-front, .study-card-q {
    background: linear-gradient(135deg, #0f172a, #1e293b) !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
}
.flip-card-back, .study-card-a {
    background: linear-gradient(135deg, #064e3b, #065f46) !important;
}
</style>
""", unsafe_allow_html=True)

# Galaxy Theme CSS (Standard tamsusis režimas buvo pakeistas į šį premium stilių)
GALAXY_THEME_CSS = """
<style>
    /* 1. PAGRINDINIS FONAS (Andromedos Galaktika) */
    [data-testid="stAppViewContainer"] {
        background-image: 
            linear-gradient(rgba(0, 0, 0, 0.65), rgba(0, 0, 0, 0.65)), 
            url("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/M31_Andromeda_Galaxy_%28aerosnapper%29.jpg/2560px-M31_Andromeda_Galaxy_%28aerosnapper%29.jpg") !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
    }

    /* Priverstinis permatomumas pagrindiniams konteineriams */
    .stApp, [data-testid="stHeader"], [data-testid="stMain"], [data-testid="stSidebar"] {
        background: transparent !important;
    }

    /* 2. ŠONINIS MENIU (Sidebar) - Stiklo efektas (Glassmorphism) */
    [data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.8) !important;
        backdrop-filter: blur(12px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    }

    /* 3. TEKSTO IR ANTRAŠČIŲ PRITAIKYMAS */
    h1, h2, h3, h4, h5, h6, p, span, div, label, .stMarkdown, .stCaption {
        color: #FFFFFF !important;
        text-shadow: 0px 2px 4px rgba(0,0,0,0.6) !important;
    }
    
    /* Akronimo (QUANTUM) raidžių švytėjimas */
    .highlight {
        color: #00BFFF !important; 
        text-shadow: 0 0 15px rgba(0, 191, 255, 0.9), 0 0 5px rgba(255, 255, 255, 0.4) !important;
        font-weight: bold;
    }

    /* 4. MYGTUKAI - Kaip šviečiantys varikliai */
    div.stButton > button {
        background: linear-gradient(135deg, #00BFFF 0%, #4B0082 100%) !important; 
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        letter-spacing: 1px !important;
        transition: all 0.3s ease-in-out !important;
        box-shadow: 0 0 15px rgba(0, 191, 255, 0.4) !important;
    }

    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 0 25px rgba(0, 191, 255, 0.8), 0 0 50px rgba(0, 191, 255, 0.5) !important;
    }

    /* 5. ĮVESTIES LAUKAI */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: rgba(22, 27, 34, 0.7) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        backdrop-filter: blur(5px);
    }

    /* Tabs & Expander pritaikymas galaktikai */
    .stTabs [data-baseweb="tab-list"] { background-color: transparent !important; }
    .stTabs [data-baseweb="tab"] { color: #d1d5db !important; }
    .stTabs [aria-selected="true"] { color: #00BFFF !important; border-bottom-color: #00BFFF !important; }
    div[data-testid="stExpander"] { background-color: rgba(255, 255, 255, 0.05) !important; border-color: rgba(255, 255, 255, 0.1) !important; }

    /* Paslepiam elementus */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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
    # Try to restore login from browser localStorage
    stored_user = streamlit_js_eval(js_expressions="localStorage.getItem('quantum_user')")
    if stored_user and stored_user != 'null':
        try:
            user_data = json.loads(stored_user)
            if user_data and user_data.get('id') and user_data.get('email'):
                st.session_state.user = user_data
                # Restore premium status
                if SUPABASE_AVAILABLE:
                    profile = get_user_profile(user_data['id'])
                    st.session_state.is_premium = profile.get('is_premium', False)
                    st.session_state.subscription_id = profile.get('subscription_id')
                # Load flashcards
                sync_flashcards_from_supabase(user_data['id'])
                st.rerun()
        except (json.JSONDecodeError, Exception):
            pass  # Invalid stored data, ignore
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = 'login'
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = time.time()

# Auto-logout after 30 minutes of inactivity
SESSION_TIMEOUT = 30 * 60  # 30 minutes in seconds
if st.session_state.user:
    if time.time() - st.session_state.last_activity > SESSION_TIMEOUT:
        st.session_state.user = None
        st.session_state.flashcards = []
        st.session_state.study_cards = {}
        streamlit_js_eval(js_expressions="localStorage.removeItem('quantum_user')")
        st.toast("⏰ Sesija baigėsi dėl neaktyvumo. Prisijunkite iš naujo.")
        st.rerun()
    else:
        st.session_state.last_activity = time.time()

# Exam session state
if 'exam_active' not in st.session_state:
    st.session_state.exam_active = False
if 'exam_cards' not in st.session_state:
    st.session_state.exam_cards = []
if 'exam_current_idx' not in st.session_state:
    st.session_state.exam_current_idx = 0
if 'exam_results' not in st.session_state:
    st.session_state.exam_results = []
if 'exam_start_time' not in st.session_state:
    st.session_state.exam_start_time = None
if 'exam_show_answer' not in st.session_state:
    st.session_state.exam_show_answer = False
if 'exam_finished' not in st.session_state:
    st.session_state.exam_finished = False
if 'exam_total' not in st.session_state:
    st.session_state.exam_total = 0
if 'exam_time_limit' not in st.session_state:
    st.session_state.exam_time_limit = None

# Apply Galaxy Theme CSS only if dark_mode is True
if st.session_state.dark_mode:
    st.markdown(GALAXY_THEME_CSS, unsafe_allow_html=True)
else:
    # Optional: Force some standard light mode tweaks if needed
    st.markdown("""
    <style>
        .highlight { color: #0060ff !important; font-weight: bold; }
        #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

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
            update_streak(st.session_state.user['id'])

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
        st.error("API raktas nenustatytas. Susisiekite su administratoriumi arba bandykite vėliau.")
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
Sukuriame {num_cards} kortelių iš šio teksto {language} kalba.

TEKSTAS:
{text[:get_limit('chars')]}

GRĄŽINK TIK JSON ARRAY formatu (be jokio papildomo teksto):
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

# Sidebar (rendered BEFORE guest check so mobile users see login form)
with st.sidebar:
    # Logo & Brand
    st.image("assets/logo.png", use_container_width=True)
    st.caption("""<p style='text-align: center; font-family: monospace; letter-spacing: 1px;'>
        <span class="highlight">Q</span>uestion · <span class="highlight">U</span>nderstand · <span class="highlight">A</span>I · <span class="highlight">N</span>eural · <span class="highlight">T</span>hink · <span class="highlight">U</span>nified · <span class="highlight">M</span>emory
    </p>""", unsafe_allow_html=True)

    # Dark/Light mode toggle
    dark_on = st.toggle("🌙 Tamsusis režimas", value=st.session_state.dark_mode, key="dark_toggle")
    if dark_on != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_on
        st.rerun()

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
                    # Clear localStorage
                    streamlit_js_eval(js_expressions="localStorage.removeItem('quantum_user')")
                    st.rerun()

            # Account editing
            with st.expander("✏️ Redaguoti paskyrą"):
                # Display name
                current_profile = get_user_profile(st.session_state.user['id'])
                current_name = current_profile.get('display_name', '')

                new_name = st.text_input(
                    "Vardas / slapyvardis:",
                    value=current_name,
                    placeholder="Pvz. Jonas S.",
                    key="edit_display_name"
                )
                if st.button("💾 Išsaugoti vardą", use_container_width=True, key="save_name_btn"):
                    if new_name and new_name != current_name:
                        res = update_display_name(st.session_state.user['id'], new_name)
                        if res.get('success'):
                            st.success("Vardas atnaujintas!")
                        else:
                            st.error("Nepavyko atnaujinti vardo.")
                    elif not new_name:
                        st.warning("Įveskite vardą")

                st.divider()

                # Change email
                st.markdown("**Keisti el. paštą**")
                new_email = st.text_input(
                    "Naujas el. paštas:",
                    placeholder="naujas@email.com",
                    key="edit_email"
                )
                if st.button("📧 Keisti el. paštą", use_container_width=True, key="change_email_btn"):
                    if new_email and new_email != st.session_state.user['email']:
                        res = change_email(new_email)
                        if res.get('success'):
                            st.success("Patvirtinimo laiškas išsiųstas į naują el. paštą. Patikrinkite pašto dėžutę.")
                        else:
                            err = res.get('error', '').lower()
                            if 'already' in err or 'exists' in err:
                                st.error("Šis el. paštas jau užregistruotas.")
                            else:
                                st.error("Nepavyko pakeisti el. pašto. Bandykite vėliau.")
                    elif not new_email:
                        st.warning("Įveskite naują el. paštą")

                st.divider()

                # Change password
                st.markdown("**Keisti slaptažodį**")
                new_pass = st.text_input(
                    "Naujas slaptažodis:",
                    type="password",
                    placeholder="Min. 6 simboliai",
                    key="edit_new_pass"
                )
                new_pass_confirm = st.text_input(
                    "Pakartokite slaptažodį:",
                    type="password",
                    placeholder="••••••••",
                    key="edit_new_pass_confirm"
                )
                if st.button("🔑 Keisti slaptažodį", use_container_width=True, key="change_pass_btn"):
                    if not new_pass or not new_pass_confirm:
                        st.warning("Užpildykite abu laukus")
                    elif len(new_pass) < 6:
                        st.warning("Slaptažodis per trumpas (min. 6 simboliai)")
                    elif new_pass != new_pass_confirm:
                        st.warning("Slaptažodžiai nesutampa")
                    else:
                        res = change_password(new_pass)
                        if res.get('success'):
                            st.success("Slaptažodis pakeistas sėkmingai!")
                        else:
                            st.error("Nepavyko pakeisti slaptažodžio. Bandykite vėliau.")

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
                            # Billing Portal button
                            profile = get_user_profile(st.session_state.user['id'])
                            cust_id = profile.get('stripe_customer_id')
                            if cust_id:
                                if st.button("⚙️ Valdyti prenumeratą", use_container_width=True):
                                    portal = create_billing_portal(cust_id)
                                    if portal.get('url'):
                                        streamlit_js_eval(js_expressions=f"window.open('{portal['url']}', '_blank')")
                                    else:
                                        st.error("Nepavyko atidaryti portalo.")
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
                            # Save login to browser localStorage
                            user_json = json.dumps(st.session_state.user)
                            streamlit_js_eval(js_expressions=f"localStorage.setItem('quantum_user', '{user_json}')")
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
                
                # Forgot password
                if st.button("🔑 Pamiršau slaptažodį", use_container_width=True):
                    if email:
                        res = reset_password(email)
                        if res.get('success'):
                            st.success("Slaptažodžio atnaujinimo nuoroda išsiųsta į jūsų el. paštą!")
                        else:
                            st.error("Nepavyko išsiųsti. Patikrinkite el. pašto adresą.")
                    else:
                        st.warning("Pirmiausia įveskite savo el. pašto adresą viršuje.")
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

    # API key: admin sees input, regular users use server key
    if is_admin():
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
    else:
        api_key = os.getenv("GEMINI_API_KEY", "")

    st.divider()

    if is_admin():
        st.subheader("Šiandienos progresas")
        current_limit = get_limit('daily')
        remaining = max(0, current_limit - st.session_state.flashcards_count)
        progress = min(st.session_state.flashcards_count / current_limit, 1.0)
        st.progress(progress)
        st.caption(f"Sukurta {st.session_state.flashcards_count} iš {current_limit} kortelių")

        if remaining == 0 and not st.session_state.is_premium:
            st.warning("Dienos limitas pasiektas. Tapkite Premium nariu ir kurkite neribotai!")

    # 🔥 Streak display
    if st.session_state.user and SUPABASE_AVAILABLE:
        streak_data = get_streak(st.session_state.user['id'])
        streak = streak_data['streak']
        longest = streak_data['longest']
        total = streak_data['total']
        studied_today = streak_data['studied_today']
        
        st.divider()
        
        # Fire emojis based on streak length
        if streak >= 30:
            fire = "🔥🔥🔥🔥🔥"
            msg = "LEGENDINIS! Mėnuo iš eilės!"
        elif streak >= 14:
            fire = "🔥🔥🔥🔥"
            msg = "NEĮTIKĖTINA! 2+ savaitės!"
        elif streak >= 7:
            fire = "🔥🔥🔥"
            msg = "PUIKU! Visa savaitė!"
        elif streak >= 3:
            fire = "🔥🔥"
            msg = "Šauniai sekasi!"
        elif streak >= 1:
            fire = "🔥"
            msg = "Geras startas!"
        else:
            fire = "💤"
            msg = "Mokykis šiandien!"
        
        st.markdown(f"### {fire} {streak} d.")
        
        if studied_today:
            st.success(f"✅ Šiandien jau mokėtės!")
        else:
            st.warning("⏳ Šiandien dar nesimokėte")
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.metric("Rekordas", f"{longest} d.")
        with col_s2:
            st.metric("Iš viso", f"{total} 🃏")
        
        st.caption(msg)

    st.divider()
    st.caption("Sukurta su ❤️ Lietuvos studentams")

    with st.expander("Privatumo politika (BDAR)"):
        st.markdown("""
<a name="privatumo-politika"></a>
**QUANTUM — Privatumo politika**
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

# Main UI Logic
if not st.session_state.user:
    # LANDING PAGE FOR GUESTS
    col_l1, col_l2, col_l3 = st.columns([1,1,1])
    with col_l2:
        st.image("assets/logo.png", use_container_width=True)
    
    st.markdown("""
    <div style="text-align: center; padding: 0px 20px 40px 20px;">
        <p style="font-size: 1.2rem; color: #8b949e; max-width: 900px; margin: 0 auto; font-family: monospace; letter-spacing: 2px; text-transform: uppercase;">
            <span class="highlight">Q</span>uestion · <span class="highlight">U</span>nderstand · <span class="highlight">A</span>I · <span class="highlight">N</span>eural · <span class="highlight">T</span>hink · <span class="highlight">U</span>nified · <span class="highlight">M</span>emory
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 20px; background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
            <h3 style="color: #00f2ff;">⚡ Greitis</h3>
            <p style="color: #8b949e;">Sukurk 10 kortelių iš bet kokio teksto ar PDF per 5 sekundes.</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 20px; background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
            <h3 style="color: #00f2ff;">🧠 Intelektas</h3>
            <p style="color: #8b949e;">Gemini 2.0 technologija užtikrina aukščiausią klausimų kokybę.</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div style="text-align: center; padding: 20px; background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
            <h3 style="color: #00f2ff;">🎯 Rezultatai</h3>
            <p style="color: #8b949e;">Spaced Repetition sistema padės viską prisiminti visam laikui.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 **Norėdami pradėti, atidarykite meniu ☰ viršuje kairėje ir prisijunkite.**")
    
    st.stop() # Prevents guests from seeing the technical tabs below

# Main tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📝 Naujos kortelės",
    "🧠 Mokymasis",
    "🎴 Peržiūra",
    "💾 Atsisiuntimas",
    "💬 Paklausti AI",
    "👥 Bendruomenė"
])

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
            language = st.selectbox("Kalba:", ["lietuvių", "anglų"])
        with col_opt3:
            st.write("")  # spacing
            if st.button("🎯 Generuoti korteles", type="primary", disabled=not input_text or not can_generate, use_container_width=True):
                if not api_key:
                    st.error("API raktas nenustatytas. Susisiekite su administratoriumi arba bandykite vėliau.")
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
                        st.error("API raktas nenustatytas. Susisiekite su administratoriumi arba bandykite vėliau.")
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
                        st.error("API raktas nenustatytas. Susisiekite su administratoriumi arba bandykite vėliau.")
                    else:
                        with st.spinner("Kuriamos kortelės..."):
                            cards = generate_flashcards_from_text(transcript, num_cards_yt, "lietuvių", api_key)
                            save_generated_cards(cards)

    # ---- NUOTRAUKA ----
    elif source_type == "📸 Nuotrauka":
        st.info("Nufotografuokite savo užrašus, lentą ar skaidrę — AI viską atpažins!")

        uploaded_images = st.file_uploader(
            "Įkelkite nuotrauką (-as):",
            type=["jpg", "jpeg", "png", "webp"],
            help="Palaikomi formatai: JPG, PNG, WEBP. Galima kelti kelias nuotraukas iš karto!",
            accept_multiple_files=True
        )

        if uploaded_images:
            num_cards_img = st.slider("Kortelių kiekis (vienai nuotraukai):", 5, 20, 10, key="slider_img")
            
            # Show previews
            preview_cols = st.columns(min(len(uploaded_images), 4))
            for i, img_file in enumerate(uploaded_images):
                with preview_cols[i % len(preview_cols)]:
                    preview = Image.open(img_file)
                    st.image(preview, caption=f"📸 {i+1}", use_container_width=True)
                    img_file.seek(0)  # Reset file pointer after preview

            if st.button("🎯 Generuoti iš nuotraukų", type="primary", disabled=not can_generate, use_container_width=True):
                if not api_key:
                    st.error("API raktas nenustatytas. Susisiekite su administratoriumi arba bandykite vėliau.")
                else:
                    all_cards = []
                    for idx, uploaded_image in enumerate(uploaded_images):
                        with st.spinner(f"Analizuojama nuotrauka {idx+1}/{len(uploaded_images)}..."):
                            try:
                                client = get_gemini_client(api_key)
                                image = Image.open(uploaded_image)

                                # Keep original format when possible
                                img_format = uploaded_image.type.split('/')[-1].upper()
                                if img_format == 'JPG':
                                    img_format = 'JPEG'
                                if img_format not in ('JPEG', 'PNG', 'WEBP'):
                                    img_format = 'PNG'

                                # Resize image if too large
                                max_size = 1600
                                if image.width > max_size or image.height > max_size:
                                    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                                img_buffer = BytesIO()
                                image.save(img_buffer, format=img_format)
                                img_bytes = img_buffer.getvalue()

                                mime_type = f"image/{img_format.lower()}"
                                if img_format == 'JPEG':
                                    mime_type = "image/jpeg"

                                prompt = f"""Tu esi ekspertas akademinis asistentas.

Išanalizuok šią nuotrauką (tai gali būti užrašai, lenta, skaidrė ar vadovėlis).
Sukurk {num_cards_img} kortelių lietuvių kalba.

GRĄŽINK TIK JSON ARRAY formatu:
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
                                    st.warning(f"Nepavyko atpažinti nuotraukos {idx+1} turinio.")
                                else:
                                    cards = parse_flashcards_json(response.text)
                                    if cards:
                                        all_cards.extend(cards)
                                    else:
                                        st.warning(f"Nepavyko sukurti kortelių iš nuotraukos {idx+1}.")
                            except Exception as e:
                                if "timeout" in str(e).lower():
                                    st.warning(f"Nuotrauka {idx+1} — užtruko per ilgai, praleista.")
                                else:
                                    st.warning(f"Nuotrauka {idx+1} — nepavyko apdoroti.")
                    
                    # Save all cards at once
                    if all_cards:
                        save_generated_cards(all_cards)
                    else:
                        st.error("Nepavyko sukurti kortelių iš nuotraukų. Pabandykite kitas.")

# ==================
# TAB 2: MOKYMASIS
# ==================
with tab2:
    st.header("🧠 Mokymasis")

    study_mode = st.radio(
        "Pasirinkite mokymosi režimą:",
        ["Kartojimas", "Egzaminas"],
        horizontal=True,
        key="study_mode_radio",
        label_visibility="collapsed"
    )

    st.divider()

    if study_mode == "Kartojimas":
        # === SPACED REPETITION (original code) ===
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

    else:
        # === EGZAMINO REŽIMAS ===

        if not st.session_state.flashcards:
            st.info("Norėdami pradėti egzaminą, pirmiausia susikurkite kortelių!")

        elif st.session_state.exam_finished:
            # ---- REZULTATŲ EKRANAS ----
            st.subheader("Egzamino rezultatai")

            results = st.session_state.exam_results
            correct = sum(1 for r in results if r['correct'])
            total = len(results)
            percent = (correct / total) * 100 if total > 0 else 0

            # Update streak after exam
            if st.session_state.user and SUPABASE_AVAILABLE and total > 0:
                update_streak(st.session_state.user['id'], cards_studied=total)

            # Time taken
            elapsed = int(time.time() - st.session_state.exam_start_time) if st.session_state.exam_start_time else 0
            time_str = f"{elapsed // 60} min {elapsed % 60} sek"

            # Color-coded progress
            if percent >= 80:
                bar_color = "green"
                grade_text = "Puikiai!"
            elif percent >= 50:
                bar_color = "orange"
                grade_text = "Neblogai, bet galima geriau"
            else:
                bar_color = "red"
                grade_text = "Reikia daugiau praktikos"

            st.markdown(f"""
            <div style="text-align:center; padding: 20px; border-radius: 15px;
                        background: linear-gradient(135deg, rgba(0,0,0,0.2), rgba(0,0,0,0.1));
                        border: 2px solid {bar_color};">
                <h1 style="color: {bar_color}; margin: 0;">{correct}/{total}</h1>
                <h2 style="color: {bar_color}; margin: 4px 0;">{percent:.0f}%</h2>
                <p style="color: #8b949e; margin: 4px 0;">{grade_text}</p>
                <p style="color: #8b949e; margin: 4px 0;">Laikas: {time_str}</p>
            </div>
            """, unsafe_allow_html=True)

            st.progress(percent / 100)

            # Weak spots
            weak_spots = [r['card'] for r in results if not r['correct']]
            if weak_spots:
                st.divider()
                with st.expander(f"Silpnos vietos ({len(weak_spots)} kortelės)", expanded=True):
                    for card in weak_spots:
                        st.markdown(f"**{html.escape(card['klausimas'])}**")
                        st.caption(f"Atsakymas: {html.escape(card['atsakymas'])}")
            else:
                st.balloons()
                st.success("Tobula! Visos atsakytos teisingai!")

            st.divider()
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if st.button("Bandyti dar kartą", type="primary", use_container_width=True, key="exam_retry"):
                    st.session_state.exam_finished = False
                    st.session_state.exam_active = False
                    st.rerun()
            with bcol2:
                if st.button("Grįžti į kartojimą", use_container_width=True, key="exam_back"):
                    st.session_state.exam_finished = False
                    st.session_state.exam_active = False
                    st.rerun()

        elif not st.session_state.exam_active:
            # ---- PRADŽIOS EKRANAS ----
            total_available = len(st.session_state.flashcards)
            st.markdown(f"Turite **{total_available}** kortelių. Pasirinkite egzamino nustatymus:")

            exam_count = st.select_slider(
                "Klausimų skaičius:",
                options=[n for n in [5, 10, 15, 20] if n <= total_available] or [total_available],
                value=min(10, total_available),
                key="exam_count_slider"
            )

            use_timer = st.checkbox("Su laiko limitu", key="exam_use_timer")
            time_limit_minutes = None
            if use_timer:
                time_limit_minutes = st.select_slider(
                    "Laiko limitas:",
                    options=[5, 10, 15],
                    value=10,
                    format_func=lambda x: f"{x} min",
                    key="exam_time_slider"
                )

            st.markdown("""
            - Klausimai pateikiami atsitiktine tvarka
            - Pabaigoje pamatysite balą ir silpnas vietas
            """)

            if st.button("Pradėti egzaminą", type="primary", use_container_width=True, key="exam_start"):
                all_cards = list(st.session_state.flashcards)
                random.shuffle(all_cards)
                st.session_state.exam_cards = all_cards[:exam_count]
                st.session_state.exam_total = exam_count
                st.session_state.exam_active = True
                st.session_state.exam_finished = False
                st.session_state.exam_current_idx = 0
                st.session_state.exam_results = []
                st.session_state.exam_show_answer = False
                st.session_state.exam_start_time = time.time()
                st.session_state.exam_time_limit = (time_limit_minutes * 60) if time_limit_minutes else None
                st.rerun()

        else:
            # ---- EGZAMINO EIGA ----
            idx = st.session_state.exam_current_idx
            cards = st.session_state.exam_cards
            total = len(cards)
            elapsed = int(time.time() - st.session_state.exam_start_time)
            time_limit = st.session_state.exam_time_limit

            # Check time limit
            if time_limit and elapsed >= time_limit:
                st.session_state.exam_finished = True
                st.session_state.exam_active = False
                st.rerun()

            # Header: progress + timer
            hcol1, hcol2 = st.columns([3, 1])
            with hcol1:
                st.progress((idx + 1) / total)
                st.caption(f"Klausimas {idx + 1} iš {total}")
            with hcol2:
                if time_limit:
                    remaining = max(0, time_limit - elapsed)
                    r_min = remaining // 60
                    r_sec = remaining % 60
                    color = "red" if remaining < 60 else "#8b949e"
                    st.markdown(f"<p style='text-align:right; color:{color}; font-size:1.3em; font-weight:bold;'>{r_min:02d}:{r_sec:02d}</p>", unsafe_allow_html=True)
                else:
                    st.metric("Laikas", f"{elapsed // 60:02d}:{elapsed % 60:02d}")

            # Question card
            card = cards[idx]
            st.markdown(f"""
            <div class="study-card study-card-q">
                <h3>{html.escape(card['klausimas'])}</h3>
            </div>
            """, unsafe_allow_html=True)

            if not st.session_state.exam_show_answer:
                if st.button("Rodyti atsakymą", type="primary", use_container_width=True, key="exam_show"):
                    st.session_state.exam_show_answer = True
                    st.rerun()
            else:
                st.markdown(f"""
                <div class="study-card study-card-a">
                    <h3>{html.escape(card['atsakymas'])}</h3>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("### Ar žinojote atsakymą?")
                rcol1, rcol2 = st.columns(2)
                with rcol1:
                    if st.button("Žinojau", use_container_width=True, key="exam_correct"):
                        st.session_state.exam_results.append({"card": card, "correct": True})
                        if idx + 1 < total:
                            st.session_state.exam_current_idx += 1
                            st.session_state.exam_show_answer = False
                        else:
                            st.session_state.exam_finished = True
                            st.session_state.exam_active = False
                        st.rerun()
                with rcol2:
                    if st.button("Nežinojau", use_container_width=True, key="exam_wrong"):
                        st.session_state.exam_results.append({"card": card, "correct": False})
                        if idx + 1 < total:
                            st.session_state.exam_current_idx += 1
                            st.session_state.exam_show_answer = False
                        else:
                            st.session_state.exam_finished = True
                            st.session_state.exam_active = False
                        st.rerun()

            st.divider()
            if st.button("Nutraukti egzaminą", key="exam_cancel"):
                st.session_state.exam_active = False
                st.session_state.exam_finished = False
                st.rerun()

# ==================
# TAB 3: PERŽIŪRA
# ==================
with tab3:
    st.header("🎴 Jūsų kortelės")

    if not st.session_state.flashcards:
        st.info("Kol kas neturite kortelių. Sukurkite jas 'Naujos kortelės' skiltyje!")
    else:
        all_cards = st.session_state.flashcards

        # Search & filter
        search_col, count_col = st.columns([3, 1])
        with search_col:
            card_search = st.text_input(
                "🔍 Ieškoti kortelėse:",
                placeholder="Įveskite raktažodį...",
                key="card_search"
            )
        with count_col:
            st.metric("Iš viso", len(all_cards))

        # Filter cards by search query
        if card_search:
            query_lower = card_search.lower()
            filtered_indices = [
                i for i, c in enumerate(all_cards)
                if query_lower in c['klausimas'].lower() or query_lower in c['atsakymas'].lower()
            ]
            cards = [all_cards[i] for i in filtered_indices]
            if not cards:
                st.warning(f"Nerasta kortelių su \"{card_search}\"")
            else:
                st.caption(f"Rasta {len(cards)} iš {len(all_cards)} kortelių")
        else:
            filtered_indices = list(range(len(all_cards)))
            cards = all_cards

        if cards:
            total = len(cards)

            # Clamp current_card to valid range
            if st.session_state.current_card >= total:
                st.session_state.current_card = total - 1
            if st.session_state.current_card < 0:
                st.session_state.current_card = 0
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

            for idx_in_filtered, real_idx in enumerate(filtered_indices):
                c = all_cards[real_idx]
                label = f"**{real_idx+1}. {html.escape(c['klausimas'][:50])}{'...' if len(c['klausimas']) > 50 else ''}**"
                with st.expander(label):
                    new_q = st.text_input("Klausimas:", c['klausimas'], key=f"q_{real_idx}")
                    new_a = st.text_area("Atsakymas:", c['atsakymas'], key=f"a_{real_idx}", height=100)

                    if st.button("💾 Išsaugoti", key=f"save_{real_idx}"):
                        st.session_state.flashcards[real_idx] = {"klausimas": new_q, "atsakymas": new_a}
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
        st.warning("AI asistentas šiuo metu neprieinamas. Bandykite vėliau.")
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

# ==================
# TAB 6: BENDRUOMENĖ
# ==================
with tab6:
    st.header("👥 Bendruomenė")
    st.caption("Naršykite kitų studentų korteles arba pasidalinkite savomis")

    community_mode = st.radio(
        "Režimas:",
        ["🔍 Naršyti", "📤 Publikuoti"],
        horizontal=True,
        label_visibility="collapsed",
        key="community_mode"
    )

    st.divider()

    if community_mode == "🔍 Naršyti":
        # === BROWSING SECTION ===
        st.subheader("🔍 Raskite kortelių rinkinius")

        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            search_query = st.text_input(
                "Paieška:",
                placeholder="Pvz. Anatomija, Matematika, Programavimas...",
                key="community_search"
            )
        with search_col2:
            uni_filter = st.selectbox(
                "Universitetas:",
                ["Visi", "VU", "KTU", "VGTU", "VDU", "KU", "MRU", "LSU", "Kita"],
                key="community_uni"
            )

        if SUPABASE_AVAILABLE:
            result = get_public_sets(
                query=search_query if search_query else None,
                university=uni_filter if uni_filter != "Visi" else None
            )

            if result['success'] and result['sets']:
                st.caption(f"Rasta {len(result['sets'])} rinkinių")

                for pub_set in result['sets']:
                    set_name = pub_set.get('name', 'Be pavadinimo')
                    set_uni = pub_set.get('university', '')
                    set_course = pub_set.get('course', '')
                    set_subject = pub_set.get('subject', '')
                    downloads = pub_set.get('downloads_count', 0)
                    set_id = pub_set.get('id')

                    # Author email (partial, for privacy)
                    author_info = pub_set.get('profiles', {})
                    author_email = author_info.get('email', '') if isinstance(author_info, dict) else ''
                    if author_email:
                        parts = author_email.split('@')
                        author_display = f"{parts[0][:3]}***@{parts[1]}" if len(parts) == 2 else ''
                    else:
                        author_display = ''

                    # Card label
                    label_parts = [f"**{html.escape(set_name)}**"]
                    if set_uni:
                        label_parts.append(f"🏛️ {set_uni}")
                    if set_course:
                        label_parts.append(f"📚 {set_course}")
                    label = " · ".join(label_parts)

                    with st.expander(label):
                        info_col1, info_col2, info_col3 = st.columns(3)
                        with info_col1:
                            st.caption(f"🏛️ {set_uni or 'Nenurodyta'}")
                        with info_col2:
                            st.caption(f"📖 {set_subject or 'Nenurodyta'}")
                        with info_col3:
                            st.caption(f"⬇️ {downloads} atsisiuntimų")

                        if author_display:
                            st.caption(f"👤 {author_display}")

                        # Clone button
                        if st.session_state.user:
                            if st.button("📥 Kopijuoti į savo", key=f"clone_{set_id}", use_container_width=True, type="primary"):
                                with st.spinner("Kopijuojama..."):
                                    clone_result = clone_public_set(set_id, st.session_state.user['id'])
                                    if clone_result.get('success'):
                                        sync_flashcards_from_supabase(st.session_state.user['id'])
                                        st.success("✅ Rinkinys nukopijuotas į jūsų paskyrą!")
                                        st.rerun()
                                    else:
                                        st.error(f"Nepavyko nukopijuoti: {clone_result.get('error', 'Nežinoma klaida')}")
                        else:
                            st.info("💡 Prisijunkite, kad galėtumėte kopijuoti rinkinius")

            elif result['success'] and not result['sets']:
                st.info("🔍 Nerasta jokių viešų rinkinių. Būkite pirmieji — publikuokite savo!")
            else:
                st.warning("Nepavyko prisijungti prie bendruomenės. Bandykite vėliau.")
        else:
            st.warning("Bendruomenės funkcija reikalauja Supabase prisijungimo.")

    else:
        # === PUBLISHING SECTION ===
        st.subheader("📤 Publikuokite savo rinkinius")

        if not st.session_state.user:
            st.info("💡 Prisijunkite, kad galėtumėte publikuoti savo korteles bendruomenei.")
        elif not SUPABASE_AVAILABLE:
            st.warning("Publikavimui reikia Supabase prisijungimo.")
        else:
            user_sets_result = get_user_sets(st.session_state.user['id'])

            if user_sets_result['success'] and user_sets_result['sets']:
                user_sets = user_sets_result['sets']

                set_options = [
                    f"{s['name']} ({s.get('card_count', '?')} kort.) {'✅ Viešas' if s.get('is_public') else ''}"
                    for s in user_sets
                ]

                selected_set_idx = st.selectbox(
                    "Pasirinkite rinkinį:",
                    range(len(set_options)),
                    format_func=lambda x: set_options[x],
                    key="publish_set_select"
                )

                selected_set = user_sets[selected_set_idx]

                if selected_set.get('is_public'):
                    st.success(f"✅ Šis rinkinys jau viešas ({selected_set.get('university', '')}, {selected_set.get('course', '')})")
                    if st.button("🔒 Padaryti privatų", key="make_private", use_container_width=True):
                        make_set_public(selected_set['id'], '', '', '', is_public=False)
                        st.success("Rinkinys dabar privatus.")
                        st.rerun()
                else:
                    st.markdown("Užpildykite informaciją, kad kiti studentai galėtų lengvai rasti jūsų korteles:")

                    pub_col1, pub_col2 = st.columns(2)
                    with pub_col1:
                        pub_university = st.selectbox(
                            "🏛️ Universitetas:",
                            ["VU", "KTU", "VGTU", "VDU", "KU", "MRU", "LSU", "Kita"],
                            key="pub_uni"
                        )
                        pub_course = st.text_input(
                            "📚 Kursas / Modulis:",
                            placeholder="Pvz. Žmogaus anatomija",
                            key="pub_course"
                        )
                    with pub_col2:
                        pub_subject = st.text_input(
                            "📖 Dalykas / Tema:",
                            placeholder="Pvz. Kaulų sistema",
                            key="pub_subject"
                        )

                    if st.button("🚀 Publikuoti bendruomenei", type="primary", use_container_width=True, key="publish_btn"):
                        if not pub_course:
                            st.warning("Nurodykite bent kursą / modulį")
                        else:
                            with st.spinner("Publikuojama..."):
                                pub_result = make_set_public(
                                    selected_set['id'],
                                    pub_university,
                                    pub_course,
                                    pub_subject or '',
                                    is_public=True
                                )
                                if pub_result.get('success'):
                                    st.success("🎉 Jūsų rinkinys dabar viešas! Kiti studentai galės jį rasti bendruomenėje.")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error("Nepavyko publikuoti. Bandykite dar kartą.")
            else:
                st.info("Kol kas neturite rinkinių. Sukurkite korteles ir galėsite dalintis!")

