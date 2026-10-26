from hms_ai import classify_complaint

examples = [
    "Water is leaking from the bathroom pipe",
    "Power socket is sparking and I feel unsafe",
    "The mess served spoiled food",
    "Someone is threatening me near the hostel gate",
]
for complaint in examples:
    print(f"\nComplaint: {complaint}")
    print(classify_complaint(complaint))
