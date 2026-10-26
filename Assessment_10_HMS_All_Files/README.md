# Assessment 10 — HMS AI Complaint Assistant

## AI feature
A local machine-learning prototype that suggests a category for a complaint and a review priority. It uses TF-IDF text features and a Logistic Regression classifier trained on a small, illustrative synthetic dataset. Urgency terms (e.g. threat, sparking, fire) trigger a High-priority suggestion.

## Important limitation
This is a demonstrator, not a validated production model. The training examples are synthetic and small. The model must be evaluated with real, consented, anonymized complaints before real deployment. AI suggestions must never automatically close/reject complaints or replace a warden's judgement. Safety-related complaints need a clear human escalation path.

## Run the demo
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python demo.py
```

## Integration concept
1. Keep the existing Flask/MySQL HMS modules.
2. In the complaint form, call `/api/complaints/ai-suggestion` after the student enters a description.
3. Show category, suggested priority, confidence and explanation as editable suggestions.
4. On final submission, save the complaint and the human-confirmed category/priority using the existing complaint persistence code.
5. Log corrections for later evaluation, with access controls and retention limits.

`flask_integration_example.py` is an adapter example only. It assumes the existing Flask app has an `app` object and is not a drop-in replacement for unknown project code.
