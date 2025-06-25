from difflib import SequenceMatcher
from services.config import SIMILARITY_THRESHOLD, FACE_SIMILARITY_THRESHOLD

def get_similarity_score(a, b):
    if not a or not b:
        return 0
    return round(SequenceMatcher(None, a.strip(), b.strip()).ratio() * 100)

def validate_fields(page1_data, page2_data):
    fields = ["name", "father_name", "dob", "pan"]
    field_scores = {}
    field_pass = True
    errors = []
    
    for f in fields:
        score = get_similarity_score(page1_data.get(f), page2_data.get(f))
        passed = score >= SIMILARITY_THRESHOLD
        field_scores[f] = {
            "score": score, 
            "pass": passed,
            "page1_value": page1_data.get(f),
            "page2_value": page2_data.get(f)
        }
        if not passed:
            field_pass = False
            errors.append({
                "code": f"{f.upper()}_MISMATCH",
                "message": f"{f.replace('_', ' ').title()} differs between Page 1 and PAN card"
            })
    
    return field_scores, field_pass, errors

def validate_face_match(similarity):
    if similarity is None:
        return False, {
            "code": "FACE_MATCH_ERROR",
            "message": "Could not process face comparison"
        }
    
    face_pass = similarity >= FACE_SIMILARITY_THRESHOLD
    return face_pass, None