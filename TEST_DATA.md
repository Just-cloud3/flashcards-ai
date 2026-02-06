# Test Data - FlashCards AI

## Test tekstas (Paste į Tab 1)

```
Python Programavimo Pagrindai

1. Kintamieji ir Duomenų Tipai
Python kalboje nereikia deklaruoti kintamųjų tipo - jis nustatomas automatiškai. 
Pagrindiniai duomenų tipai: int (sveikieji skaičiai), float (slankiojo kablelio), 
str (tekstas), bool (loginis True/False), list (sąrašas), dict (žodynas).

2. Funkcijos
Funkcijos apibrėžiamos naudojant 'def' raktažodį. Pavyzdys:
def suma(a, b):
    return a + b

Funkcijos gali turėti parametrus su default reikšmėmis ir grąžinti kelias reikšmes naudojant tuple.

3. Loops (Ciklai)
For ciklas naudojamas iteruoti per seką: for i in range(10): print(i)
While ciklas kartojasi kol sąlyga teisinga: while x < 10: x += 1

4. List Comprehensions
Kompaktiškas būdas kurti sąrašus: squares = [x**2 for x in range(10)]
Galima pridėti sąlygas: evens = [x for x in range(20) if x % 2 == 0]
```

**Expected output:** ~10-15 flashcard'ų apie Python pagrindus

---

## Test PDF

Sukurk test PDF per Google Docs:
1. Eik į docs.google.com
2. Sukurk naują dokumentą
3. Įklijuok viršuje esantį tekstą
4. File → Download → PDF
5. Upload į FlashCards AI Tab 2

---

## Test nuotrauka

### Fotografuok savo konspektą arba:

1. **Screenshot iš vadovėlio:**
   - Atidaryk bet kokį PDF vadovėlį
   - Screenshot dalies puslapio
   - Upload į Tab 3

2. **Rankraštinis tekstas:**
   - Padaryk nuotrauką savo užrašų
   - Patikrink ar tekstas aiškus
   - Upload į Tab 3

### Test OCR pavyzdys:

Sukurk image su tekstu (Microsoft Word/Google Docs):

```
CHEMIJOS KONSPEKTAS

Atomai ir Molekulės
------------------
Atomas - mažiausia cheminė elemento dalelė
Molekulė - kelių atomų junginys
Elektronas - neigiamas krūvis (-1)
Protonas - teigiamas krūvis (+1)
Neutronas - neutralus krūvis (0)

Periodinė Lentelė
-----------------
118 cheminių elementų
Eilutės = Periodai (1-7)
Stulpeliai = Grupės (1-18)
```

Save as PNG → Upload į Tab 3

---

## Expected Flashcard pavyzdžiai

### Iš Python teksto:

**Flashcard 1:**
- Q: Kokie yra pagrindiniai Python duomenų tipai?
- A: int (sveikieji), float (slankiojo kablelio), str (tekstas), bool (loginis), list (sąrašas), dict (žodynas)

**Flashcard 2:**
- Q: Kaip apibrėžiama funkcija Python kalboje?
- A: Naudojant 'def' raktažodį, pavyzdžiui: def funkcija(parametras): return rezultatas

**Flashcard 3:**
- Q: Kas yra list comprehension?
- A: Kompaktiškas būdas kurti sąrašus Python kalboje, pvz: [x**2 for x in range(10)]

---

## Performance Testing

### Test su ilgu tekstu (>2000 žodžių):

Nukopijuok Wikipedia straipsnį:
https://lt.wikipedia.org/wiki/Lietuvos_istorija

Expected:
- Ekstrakcija: ~5 sek
- Generavimas: ~10-15 sek
- Rezultatas: 20-30 flashcard'ų

---

## Error Handling Tests

### Test 1: Tuščias tekstas
Input: (empty text)
Expected: Error message "Įveskite tekstą"

### Test 2: Per trumpas tekstas
Input: "Python yra programavimo kalba"
Expected: 2-3 flashcard'ai arba warning "Tekstas per trumpas gerų flashcard'ų generavimui"

### Test 3: PDF be teksto (nuotrauka)
Upload: Scanned PDF (nuotrauka, ne tekstas)
Expected: "PDF tekstas tuščias. Bandykite OCR funkciją."

### Test 4: Nuotrauka blogos kokybės
Upload: Blurred/dark image
Expected: Tesseract atpažįsta dalinai, bet AI vis tiek generuoja kažką

---

## Manual Testing Checklist

- [ ] Tab 1: Text → Flashcards works
- [ ] Tab 2: PDF upload → Extract → Flashcards
- [ ] Tab 3: Image upload → OCR → Flashcards
- [ ] Tab 4: Export Anki CSV (download veikia)
- [ ] Tab 4: Export Quizlet JSON (download veikia)
- [ ] Sidebar: Counter increases correctly
- [ ] Sidebar: Limit warning at 20 flashcards
- [ ] Edit flashcard question/answer works
- [ ] UI responsive on mobile

---

## Automation Test Script (optional)

```python
# test_app.py
import pytest
from app import generate_flashcards_from_text, extract_text_from_pdf

def test_generate_flashcards():
    text = "Python yra programavimo kalba. Ji sukurta 1991 metais."
    cards = generate_flashcards_from_text(text, num_cards=5)
    
    assert len(cards) > 0
    assert 'klausimas' in cards[0]
    assert 'atsakymas' in cards[0]

def test_pdf_extraction():
    # Mock PDF file
    with open('test.pdf', 'rb') as f:
        text = extract_text_from_pdf(f)
        assert len(text) > 0

# Run: pytest test_app.py
```
