# Supabase Client for FlashCards AI
import os
from supabase import create_client, Client
from datetime import datetime, timedelta
import streamlit as st

# Supabase credentials (anon key is public by design - secured by RLS)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://dznzrxcvexmrqyctxogn.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR6bnpyeGN2ZXhtcnF5Y3R4b2duIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA0OTg0NDUsImV4cCI6MjA4NjA3NDQ0NX0.LHoa_2vp_89bAbl9MDC3sErq3l6hj0WDfR68ymUqK5A")


def get_supabase() -> Client:
    """Get or create Supabase client (per-session to avoid auth leaks)"""
    if 'supabase_client' not in st.session_state:
        st.session_state.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return st.session_state.supabase_client


# ========================
# AUTH FUNCTIONS
# ========================

def sign_in_with_email(email: str, password: str):
    """Sign in with email/password"""
    try:
        supabase = get_supabase()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return {"success": True, "user": response.user, "session": response.session}
    except Exception as e:
        return {"success": False, "error": str(e)}


def sign_up_with_email(email: str, password: str):
    """Sign up with email/password"""
    try:
        supabase = get_supabase()
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        return {"success": True, "user": response.user}
    except Exception as e:
        return {"success": False, "error": str(e)}


def sign_out():
    """Sign out current user and clear session client"""
    try:
        supabase = get_supabase()
        supabase.auth.sign_out()
        # Clear client so next login gets fresh auth state
        if 'supabase_client' in st.session_state:
            del st.session_state.supabase_client
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_current_user():
    """Get current logged in user"""
    try:
        supabase = get_supabase()
        return supabase.auth.get_user()
    except Exception:
        return None


# ========================
# FLASHCARD FUNCTIONS
# ========================

def save_flashcard_set(user_id: str, name: str, cards: list):
    """Save a set of flashcards to database. Returns DB card IDs."""
    try:
        supabase = get_supabase()

        # Create set
        set_response = supabase.table("flashcard_sets").insert({
            "user_id": user_id,
            "name": name
        }).execute()

        set_id = set_response.data[0]["id"]

        # Insert cards
        cards_to_insert = [
            {
                "set_id": set_id,
                "question": card.get("klausimas", card.get("question", "")),
                "answer": card.get("atsakymas", card.get("answer", "")),
                "difficulty": 3,
                "next_review": datetime.now().isoformat(),
                "times_reviewed": 0
            }
            for card in cards
        ]

        cards_response = supabase.table("flashcards").insert(cards_to_insert).execute()

        # Return database IDs so app can use them for study tracking
        db_card_ids = [str(c["id"]) for c in cards_response.data]

        return {"success": True, "set_id": set_id, "card_ids": db_card_ids}
    except Exception as e:
        return {"success": False, "error": str(e), "card_ids": []}


def load_user_flashcards(user_id: str):
    """Load all flashcards for a user (optimized: 2 queries instead of N+1)"""
    try:
        supabase = get_supabase()

        # Query 1: Get all user's set IDs
        sets = supabase.table("flashcard_sets").select("id, name").eq("user_id", user_id).execute()

        if not sets.data:
            return {"success": True, "cards": []}

        set_ids = [s["id"] for s in sets.data]

        # Query 2: Get ALL cards across all sets in one query
        cards = supabase.table("flashcards").select("*").in_("set_id", set_ids).execute()

        all_cards = [
            {
                "id": str(card["id"]),
                "set_id": card["set_id"],
                "klausimas": card["question"],
                "atsakymas": card["answer"],
                "difficulty": card.get("difficulty", 3),
                "next_review": card.get("next_review", datetime.now().isoformat()),
                "times_reviewed": card.get("times_reviewed", 0)
            }
            for card in cards.data
        ]

        return {"success": True, "cards": all_cards}
    except Exception as e:
        return {"success": False, "error": str(e), "cards": []}


def update_card_progress(card_id: str, difficulty: int):
    """Update card's spaced repetition progress (safe: separate read/write)"""
    try:
        supabase = get_supabase()

        # Read current state
        current = supabase.table("flashcards").select("times_reviewed").eq("id", card_id).execute()

        if not current.data:
            return {"success": False, "error": "Card not found"}

        times_reviewed = current.data[0].get("times_reviewed", 0) + 1

        # Calculate next review
        intervals = {1: 1, 2: 1, 3: 3, 4: 7, 5: 14}
        days = intervals.get(difficulty, 3)
        next_review = (datetime.now() + timedelta(days=days)).isoformat()

        # Update
        supabase.table("flashcards").update({
            "difficulty": difficulty,
            "next_review": next_review,
            "times_reviewed": times_reviewed
        }).eq("id", card_id).execute()

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_cards_for_review(user_id: str):
    """Get cards that need review today"""
    try:
        supabase = get_supabase()
        today = datetime.now().isoformat()

        # Get user's set IDs
        sets = supabase.table("flashcard_sets").select("id").eq("user_id", user_id).execute()
        set_ids = [s["id"] for s in sets.data]

        if not set_ids:
            return {"success": True, "cards": []}

        # Get cards due for review
        cards = supabase.table("flashcards").select("*").in_("set_id", set_ids).lte("next_review", today).execute()

        return {
            "success": True,
            "cards": [
                {
                    "id": str(c["id"]),
                    "klausimas": c["question"],
                    "atsakymas": c["answer"],
                    "difficulty": c.get("difficulty", 3)
                }
                for c in cards.data
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e), "cards": []}


def delete_flashcard_set(set_id: str):
    """Delete a flashcard set and all its cards (manual cascade)"""
    try:
        supabase = get_supabase()
        # Delete cards first (safe even if DB has cascade)
        supabase.table("flashcards").delete().eq("set_id", set_id).execute()
        # Then delete the set
        supabase.table("flashcard_sets").delete().eq("id", set_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
# ========================
# PREMIUM / USER PROFILE
# ========================

def get_user_profile(user_id: str):
    """Get full user profile (premium status, subscription info)"""
    try:
        supabase = get_supabase()
        result = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if result.data:
            return result.data[0]

        # If no profile, create one
        supabase.table("profiles").insert({
            "id": user_id,
            "is_premium": False,
            "subscription_id": None,
            "stripe_customer_id": None
        }).execute()
        return {"id": user_id, "is_premium": False, "subscription_id": None, "stripe_customer_id": None}
    except Exception:
        return {"id": user_id, "is_premium": False, "subscription_id": None, "stripe_customer_id": None}


def get_user_premium_status(user_id: str):
    """Check if user has premium status"""
    profile = get_user_profile(user_id)
    return profile.get("is_premium", False)


def set_user_premium_status(user_id: str, status: bool, subscription_id=None, stripe_customer_id=None):
    """Update user's premium status and Stripe info"""
    try:
        supabase = get_supabase()
        data = {"id": user_id, "is_premium": status}
        if subscription_id is not None:
            data["subscription_id"] = subscription_id
        if stripe_customer_id is not None:
            data["stripe_customer_id"] = stripe_customer_id
        supabase.table("profiles").upsert(data).execute()
        return True
    except Exception:
        return False


# ========================
# GDPR / BDAR FUNCTIONS
# ========================

def export_user_data(user_id: str, email: str):
    """BDAR Art. 20 - Export all user's personal data as JSON"""
    try:
        supabase = get_supabase()

        # Get all sets
        sets = supabase.table("flashcard_sets").select("*").eq("user_id", user_id).execute()
        set_ids = [s["id"] for s in sets.data] if sets.data else []

        # Get all cards
        all_cards = []
        if set_ids:
            cards = supabase.table("flashcards").select("*").in_("set_id", set_ids).execute()
            all_cards = cards.data if cards.data else []

        return {
            "success": True,
            "data": {
                "vartotojas": {
                    "id": user_id,
                    "el_pastas": email,
                    "eksporto_data": datetime.now().isoformat()
                },
                "korteliu_rinkiniai": sets.data if sets.data else [],
                "korteles": all_cards
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_user_account(user_id: str):
    """BDAR Art. 17 - Delete all user data (right to be forgotten)"""
    try:
        supabase = get_supabase()

        # 1. Get all user's sets
        sets = supabase.table("flashcard_sets").select("id").eq("user_id", user_id).execute()
        set_ids = [s["id"] for s in sets.data] if sets.data else []

        # 2. Delete all cards from all sets
        if set_ids:
            supabase.table("flashcards").delete().in_("set_id", set_ids).execute()

        # 3. Delete all sets
        supabase.table("flashcard_sets").delete().eq("user_id", user_id).execute()

        # 4. Sign out (clears auth session)
        supabase.auth.sign_out()
        if 'supabase_client' in st.session_state:
            del st.session_state.supabase_client

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
