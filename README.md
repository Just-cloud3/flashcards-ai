# 📚 FlashCards AI - Automatinis flashcard'ų generatorius

**Sukurk mokymosi korteles iš teksto, PDF ar nuotraukų per sekundes su AI pagalba!**

---

## 🚀 Greitas startas (5 minutės)

### 1️⃣ Klonuok projektą
```bash
git clone <your-repo-url>
cd flashcard-app
```

### 2️⃣ Įdiegk priklausomybes
```bash
pip install -r requirements.txt
```

### 3️⃣ Įdiegk Tesseract OCR (nuotraukų atpažinimui)

**macOS:**
```bash
brew install tesseract
brew install tesseract-lang  # Lietuvių kalbos paketas
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-lit  # Lietuvių kalba
```

**Windows:**
1. Atsisiųsk: https://github.com/UB-Mannheim/tesseract/wiki
2. Įdiegk ir pridėk į PATH

### 4️⃣ Sukonfigūruok API key
```bash
cp .env.example .env
```

Redaguok `.env` ir įrašyk savo OpenAI API key:
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**Gauk OpenAI API key:**
1. Eik į https://platform.openai.com/api-keys
2. Sukurk naują API key
3. Nukopijuok į `.env` failą

### 5️⃣ Paleisk aplikaciją
```bash
streamlit run app.py
```

Atsidaro naršyklėje: `http://localhost:8501` 🎉

---

## 📋 Funkcionalumas

### ✅ Fase 1: Tekstas → Flashcards (DONE)
- Įklijuoji tekstą → AI sukuria flashcard'us
- Redaguojami klausimai/atsakymai
- Limitas: 20 flashcard'ų nemokamai

### ✅ Fase 2: PDF → Flashcards (DONE)
- Upload PDF failą
- Ekstraktuojamas tekstas
- Generuojami flashcard'ai

### ✅ Fase 3: Nuotrauka → Flashcards (DONE)
- Upload nuotrauką (konspektai, vadovėliai)
- OCR su Tesseract (nemokamas)
- Future: Google Vision API (premium, geresnė kokybė)

### ✅ Fase 4: Export (DONE)
- **Anki CSV** - importuok į Anki programą
- **Quizlet JSON** - importuok į Quizlet

### 🔜 Ateityje (Monetizacija)
- Stripe integracija (€3.99/mėn Premium)
- Google Vision OCR (geresnis atpažinimas)
- Neriboti flashcard'ai
- Saugojimas debesyje

---

## 💰 Kaštų apskaičiavimas

### OpenAI API (GPT-3.5-turbo)
- **Kaina:** ~$0.002 per 1,000 tokenų
- **10 flashcard'ų:** ~500 tokenų = **$0.001** (~€0.001)
- **100 flashcard'ų:** ~5,000 tokenų = **$0.01** (~€0.01)

### Pavyzdys: 200 Premium vartotojų
- Kiekvienas sukuria **100 flashcard'ų/mėn**
- Viso: **20,000 flashcard'ų**
- API cost: **~€2-3/mėn**
- Pajamos: **200 × €3.99 = €798/mėn**
- **Profit margin: ~99%** 🚀

---

## 🛠️ Deployment į Streamlit Cloud (NEMOKAMAS!)

### 1. Sukurk GitHub repo
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-url>
git push -u origin main
```

### 2. Deploy į Streamlit Cloud
1. Eik į https://streamlit.io/cloud
2. Sign in su GitHub
3. "New app" → Pasirink savo repo
4. Main file: `app.py`
5. **Secrets** → Pridėk:
   ```toml
   OPENAI_API_KEY = "sk-your-key-here"
   ```
6. Deploy! 🚀

**URL:** `https://your-app-name.streamlit.app`

---

## 📊 Testavimas su studentais

### Beta testas (Savaitė 3)

**Kur rasti studentus:**
1. **Facebook grupės:**
   - "Studijuojančių studentų grupė"
   - VU/KTU/VGTU studentų grupės
   - "Studentų nuolaidos Lietuvoje"

2. **Pasiūlymas:**
   ```
   🎓 BETA TESTERIAI IEŠKOMI!
   
   Testuoju naują AI įrankį flashcard'ų kūrimui.
   Upload PDF/nuotrauką → gauni mokymosi korteles.
   
   Beta testeriai: NEMOKAMAI PREMIUM (vietoj €3.99/mėn)!
   
   Reikia tik:
   ✅ Testuoti 1 savaitę
   ✅ Duoti feedback
   
   PM jei įdomu! Tik 20 vietų.
   ```

3. **Metrikos sekti:**
   - Kiek flashcard'ų sukurta?
   - Kokie failų formatai populiariausi?
   - Kur priekabiaujama UI?
   - Ar mokėtų €3.99/mėn?

---

## 🔧 Development roadmap

### ✅ Week 1: MVP
- [x] Text input → Flashcards
- [x] Basic UI su Streamlit

### ✅ Week 2: PDF + Deploy
- [x] PDF upload funkcionalumas
- [x] Deploy Streamlit Cloud

### 🔄 Week 3: Beta test
- [ ] 20-30 beta testerių
- [ ] Surinkti feedback
- [ ] UI patobulinimai

### 📅 Week 4: Monetizacija
- [ ] OCR nuotraukoms (Tesseract + Google Vision)
- [ ] Stripe payment integration
- [ ] Premium features

---

## 🐛 Dažniausios problemos

### "Tesseract not found"
```bash
# macOS
brew install tesseract tesseract-lang

# Linux
sudo apt-get install tesseract-ocr tesseract-ocr-lit
```

### "OpenAI API error"
- Patikrink ar teisingas API key `.env` faile
- Ar turi credits OpenAI accounte? (Check: https://platform.openai.com/account/billing)

### "PDF tekstas tuščias"
- PDF yra suskanuota nuotrauka (ne tekstinis)
- Sprendimas: Naudok OCR funkciją (Tab 3: Nuotrauka)

---

## 📞 Kontaktai

Klausimų/problemų atveju:
- GitHub Issues: `<your-repo>/issues`
- Email: `your-email@example.com`

---

## 📜 License

MIT License - naudok laisvai!

---

**Made with ❤️ for Lithuanian students**
