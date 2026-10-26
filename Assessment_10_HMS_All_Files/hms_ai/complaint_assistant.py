"""
HMS AI Complaint Assistant
A small, local ML prototype for classifying hostel complaints and suggesting urgency.
This is an integration module, not a replacement for the existing HMS application.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

TRAINING_DATA = [
    ("Water is leaking from the bathroom pipe", "Plumbing"),
    ("No water supply in our floor", "Plumbing"),
    ("Tap is broken and the sink is overflowing", "Plumbing"),
    ("Drain is blocked and smells bad", "Plumbing"),
    ("The toilet flush is not working", "Plumbing"),
    ("The room light is not working", "Electrical"),
    ("Power socket is sparking", "Electrical"),
    ("Fan stopped working and room is hot", "Electrical"),
    ("There is a power cut in our block", "Electrical"),
    ("The switchboard is damaged", "Electrical"),
    ("Food was cold and had insects", "Mess/Food"),
    ("The mess served spoiled food", "Mess/Food"),
    ("Dinner quality is poor", "Mess/Food"),
    ("There was a stone in the rice", "Mess/Food"),
    ("The dining area is dirty", "Mess/Food"),
    ("Room has not been cleaned for days", "Cleanliness"),
    ("Garbage has not been collected", "Cleanliness"),
    ("Bathroom floor is dirty", "Cleanliness"),
    ("There are insects in the room", "Cleanliness"),
    ("Common area needs cleaning", "Cleanliness"),
    ("Someone is making loud noise at night", "Noise/Discipline"),
    ("Students are playing music loudly after quiet hours", "Noise/Discipline"),
    ("A visitor is entering without permission", "Noise/Discipline"),
    ("There is a disturbance in the corridor", "Noise/Discipline"),
    ("Roommate keeps disturbing sleep", "Noise/Discipline"),
    ("My cupboard lock is broken", "Maintenance"),
    ("Window handle is damaged", "Maintenance"),
    ("Bed frame is broken", "Maintenance"),
    ("The door does not close properly", "Maintenance"),
    ("Desk and chair are damaged", "Maintenance"),
    ("I feel unsafe because someone threatened me", "Safety"),
    ("There is a serious security concern near the gate", "Safety"),
    ("Someone is harassing a student", "Safety"),
    ("A stranger is trying to enter the hostel", "Safety"),
    ("I need help immediately because of a threat", "Safety"),
]

URGENT_TERMS = [
    "fire", "smoke", "sparking", "electric shock", "threat", "harass",
    "unsafe", "violence", "injury", "emergency", "gas leak", "stranger"
]

@dataclass
class ComplaintSuggestion:
    category: str
    priority: str
    confidence: float
    explanation: str

class ComplaintAssistant:
    def __init__(self) -> None:
        self.model = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced"))
        ])
        texts, labels = zip(*TRAINING_DATA)
        self.model.fit(list(texts), list(labels))

    def predict(self, complaint_text: str) -> Dict:
        text = re.sub(r"\s+", " ", (complaint_text or "").strip())
        if len(text) < 8:
            raise ValueError("Please enter a complaint with at least 8 characters.")
        probs = self.model.predict_proba([text])[0]
        classes = self.model.named_steps["classifier"].classes_
        best_index = int(probs.argmax())
        category = str(classes[best_index])
        confidence = float(probs[best_index])
        lower = text.lower()
        urgent_hits = [term for term in URGENT_TERMS if term in lower]
        if urgent_hits:
            priority = "High"
            explanation = "Urgency keyword detected: " + ", ".join(urgent_hits[:3])
        elif category in {"Plumbing", "Electrical", "Safety"}:
            priority = "Medium"
            explanation = f"Category-based suggestion: {category} issues should be reviewed promptly."
        else:
            priority = "Normal"
            explanation = f"Suggested from complaint category: {category}."
        return asdict(ComplaintSuggestion(category, priority, round(confidence, 3), explanation))

assistant = ComplaintAssistant()

def classify_complaint(text: str) -> Dict:
    """Call this from the HMS complaint-submission route."""
    return assistant.predict(text)
