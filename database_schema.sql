-- FlashCards AI Database Schema for Supabase
-- Run this in Supabase SQL Editor (supabase.com → SQL Editor → New Query)

-- Flashcard sets table
CREATE TABLE IF NOT EXISTS flashcard_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT 'Mano kortelės',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Flashcards table
CREATE TABLE IF NOT EXISTS flashcards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    set_id UUID REFERENCES flashcard_sets(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    difficulty INTEGER DEFAULT 3 CHECK (difficulty >= 1 AND difficulty <= 5),
    next_review TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    times_reviewed INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE flashcard_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE flashcards ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Each user sees only their own data
CREATE POLICY "Users can view own sets" ON flashcard_sets
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sets" ON flashcard_sets
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sets" ON flashcard_sets
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sets" ON flashcard_sets
    FOR DELETE USING (auth.uid() = user_id);

-- Flashcards policies (based on set ownership)
CREATE POLICY "Users can view own cards" ON flashcards
    FOR SELECT USING (
        set_id IN (SELECT id FROM flashcard_sets WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can insert own cards" ON flashcards
    FOR INSERT WITH CHECK (
        set_id IN (SELECT id FROM flashcard_sets WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can update own cards" ON flashcards
    FOR UPDATE USING (
        set_id IN (SELECT id FROM flashcard_sets WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can delete own cards" ON flashcards
    FOR DELETE USING (
        set_id IN (SELECT id FROM flashcard_sets WHERE user_id = auth.uid())
    );

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_flashcard_sets_user ON flashcard_sets(user_id);
CREATE INDEX IF NOT EXISTS idx_flashcards_set ON flashcards(set_id);
CREATE INDEX IF NOT EXISTS idx_flashcards_next_review ON flashcards(next_review);
