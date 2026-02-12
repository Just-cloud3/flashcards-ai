# ⚛️ QUANTUM — Išmanus Mokymosi Platforma

**QUANTUM** yra AI-valdoma flashcard'ų platforma, sukurta Lietuvos studentams. Sukurkite mokymosi korteles iš bet kokio teksto, PDF, YouTube video ar nuotraukos per kelias sekundes.

## ✨ Funkcijos

- 📝 **AI kortelių generavimas** — iš teksto, PDF, YouTube, nuotraukų
- 📸 **Multi-image upload** — kelios nuotraukos vienu metu
- 🧠 **Spaced Repetition** — mokymasis su intervalais
- ⚡ **Egzamino režimas** — laikinas testas su rezultatais
- 🎴 **3D Flip kortelės** — interaktyvi peržiūra
- 🔊 **TTS (Text-to-Speech)** — klausykite klausimų ir atsakymų
- 💬 **AI Tutor** — klauskite AI apie savo korteles
- 👥 **Bendruomenė** — dalinkitės rinkiniais, kopijuokite kitų
- 🔥 **Streak counter** — motyvacija mokytis kasdien
- 💎 **Premium** — neribotos kortelės su Stripe prenumerata
- 🌙 **Dark mode** — patogi naktį
- 📱 **Mobile friendly** — veikia telefonuose

## 🚀 Greitas Startas

### 1. Klonuokite projektą
```bash
git clone https://github.com/Just-cloud3/flashcards-ai.git
cd flashcards-ai
```

### 2. Įdiekite priklausomybes
```bash
pip install -r requirements.txt
```

### 3. Nustatykite aplinkos kintamuosius
Sukurkite `.env` failą:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
STRIPE_SECRET_KEY=your_stripe_key
STRIPE_PUBLIC_KEY=your_stripe_public_key
APP_BASE_URL=http://localhost:8501
```

### 4. Paleiskite
```bash
streamlit run app.py
```

## 🗄️ Duomenų bazė (Supabase)

Projektas naudoja Supabase (PostgreSQL). Reikalingos lentelės:
- `profiles` — vartotojų profiliai, premium statusas, streak
- `flashcard_sets` — kortelių rinkiniai
- `flashcards` — atskiros kortelės su spaced repetition duomenimis

## 💳 Mokėjimai (Stripe)

- €3.99/mėn Premium prenumerata
- Stripe Checkout + Billing Portal
- Test režimas: kortelė `4242 4242 4242 4242`

## 🛠️ Technologijos

| Technologija | Paskirtis |
|---|---|
| **Streamlit** | Frontend + Backend |
| **Google Gemini 2.0** | AI kortelių generavimas |
| **Supabase** | PostgreSQL DB + Auth |
| **Stripe** | Mokėjimai |
| **gTTS** | Text-to-Speech |
| **PyPDF2** | PDF apdorojimas |

## 📄 Licencija

© 2026 QUANTUM. Visos teisės saugomos.
