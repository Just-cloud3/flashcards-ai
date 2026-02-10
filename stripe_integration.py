# Stripe Payment Integration for FlashCards AI
import stripe
import os

# Stripe configuration
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# App URL (set in .env or Streamlit secrets)
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://flashcards-ai-alkzzpbrvujame5y86dxzg.streamlit.app")


def create_checkout_session(customer_email=None):
    """Create Stripe checkout session for Premium subscription.
    Returns {'url': '...'} on success or {'error': '...'} on failure."""
    if not stripe.api_key:
        return {"error": "STRIPE_SECRET_KEY nenustatytas. Patikrinkite Streamlit Secrets."}

    try:
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
            success_url=f'{APP_BASE_URL}/?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{APP_BASE_URL}/',
            customer_email=customer_email,
        )
        return {"url": checkout_session.url}
    except Exception as e:
        return {"error": str(e)}


def verify_stripe_session(session_id):
    """Verify if a Stripe session was completed successfully.
    Returns dict with payment info or None on failure."""
    if not stripe.api_key or not session_id:
        return None

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            return {
                "paid": True,
                "customer_email": session.customer_details.email if session.customer_details else None,
                "subscription_id": session.subscription,
                "customer_id": session.customer,
            }
        return None
    except Exception:
        return None


def cancel_subscription(subscription_id):
    """Cancel a Stripe subscription at period end"""
    if not stripe.api_key or not subscription_id:
        return {"success": False, "error": "Nėra subscription ID"}

    try:
        # Cancel at end of billing period (not immediately)
        sub = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        return {
            "success": True,
            "cancel_at": sub.current_period_end
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_subscription_status(subscription_id):
    """Check current subscription status"""
    if not stripe.api_key or not subscription_id:
        return None

    try:
        sub = stripe.Subscription.retrieve(subscription_id)
        return {
            "status": sub.status,  # active, canceled, past_due, unpaid
            "cancel_at_period_end": sub.cancel_at_period_end,
            "current_period_end": sub.current_period_end,
        }
    except Exception:
        return None
