"""
STRIPE PAYMENT INTEGRATION (FASE 4)
====================================

Pridėk šį kodą į app.py kai būsi pasirengęs monetizacijai.

Setup:
1. pip install stripe
2. Registruokis: https://dashboard.stripe.com/register
3. Gauk API keys: https://dashboard.stripe.com/apikeys
4. Pridėk į .env:
   STRIPE_PUBLIC_KEY=pk_test_...
   STRIPE_SECRET_KEY=sk_test_...
"""

import stripe
import os

# Stripe configuration
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def create_checkout_session(customer_email=None):
    """Create Stripe checkout session for Premium subscription"""
    if not stripe.api_key:
        return None
        
    try:
        # Base URL for redirct
        base_url = "https://flashcards-ai-alkzzpbrvujame5y86dxzg.streamlit.app"
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': 'FlashCards AI Premium',
                            'description': 'Neriboti flashcard\'ai + Didesni failų limitai',
                        },
                        'unit_amount': 399,  # €3.99
                        'recurring': {'interval': 'month'},
                    },
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=f'{base_url}/?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{base_url}/',
            customer_email=customer_email,
        )
        return checkout_session.url
    except Exception as e:
        print(f"Stripe Checkout Error: {e}")
        return None

def verify_stripe_session(session_id):
    """Verify if a Stripe session was completed successfully"""
    if not stripe.api_key or not session_id:
        return False
        
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session.payment_status == "paid"
    except Exception as e:
        print(f"Stripe Verification Error: {e}")
        return False

# ========================================
# PRIDĖK Į SIDEBAR (app.py)
# ========================================

"""
# In sidebar section:

if st.session_state.flashcards_count >= 20 and not st.session_state.is_premium:
    st.warning("⚠️ Pasiekėte nemokamą limitą!")
    st.markdown("### 💎 Premium")
    st.markdown("**€3.99/mėn**")
    st.markdown("✅ Neriboti flashcard'ai")
    st.markdown("✅ Google Vision OCR")
    st.markdown("✅ Prioritetinis palaikymas")
    
    if st.button("🚀 Upgrade į Premium", type="primary"):
        import stripe_integration
        checkout_url = stripe_integration.create_checkout_session()
        if checkout_url:
            st.markdown(f"[💳 Pereiti į mokėjimą]({checkout_url})")
        else:
            st.error("Klaida kuriant mokėjimo sesija. Bandykite vėliau.")
"""

# ========================================
# WEBHOOK HANDLER (payment_webhook.py)
# ========================================

"""
Sukurk atskirą failą payment_webhook.py su FastAPI endpoint'u:

from fastapi import FastAPI, Request
import stripe
import os

app = FastAPI()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")  # From Stripe dashboard

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return {"error": "Invalid payload"}, 400
    except stripe.error.SignatureVerificationError as e:
        return {"error": "Invalid signature"}, 400
    
    # Handle successful payment
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session['customer_email']
        
        # TODO: Update database - user is now premium
        # save_premium_user(customer_email)
        
        print(f"Payment successful for {customer_email}")
    
    return {"status": "success"}
"""

# ========================================
# DATABASE SCHEMA (future)
# ========================================

"""
SQLite schema (users.db):

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    is_premium BOOLEAN DEFAULT 0,
    flashcards_count INTEGER DEFAULT 0,
    stripe_customer_id TEXT,
    subscription_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    premium_until TIMESTAMP
);

CREATE TABLE flashcards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

# ========================================
# PRICING TIERS (suggestion)
# ========================================

"""
💡 PRICING STRATEGIJA:

1. FREE TIER:
   - 20 flashcard'ų/mėn
   - Tesseract OCR only
   - Export: Anki CSV only

2. PREMIUM (€3.99/mėn):
   - Neriboti flashcard'ai
   - Google Vision OCR
   - Export: Anki + Quizlet + JSON
   - Cloud storage
   - Prioritetinis support

3. TEAM TIER (€9.99/mėn) - Future:
   - Visa Premium
   - 5 vartotojų accounts
   - Shared flashcard'ų library
   - Analytics dashboard
   
ALTERNATYVA: Pay-as-you-go
- €0.05 per flashcard
- Gerai jei vartotojai naudoja retai
- Nesreikia subscription commitment
"""

# ========================================
# EMAIL NOTIFICATIONS (SendGrid/Mailgun)
# ========================================

"""
pip install sendgrid

import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

sg = sendgrid.SendGridAPIClient(api_key=os.getenv('SENDGRID_API_KEY'))

def send_welcome_email(user_email):
    message = Mail(
        from_email='noreply@flashcardsai.lt',
        to_emails=user_email,
        subject='Sveiki atvykę į FlashCards AI Premium! 🎉',
        html_content='''
            <h2>Ačiū už pasitikėjimą!</h2>
            <p>Jūsų Premium prenumerata aktyvi.</p>
            <p>Dabar galite:</p>
            <ul>
                <li>Kurti neribotai daug flashcard'ų</li>
                <li>Naudoti Google Vision OCR</li>
                <li>Gauti prioritetinį palaikymą</li>
            </ul>
            <a href="https://your-app.streamlit.app">Pradėti naudotis →</a>
        '''
    )
    
    try:
        sg.send(message)
        print(f"Welcome email sent to {user_email}")
    except Exception as e:
        print(f"Email error: {e}")
"""
