import streamlit as st
from google import genai
from google.genai import types
import PyPDF2
import json
import csv
from io import StringIO
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="FlashCards AI - Lietuvių studentams",
    page_icon="📚",
    layout="wide"
)

# Custom CSS for flip cards
st.markdown("""
<style>
.flip-card {
    background-color: transparent;
    width: 100%;
    height: 250px;
    perspective: 1000px;
    margin: 20px 0;
}
.flip-card-inner {
    position: relative;
    width: 100%;
    height: 100%;
    text-align: center;
    transition: transform 0.6s;
    transform-style: preserve-3d;
    cursor: pointer;
}
.flip-card:hover .flip-card-inner {
    transform: rotateY(180deg);
}
.flip-card-front, .flip-card-back {
    position: absolute;
    width: 100%;
    height: 100%;
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
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}
.flip-card-back {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: white;
    transform: rotateY(180deg);
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'flashcards' not in st.session_state:
    st.session_state.flashcards = []
if 'flashcards_count' not in st.session_state:
    st.session_state.flashcards_count = 0
if 'current_card' not in st.session_state:
    st.session_state.current_card = 0
if 'is_premium' not in st.session_state:
    st.session_state.is_premium = False

# Daily limit
DAILY_LIMIT = 20
MAX_PDF_CHARS = 10000

# ==========================
# GEMINI API SETUP
# ==========================

def get_gemini_client(api_key):
    """Configure and return Gemini client"""
    return genai.Client(api_key=api_key)

# ==========================
# FLASHCARD GENERATION
# ==========================

def generate_flashcards_from_text(text, num_cards=10, language="lietuvių", api_key=None):
    """Generate flashcards using Gemini 2.0 Flash"""
    if not api_key:
        st.error("❌ Įveskite Gemini API key!")
        return []
    
    try:
        client = get_gemini_client(api_key)
        
        # Active Recall metodologija
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
{text}

GRAŽINK TIK JSON ARRAY formatu (be jokio papildomo teksto):
[
  {{"klausimas": "...", "atsakymas": "..."}},
  {{"klausimas": "...", "atsakymas": "..."}}
]
"""
        
        # New API call format
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",  # Try newest model
            contents=prompt
        )
        content = response.text
        
        # Parse JSON
        import re
        # Išvalyti markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        # Robust JSON parsing
        try:
            flashcards = json.loads(content.strip())
        except json.JSONDecodeError:
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                flashcards = json.loads(match.group())
            else:
                st.error("❌ AI negrąžino tinkamo JSON formato. Bandykite dar kartą.")
                return []
        
        # Validate
        if not isinstance(flashcards, list):
            st.error("❌ AI negrąžino kortelių sąrašo formato")
            return []
        
        valid_cards = []
        for card in flashcards:
            if isinstance(card, dict) and 'klausimas' in card and 'atsakymas' in card:
                valid_cards.append(card)
        
        return valid_cards
        
    except Exception as e:
        st.error(f"Klaida generuojant flashcard'us: {str(e)}")
        return []

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
            text += page.extract_text() + "\n"
        
        if len(text) > MAX_PDF_CHARS:
            text = text[:MAX_PDF_CHARS]
            st.warning(f"⚠️ PDF tekstas apribotas iki {MAX_PDF_CHARS:,} simbolių")
        
        return text
    except Exception as e:
        st.error(f"Klaida skaitant PDF: {str(e)}")
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

# Header
st.title("📚 FlashCards AI")
st.markdown("**Automatiškai sukurk flashcard'us iš teksto ar PDF** | Powered by Gemini 2.0 Flash ⚡")

# Sidebar
with st.sidebar:
    st.header("⚙️ Nustatymai")
    
    # API Key instructions
    st.markdown("""**📌 Kaip gauti Gemini API raktą:**
1. Eik į [aistudio.google.com](https://aistudio.google.com/apikey)
2. Prisijunk su Google paskyra
3. Sukurk naują API key
4. Įklijuok čia ⬇️""")
    
    api_key = st.text_input(
        "Gemini API Key", 
        value=os.getenv("GEMINI_API_KEY", ""),
        type="password",
        placeholder="AIza..."
    )
    
    st.divider()
    
    # Free tier limits
    st.subheader("📊 Jūsų limitas")
    remaining = max(0, DAILY_LIMIT - st.session_state.flashcards_count)
    progress = min(st.session_state.flashcards_count / DAILY_LIMIT, 1.0)
    st.progress(progress)
    st.caption(f"{st.session_state.flashcards_count}/{DAILY_LIMIT} flashcard'ų šiandien")
    
    if remaining == 0 and not st.session_state.is_premium:
        st.warning("⚠️ Pasiekėte dienos limitą!")
        st.markdown("### 💎 Premium €3.99/mėn")
        st.markdown("✅ Neriboti flashcard'ai")
        if st.button("🚀 Upgrade", type="primary"):
            st.info("Stripe integracija - netrukus!")
    
    st.divider()
    st.caption("Made with ❤️ for LT students")
    st.caption("Powered by Gemini 2.0 Flash ⚡")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["📝 Tekstas", "📄 PDF", "🎴 Peržiūra", "💾 Eksportas"])

# ==================
# TAB 1: TEXT INPUT
# ==================
with tab1:
    st.header("Sukurk flashcard'us iš teksto")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        input_text = st.text_area(
            "Įklijuokite tekstą:",
            height=300,
            placeholder="Kopijuokite paskaitų konspektą, vadovėlio skyrių ar savo užrašus..."
        )
    
    with col2:
        num_cards = st.slider("Kortelių skaičius:", 5, 20, 10)
        language = st.selectbox("Kalba:", ["lietuvių", "anglų", "abi"])
        
        can_generate = (
            st.session_state.flashcards_count < DAILY_LIMIT or 
            st.session_state.is_premium
        )
        
        if st.button("🎯 Generuoti", type="primary", disabled=not input_text or not can_generate):
            if not api_key:
                st.error("❌ Įveskite Gemini API key!")
            else:
                with st.spinner("Kuriami flashcard'ai... ⏳"):
                    cards = generate_flashcards_from_text(input_text, num_cards, language, api_key)
                    if cards:
                        st.session_state.flashcards = cards
                        st.session_state.flashcards_count += len(cards)
                        st.session_state.current_card = 0
                        st.balloons()
                        st.success(f"✅ Sukurta {len(cards)} flashcard'ų!")
                        st.rerun()

# ==================
# TAB 2: PDF UPLOAD
# ==================
with tab2:
    st.header("Sukurk flashcard'us iš PDF")
    
    uploaded_pdf = st.file_uploader(
        "Įkelkite PDF failą:",
        type=["pdf"],
        help="Veikia su tekstiniais PDF (ne skanuotomis nuotraukomis)"
    )
    
    if uploaded_pdf:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            with st.spinner("Ekstraktuojamas tekstas..."):
                pdf_text = extract_text_from_pdf(uploaded_pdf)
            
            if pdf_text:
                st.text_area("Ekstraktuotas tekstas:", pdf_text[:1000] + "...", height=200)
                st.caption(f"Viso simbolių: {len(pdf_text):,}")
        
        with col2:
            num_cards_pdf = st.slider("Kortelių skaičius:", 5, 20, 10, key="pdf_slider")
            
            can_generate = (
                st.session_state.flashcards_count < DAILY_LIMIT or 
                st.session_state.is_premium
            )
            
            if st.button("🎯 Generuoti iš PDF", type="primary", disabled=not pdf_text or not can_generate):
                if not api_key:
                    st.error("❌ Įveskite Gemini API key!")
                else:
                    with st.spinner("Kuriami flashcard'ai iš PDF... ⏳"):
                        cards = generate_flashcards_from_text(pdf_text, num_cards_pdf, "lietuvių", api_key)
                        if cards:
                            st.session_state.flashcards = cards
                            st.session_state.flashcards_count += len(cards)
                            st.session_state.current_card = 0
                            st.balloons()
                            st.success(f"✅ Sukurta {len(cards)} flashcard'ų!")
                            st.rerun()

# ==================
# TAB 3: FLASHCARD VIEWER
# ==================
with tab3:
    st.header("🎴 Peržiūrėk flashcard'us")
    
    if not st.session_state.flashcards:
        st.info("👈 Pirmiausia sukurkite flashcard'us kitose kortelėse!")
    else:
        cards = st.session_state.flashcards
        total = len(cards)
        current = st.session_state.current_card
        
        # Progress
        st.progress((current + 1) / total)
        st.caption(f"Kortelė {current + 1} iš {total}")
        
        # Flip card
        card = cards[current]
        st.markdown(f"""
        <div class="flip-card">
            <div class="flip-card-inner">
                <div class="flip-card-front">
                    <p><strong>❓ Klausimas:</strong><br>{card['klausimas']}</p>
                </div>
                <div class="flip-card-back">
                    <p><strong>✅ Atsakymas:</strong><br>{card['atsakymas']}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.caption("💡 Desktop: užvesk pelę | Mobile: bakstelk kortelę")
        
        # Navigation
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅️ Atgal", disabled=current == 0):
                st.session_state.current_card -= 1
                st.rerun()
        
        with col3:
            if st.button("Pirmyn ➡️", disabled=current == total - 1):
                st.session_state.current_card += 1
                st.rerun()
        
        # Editable cards
        st.divider()
        st.subheader("✏️ Redaguoti korteles")
        
        for i, c in enumerate(cards):
            with st.expander(f"**{i+1}. {c['klausimas'][:50]}...**" if len(c['klausimas']) > 50 else f"**{i+1}. {c['klausimas']}**"):
                new_q = st.text_input("Klausimas:", c['klausimas'], key=f"q_{i}")
                new_a = st.text_area("Atsakymas:", c['atsakymas'], key=f"a_{i}", height=100)
                
                if st.button("💾 Išsaugoti", key=f"save_{i}"):
                    st.session_state.flashcards[i] = {"klausimas": new_q, "atsakymas": new_a}
                    st.success("Išsaugota!")

# ==================
# TAB 4: EXPORT
# ==================
with tab4:
    st.header("💾 Eksportuoti flashcard'us")
    
    if not st.session_state.flashcards:
        st.info("👈 Pirmiausia sukurkite flashcard'us!")
    else:
        st.success(f"✅ Turite {len(st.session_state.flashcards)} flashcard'ų paruoštų eksportui")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("📥 Anki")
            st.caption("Importuokite į Anki programą")
            st.download_button(
                label="⬇️ CSV (Anki)",
                data=export_to_anki_csv(st.session_state.flashcards),
                file_name=f"flashcards_anki_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            st.subheader("📥 Quizlet")
            st.caption("Importuokite į Quizlet")
            st.download_button(
                label="⬇️ JSON (Quizlet)",
                data=export_to_quizlet_json(st.session_state.flashcards),
                file_name=f"flashcards_quizlet_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
        
        with col3:
            st.subheader("📥 Tekstas")
            st.caption("Paprastas TXT formatas")
            st.download_button(
                label="⬇️ TXT",
                data=export_to_txt(st.session_state.flashcards),
                file_name=f"flashcards_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )
        
        # Preview
        st.divider()
        st.subheader("👀 Peržiūra")
        for i, card in enumerate(st.session_state.flashcards, 1):
            st.markdown(f"**{i}. {card['klausimas']}**")
            st.caption(f"↳ {card['atsakymas']}")
