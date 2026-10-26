# Example adapter for an existing Flask HMS complaint route.
# Merge the relevant lines into your current route; don't replace the whole app.
from flask import request, jsonify
from hms_ai import classify_complaint

@app.post("/api/complaints/ai-suggestion")
def ai_complaint_suggestion():
    payload = request.get_json(silent=True) or {}
    complaint_text = payload.get("description", "")
    try:
        suggestion = classify_complaint(complaint_text)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    # Return a suggestion only. The student/warden can edit it before saving.
    return jsonify(suggestion), 200
