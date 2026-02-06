# 📁 FlashCards AI - Project Structure

## Failų medis

```
flashcard-app/
├── app.py                      # 🎯 MAIN APP - Streamlit UI + visas funkcionalumas
├── requirements.txt            # 📦 Python dependencies
├── packages.txt                # 📦 System packages (Tesseract OCR)
├── .env.example               # 🔐 Environment variables template
├── .gitignore                 # 🚫 Git ignore rules
│
├── .streamlit/
│   └── config.toml            # ⚙️ Streamlit configuration
│
├── stripe_integration.py      # 💰 Stripe payment (Fase 4 - future)
│
├── README.md                  # 📖 Project documentation
├── QUICKSTART.md              # 🚀 Quick deployment guide
├── MARKETING.md               # 📣 Marketing copy templates
└── TEST_DATA.md               # 🧪 Test scenarios & sample data
```

---

## Failų aprašymas

### Core Files

#### `app.py` (Main application)
**Apimtis:** 450+ eilučių
**Funkcionalumas:**
- ✅ **Fase 1:** Text → Flashcards (OpenAI GPT-3.5)
- ✅ **Fase 2:** PDF → Extract → Flashcards
- ✅ **Fase 3:** Image → OCR (Tesseract) → Flashcards
- ✅ **Fase 4:** Export (Anki CSV, Quizlet JSON)
- 📊 Session state management
- 🚦 Free tier limits (20 flashcards)
- 🎨 Streamlit UI su tabs

**Dependencies:**
```python
import streamlit as st
import openai
import PyPDF2
import pytesseract
from PIL import Image
import json
import csv
```

#### `requirements.txt`
Python bibliotekos:
```
streamlit==1.31.0       # Web UI framework
openai==0.28.0          # OpenAI API (GPT-3.5)
PyPDF2==3.0.1           # PDF text extraction
pytesseract==0.3.10     # OCR wrapper
Pillow==10.2.0          # Image processing
python-dotenv==1.0.0    # Environment variables
```

#### `packages.txt`
System-level dependencies (Streamlit Cloud):
```
tesseract-ocr           # OCR engine
tesseract-ocr-lit       # Lithuanian language pack
tesseract-ocr-eng       # English language pack
```

---

### Configuration Files

#### `.env.example`
Template environment variables:
```bash
OPENAI_API_KEY=sk-your-api-key-here

# Future: Stripe keys
# STRIPE_PUBLIC_KEY=pk_test_...
# STRIPE_SECRET_KEY=sk_test_...

# Future: Google Vision API
# GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json
```

**Setup:**
```bash
cp .env.example .env
# Edit .env and add your actual API keys
```

#### `.streamlit/config.toml`
Streamlit app configuration:
- Theme colors
- Server settings
- CORS config

#### `.gitignore`
Ignores:
- `__pycache__/`, `*.pyc`
- `.env` (secrets)
- `.vscode/`, `.idea/`
- `*.log`

---

### Future Files (Fase 4)

#### `stripe_integration.py`
**Status:** Template ready, not active yet

**Funkcijos:**
- `create_checkout_session()` - Stripe payment flow
- Webhook handler for payment events
- Premium user activation

**Kada naudoti:**
1. Baigus beta testą (Week 3)
2. Turėjus 10+ paying intent users
3. Stripe account approved

**Integration steps:**
```python
# In app.py sidebar:
if st.button("Upgrade to Premium"):
    import stripe_integration
    checkout_url = stripe_integration.create_checkout_session()
    st.markdown(f"[Pay here]({checkout_url})")
```

---

## Documentation Files

### `README.md`
**Auditorija:** Developers
**Turinys:**
- Project overview
- Installation instructions
- Development roadmap
- API cost calculations
- Deployment guide

### `QUICKSTART.md`
**Auditorija:** First-time users
**Turinys:**
- 5-minute local setup
- Streamlit Cloud deployment (step-by-step)
- Beta testing strategy
- Troubleshooting FAQ

### `MARKETING.md`
**Auditorija:** Growth/Marketing
**Turinys:**
- Social media copy (Facebook, Instagram, TikTok)
- Beta tester recruitment ads
- Landing page copy
- Email templates
- Referral program ideas

### `TEST_DATA.md`
**Auditorija:** QA/Testing
**Turinys:**
- Sample text for testing
- Expected flashcard outputs
- PDF test guide
- Image OCR test scenarios
- Manual testing checklist

---

## Dataflow

```
User Input
    ↓
┌─────────────────────────────────────┐
│  TEXT / PDF / IMAGE                 │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  EXTRACTION                         │
│  - Text: direct input               │
│  - PDF: PyPDF2.PdfReader            │
│  - Image: pytesseract.image_to_str  │
└─────────────────────────────────────┘
    ↓
    Text content
    ↓
┌─────────────────────────────────────┐
│  AI GENERATION (OpenAI GPT-3.5)     │
│  Prompt: "Sukurk N flashcard'ų..."  │
└─────────────────────────────────────┘
    ↓
    JSON flashcards
    ↓
┌─────────────────────────────────────┐
│  SESSION STATE                      │
│  st.session_state.flashcards = [..] │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  UI DISPLAY                         │
│  - Editable expanders               │
│  - Counter update                   │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  EXPORT                             │
│  - Anki CSV (semicolon-separated)   │
│  - Quizlet JSON                     │
└─────────────────────────────────────┘
    ↓
    Download
```

---

## State Management

### Session State Variables

```python
st.session_state = {
    'flashcards': [
        {'klausimas': '...', 'atsakymas': '...'},
        ...
    ],
    'flashcards_count': 0,      # Total created (for limit)
    'is_premium': False,         # Premium status
}
```

### State Flow

1. **User generates flashcards:**
   ```python
   cards = generate_flashcards_from_text(text, num_cards)
   st.session_state.flashcards = cards
   st.session_state.flashcards_count += len(cards)
   ```

2. **Check limits:**
   ```python
   if st.session_state.flashcards_count >= 20 and not st.session_state.is_premium:
       st.warning("Pasiekėte limitą!")
   ```

3. **Export:**
   ```python
   csv_data = export_to_anki_csv(st.session_state.flashcards)
   st.download_button(..., data=csv_data)
   ```

---

## API Integration

### OpenAI API

**Endpoint:** `openai.ChatCompletion.create()`
**Model:** `gpt-3.5-turbo`

**Request format:**
```python
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "Esi flashcard'ų ekspertas"},
        {"role": "user", "content": prompt}
    ],
    temperature=0.7,
    max_tokens=2000
)
```

**Cost:** ~$0.002/1k tokens (~€0.02 per 100 flashcards)

**Rate limits:**
- Free tier: 3 RPM (requests per minute)
- Paid tier: 60 RPM

### Future: Google Vision API (Premium)

```python
# Upgrade from Tesseract (free) to Google Vision ($1.50/1000 images)
if st.session_state.is_premium:
    text = google_vision_ocr(image)
else:
    text = pytesseract.image_to_string(image)
```

---

## Deployment Options

### Option 1: Streamlit Cloud (Recommended)
**Cost:** FREE
**Limits:**
- 1GB RAM
- 1 CPU
- 1 concurrent app
**Pros:**
- Zero config
- Auto-deploy from GitHub
- Built-in secrets management
**Cons:**
- Goes to sleep after inactivity
- Limited compute

### Option 2: Heroku
**Cost:** €7/month (Eco Dynos)
**Pros:**
- More control
- Add-ons ecosystem
**Cons:**
- Requires Procfile
- More setup

### Option 3: DigitalOcean App Platform
**Cost:** €12/month
**Pros:**
- Full control
- Scalable
**Cons:**
- Most expensive
- More DevOps needed

---

## Development Roadmap

### ✅ Week 1: MVP (COMPLETE)
- [x] Text → Flashcards
- [x] PDF → Flashcards
- [x] Image OCR → Flashcards
- [x] Export (Anki/Quizlet)

### 📅 Week 2: Deploy & Polish
- [ ] Deploy to Streamlit Cloud
- [ ] Test on mobile
- [ ] UI improvements based on self-testing

### 📅 Week 3: Beta Test
- [ ] Recruit 20-30 beta testers
- [ ] Collect feedback (Google Form)
- [ ] Iterate based on feedback

### 📅 Week 4: Monetization
- [ ] Stripe integration
- [ ] Premium features (Google Vision OCR)
- [ ] Launch marketing

### 📅 Month 2-3: Growth
- [ ] Instagram/TikTok content
- [ ] Referral program
- [ ] 50+ Premium users target

---

## Next Steps

1. **Setup local environment:**
   ```bash
   cd flashcard-app
   pip install -r requirements.txt
   brew install tesseract tesseract-lang  # macOS
   cp .env.example .env
   # Add your OpenAI API key to .env
   streamlit run app.py
   ```

2. **Test all features:**
   - Use TEST_DATA.md examples
   - Verify each tab works
   - Check exports download correctly

3. **Deploy to Streamlit Cloud:**
   - Follow QUICKSTART.md guide
   - Add secrets (OPENAI_API_KEY)
   - Share URL with friends for feedback

4. **Marketing:**
   - Use MARKETING.md templates
   - Post in Facebook university groups
   - Recruit beta testers

---

## File Sizes

```
app.py:                 ~18 KB (450 lines)
requirements.txt:       ~0.1 KB
packages.txt:           ~0.1 KB
README.md:              ~8 KB
QUICKSTART.md:          ~10 KB
MARKETING.md:           ~12 KB
TEST_DATA.md:           ~6 KB
stripe_integration.py:  ~8 KB (template)
```

**Total project size:** ~62 KB (extremely lightweight!)

---

**Ready to launch! 🚀**
