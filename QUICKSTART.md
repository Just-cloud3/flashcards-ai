# 🚀 Quick Start Guide - FlashCards AI

## ⚡ 5 minučių deployment

### 1. Lokalus testavimas

```bash
# 1. Klonuok projektą
git clone <your-repo>
cd flashcard-app

# 2. Sukurk virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Įdiegk dependencies
pip install -r requirements.txt

# 4. Įdiegk Tesseract OCR
# macOS:
brew install tesseract tesseract-lang

# Ubuntu:
sudo apt-get install tesseract-ocr tesseract-ocr-lit

# Windows: https://github.com/UB-Mannheim/tesseract/wiki

# 5. Setup environment
cp .env.example .env
# Redaguok .env ir įrašyk savo OpenAI API key

# 6. Paleisk!
streamlit run app.py
```

Atsidarys `http://localhost:8501` 🎉

---

## ☁️ Deploy į Streamlit Cloud (NEMOKAMAS)

### Step-by-step su screenshots

#### 1️⃣ Paruošk GitHub repo

```bash
# Inicijuok git (jei dar nepadaryta)
git init
git add .
git commit -m "Initial commit - FlashCards AI MVP"

# Sukurk GitHub repo: https://github.com/new
# Pavadink: flashcard-ai-app

# Push'ink kodą
git remote add origin https://github.com/TAVO-USERNAME/flashcard-ai-app.git
git branch -M main
git push -u origin main
```

#### 2️⃣ Deploy Streamlit Cloud

1. **Eik į:** https://streamlit.io/cloud
2. **Sign in** su GitHub accountu
3. Click **"New app"**
4. Pasirink:
   - **Repository:** `TAVO-USERNAME/flashcard-ai-app`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Click **"Advanced settings"**
6. Pridėk **Secrets** (kaip .env):
   ```toml
   OPENAI_API_KEY = "sk-proj-your-actual-key-here"
   ```
7. Click **"Deploy!"** 🚀

**Deployment trunka ~2-3 min.**

Po deployment gausi URL: `https://flashcard-ai-app.streamlit.app`

---

## 📊 Beta testavimas (Savaitė 3)

### Kur rasti beta testerius?

#### 1. Facebook grupės
- "Studijuojančių studentų grupė" (20k+ narių)
- VU studentų grupė
- KTU studentų grupė
- VGTU studentų grupė
- "Studentų nuolaidos Lietuvoje"

#### 2. Reddit
- r/lithuania
- r/vilnius
- University subreddits

#### 3. Instagram
- #studentaslt
- #studijosuLT
- Universiteto pages

### Beta testerių pasiūlymas

```
🎓 BETA TESTERIAI IEŠKOMI! (20 vietų)

Testuoju naują AI įrankį mokymosi kortelių kūrimui:
📚 Upload PDF/nuotrauką → Gauni flashcard'us per 10 sek

Beta testeriai gauna:
✅ NEMOKAMAS Premium (vietoj €3.99/mėn)
✅ Early access naujoms funkcijoms
✅ Direct line su developer'iu

Reikia tik:
📝 Testuoti 1 savaitę
💬 Duoti feedback (5 min survey)

Link: [tavo-app-url]
PM jei įdomu! 🚀
```

### Feedback forma (Google Forms)

**Klausimai:**
1. Kiek flashcard'ų sukūrėte?
2. Kurią funkciją naudojote dažniausiai? (Text/PDF/Nuotrauka)
3. Kokia flashcard'ų kokybė (1-10)?
4. Kas patiko labiausiai?
5. Kas erzino / nepatiko?
6. Ar mokėtumėte €3.99/mėn už Premium?
7. Kokią kainą siūlytumėte? (€/mėn)
8. Email (optional - gauti Premium early access)

---

## 💰 Monetizacija (Savaitė 4)

### Stripe Setup

#### 1. Registracija
1. Eik į https://dashboard.stripe.com/register
2. Sukurk accountą (Lithuania)
3. Complete verification (reikės ID dokumento)

#### 2. Gauk API keys
1. Dashboard → Developers → API keys
2. Kopijuok:
   - **Publishable key** (pk_test_...)
   - **Secret key** (sk_test_...)

#### 3. Sukonfigūruok Streamlit Secrets
Streamlit Cloud → App Settings → Secrets:
```toml
OPENAI_API_KEY = "sk-..."
STRIPE_PUBLIC_KEY = "pk_test_..."
STRIPE_SECRET_KEY = "sk_test_..."
```

#### 4. Test Payment
- Naudok test card: `4242 4242 4242 4242`
- Expiry: any future date
- CVC: any 3 digits

#### 5. Go Live!
Dashboard → Activate account → Gausi live keys (pk_live_..., sk_live_...)

---

## 📈 Analytics & Metrics

### Svarbiausi KPI sekti:

#### Week 1-2: Development
- [ ] App deployed successfully
- [ ] All 4 tabs working
- [ ] Export funkcijos veikia

#### Week 3: Beta test
- [ ] Beta users registered: **20-30**
- [ ] Total flashcards created: **>500**
- [ ] Positive feedback rate: **>70%**
- [ ] Willing to pay: **>40%**

#### Week 4: Launch
- [ ] Stripe integration working
- [ ] First paying customer 💰
- [ ] Goal: **10 Premium users** (€39.90/mėn)

#### Month 2-3: Growth
- [ ] **50 Premium users** (€199.50/mėn)
- [ ] **100 Premium users** (€399/mėn)
- [ ] **200 Premium users** (€798/mėn) ← Sustainable

---

## 🔧 Troubleshooting

### App nekraunasi Streamlit Cloud?

**Build logs rodo "Tesseract not found":**
→ Patikrink ar yra `packages.txt` file su:
```
tesseract-ocr
tesseract-ocr-lit
tesseract-ocr-eng
```

**OpenAI API error:**
→ Patikrink Secrets sintaksę (turi būti TOML formatas):
```toml
OPENAI_API_KEY = "sk-..."
```
NOT:
```
OPENAI_API_KEY=sk-...  # WRONG
```

**PDF tekstas tuščias:**
→ PDF yra skanuota nuotrauka, ne tekstinis failas
→ Sprendimas: naudok Tab 3 (Nuotrauka) vietoj PDF

### Tesseract OCR neatpažįsta lietuviškų raidžių?

```bash
# Patikrink ar įdiegtas lietuvių kalbos paketas
tesseract --list-langs

# Turėtų būti:
# lit (Lithuanian)
# eng (English)

# Jei ne:
brew install tesseract-lang  # macOS
sudo apt-get install tesseract-ocr-lit  # Linux
```

---

## 📞 Support

### Problemos deployment'e?
1. Check build logs: Streamlit Cloud → Logs
2. GitHub Issues: `<your-repo>/issues`

### Beta testerių klausimai?
- Email: your-email@example.com
- Discord: [optional community]

---

## 🎯 Next Steps Checklist

- [ ] Deploy MVP į Streamlit Cloud
- [ ] Test visas 4 funkcijas
- [ ] Post beta tester ad Facebook grupėse
- [ ] Surinkti 20 beta testerių
- [ ] Feedback survey po 1 savaitės
- [ ] Integrate Stripe payments
- [ ] Launch marketing (Instagram/TikTok)
- [ ] First 10 paying customers 🎉

---

**Good luck! 🚀**
