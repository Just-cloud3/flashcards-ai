# Supabase Client for FlashCards AI
import os
from supabase import create_client, Client
from datetime import datetime, timedelta

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://dznzrxcvexmrqyctxogn.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR6bnpyeGN2ZXhtcnF5Y3R4b2duIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA0OTg0NDUsImV4cCI6MjA4NjA3NDQ0NX0.LHoa_2vp_89bAbl9MDC3sErq3l6hj0WDfR68ymUqK5A")

_supabase_client = None

def get_supabase() -> Client:
    """Get or create Supabase client"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client

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
    """Sign out current user"""
    try:
        supabase = get_supabase()
        supabase.auth.sign_out()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_current_user():
    """Get current logged in user"""
    try:
        supabase = get_supabase()
        return supabase.auth.get_user()
    except:
        return None

# ========================
# FLASHCARD FUNCTIONS
# ========================

def save_flashcard_set(user_id: str, name: str, cards: list):
    """Save a set of flashcards to database"""
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
        
        supabase.table("flashcards").insert(cards_to_insert).execute()
        
        return {"success": True, "set_id": set_id}
    except Exception as e:
        return {"success": False, "error": str(e)}

def load_user_flashcards(user_id: str):
    """Load all flashcards for a user"""
    try:
        supabase = get_supabase()
        
        # Get user's sets
        sets = supabase.table("flashcard_sets").select("*").eq("user_id", user_id).execute()
        
        all_cards = []
        for card_set in sets.data:
            cards = supabase.table("flashcards").select("*").eq("set_id", card_set["id"]).execute()
            for card in cards.data:
                all_cards.append({
                    "id": card["id"],
                    "set_id": card["set_id"],
                    "klausimas": card["question"],
                    "atsakymas": card["answer"],
                    "difficulty": card["difficulty"],
                    "next_review": card["next_review"],
                    "times_reviewed": card["times_reviewed"]
                })
        
        return {"success": True, "cards": all_cards}
    except Exception as e:
        return {"success": False, "error": str(e), "cards": []}

def update_card_progress(card_id: str, difficulty: int):
    """Update card's spaced repetition progress"""
    try:
        supabase = get_supabase()
        
        # Calculate next review based on difficulty
        intervals = {1: 1, 2: 1, 3: 3, 4: 7, 5: 14}
        days = intervals.get(difficulty, 3)
        next_review = (datetime.now() + timedelta(days=days)).isoformat()
        
        supabase.table("flashcards").update({
            "difficulty": difficulty,
            "next_review": next_review,
            "times_reviewed": supabase.table("flashcards").select("times_reviewed").eq("id", card_id).execute().data[0]["times_reviewed"] + 1
        }).eq("id", card_id).execute()
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_cards_for_review(user_id: str):
    """Get cards that need review today"""
    try:
        supabase = get_supabase()
        today = datetime.now().isoformat()
        
        # Get user's sets
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
                    "id": c["id"],
                    "klausimas": c["question"],
                    "atsakymas": c["answer"],
                    "difficulty": c["difficulty"]
                }
                for c in cards.data
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e), "cards": []}

def delete_flashcard_set(set_id: str):
    """Delete a flashcard set and all its cards"""
    try:
        supabase = get_supabase()
        supabase.table("flashcard_sets").delete().eq("id", set_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
