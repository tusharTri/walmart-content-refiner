from typing import List, Tuple
import re

BANNED_WORDS = ["cosplay", "weapon", "knife", "uv", "premium", "perfect"]


def count_words(text: str) -> int:
    tokens = re.findall(r"\b\w+\b", text or "")
    return len(tokens)


def check_banned_words(text: str) -> List[str]:
    if not text:
        return []
    lower = text.lower()
    found = []
    for w in BANNED_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", lower):
            found.append(w)
    return found


def validate_title(title: str, brand: str | None = None) -> List[str]:
    violations: List[str] = []
    if title is None or not title.strip():
        violations.append("title is empty")
        return violations
    if len(title) > 150:
        violations.append("title exceeds 150 characters")
    if brand and brand.lower() not in title.lower():
        violations.append("brand missing in title")
    violations.extend([f"banned word in title: {w}" for w in check_banned_words(title)])
    return violations


def validate_meta_title(meta_title: str) -> List[str]:
    violations: List[str] = []
    if meta_title is None or not meta_title.strip():
        violations.append("meta_title is empty")
        return violations
    if len(meta_title) > 70:
        violations.append("meta_title exceeds 70 characters")
    violations.extend([f"banned word in meta_title: {w}" for w in check_banned_words(meta_title)])
    return violations


def validate_meta_desc(meta_desc: str) -> List[str]:
    violations: List[str] = []
    if meta_desc is None or not meta_desc.strip():
        violations.append("meta_description is empty")
        return violations
    if len(meta_desc) > 160:
        violations.append("meta_description exceeds 160 characters")
    violations.extend([f"banned word in meta_description: {w}" for w in check_banned_words(meta_desc)])
    return violations


def validate_description_length(description: str, brand: str | None = None) -> List[str]:
    violations: List[str] = []
    wc = count_words(description or "")
    if wc < 120 or wc > 160:
        violations.append("description word count not in 120–160 range")
    if brand and brand.lower() not in (description or "").lower():
        violations.append("brand missing in description")
    violations.extend([f"banned word in description: {w}" for w in check_banned_words(description or "")])
    return violations


def validate_bullets(bullets_list: List[str]) -> List[str]:
    violations: List[str] = []
    if not isinstance(bullets_list, list):
        return ["bullets is not a list"]
    if len(bullets_list) != 8:
        violations.append("bullets must contain exactly 8 items")
    for idx, b in enumerate(bullets_list):
        if len(b or "") > 85:
            violations.append(f"bullet {idx+1} exceeds 85 characters")
        violations.extend([f"banned word in bullet {idx+1}: {w}" for w in check_banned_words(b or "")])
    return violations


MEDICAL_PATTERNS = [r"\bcure\b", r"\btreat\b", r"\bdiagnose\b", r"\bprevent\b"]


def validate_no_medical_claims(text: str) -> List[str]:
    if not text:
        return []
    lower = text.lower()
    v = []
    for pat in MEDICAL_PATTERNS:
        if re.search(pat, lower):
            v.append("medical claim detected")
            break
    return v


def validate_product_output(output_dict: dict, input_keywords: List[str] | None, brand: str | None) -> List[str]:
    violations: List[str] = []
    title = output_dict.get("title", "")
    bullets = output_dict.get("bullets", [])
    description = output_dict.get("description", "")
    meta_title = output_dict.get("meta_title", "")
    meta_description = output_dict.get("meta_description", "")

    violations.extend(validate_title(title, brand))
    violations.extend(validate_bullets(bullets))
    violations.extend(validate_description_length(description, brand))
    violations.extend(validate_meta_title(meta_title))
    violations.extend(validate_meta_desc(meta_description))
    violations.extend(validate_no_medical_claims(" ".join([title, description, meta_title, meta_description] + list(bullets or []))))

    # Keyword presence (attributes/keywords) check - soft requirement, but record if missing
    if input_keywords:
        joined = " ".join([title, description] + list(bullets or []))).lower()
        for kw in input_keywords:
            if kw and str(kw).lower() not in joined:
                violations.append(f"keyword not present: {kw}")

    # Banned words at overall level already included in other checks
    return violations


# Backwards-compatible function kept for tests that rely on it
def validate_required_fields(rows: List[dict], required_fields: List[str]):
    issues = []
    for idx, row in enumerate(rows):
        for field in required_fields:
            if not row.get(field):
                issues.append({"row_index": idx, "field": field, "message": "Missing or empty"})
    return issues
