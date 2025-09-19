from typing import List, Optional
import re

# Banned terms Walmart does not allow
BANNED_WORDS = ["cosplay", "weapon", "knife", "uv", "premium", "perfect", "outstanding", "remarkable", "superior", "excellent", "exceptional", "amazing", "fantastic", "incredible", "wonderful", "brilliant", "magnificent", "spectacular", "extraordinary", "phenomenal"]

# Regex patterns that indicate medical claims
MEDICAL_PATTERNS = [r"\bcure\b", r"\btreat\b", r"\bdiagnose\b", r"\bprevent\b", r"\bheal\b", r"\bsteriliz\b", r"\bgerm-fight\b", r"\bantimicrobial\b", r"\bantibacterial\b", r"\btherapeutic\b", r"\bmedicinal\b", r"\bclinical\b"]


def count_words(text: str) -> int:
    tokens = re.findall(r"\b\w+\b", text or "")
    return len(tokens)


def check_banned_words(text: str) -> List[str]:
    if not text:
        return []
    lower = text.lower()
    return [w for w in BANNED_WORDS if re.search(rf"\b{re.escape(w)}\b", lower)]


def validate_title(title: str, brand: Optional[str] = None) -> List[str]:
    violations: List[str] = []
    if not title or not title.strip():
        return ["title is empty"]
    if len(title) > 150:
        violations.append("title exceeds 150 characters")
    if brand and brand.lower() not in title.lower():
        violations.append("brand missing in title")
    violations.extend([f"banned word in title: {w}" for w in check_banned_words(title)])
    return violations


def validate_meta_title(meta_title: str) -> List[str]:
    violations: List[str] = []
    if not meta_title or not meta_title.strip():
        return ["meta_title is empty"]
    if len(meta_title) > 70:
        violations.append("meta_title exceeds 70 characters")
    violations.extend([f"banned word in meta_title: {w}" for w in check_banned_words(meta_title)])
    return violations


def validate_meta_desc(meta_desc: str) -> List[str]:
    violations: List[str] = []
    if not meta_desc or not meta_desc.strip():
        return ["meta_description is empty"]
    if len(meta_desc) > 160:
        violations.append("meta_description exceeds 160 characters")
    violations.extend([f"banned word in meta_description: {w}" for w in check_banned_words(meta_desc)])
    return violations


def validate_description_length(description: str, brand: Optional[str] = None) -> List[str]:
    violations: List[str] = []
    wc = count_words(description or "")
    if wc < 120 or wc > 160:
        violations.append("description word count not in 120–160 range")
    if brand and brand.lower() not in (description or "").lower():
        violations.append("brand missing in description")
    violations.extend([f"banned word in description: {w}" for w in check_banned_words(description or "")])
    return violations


def validate_bullets(bullets_str: str) -> List[str]:
    violations: List[str] = []
    if not bullets_str or not isinstance(bullets_str, str):
        return ["bullets is empty or not a string"]

    # Extract <li> items
    li_pattern = r'<li[^>]*>(.*?)</li>'
    li_matches = re.findall(li_pattern, bullets_str, re.IGNORECASE | re.DOTALL)

    if len(li_matches) != 8:
        violations.append(f"bullets must contain exactly 8 items, found {len(li_matches)}")

    for idx, bullet_content in enumerate(li_matches):
        if len(bullet_content.strip()) > 85:
            violations.append(f"bullet {idx+1} exceeds 85 characters")
        violations.extend([f"banned word in bullet {idx+1}: {w}" for w in check_banned_words(bullet_content)])

    return violations


def validate_no_medical_claims(text: str) -> List[str]:
    """Detect medical claims in text and report which pattern was matched."""
    if not text:
        return []
    lower = text.lower()
    violations = []
    for pat in MEDICAL_PATTERNS:
        if re.search(pat, lower):
            # Clean pattern for human-readable message
            label = re.sub(r"\\b", "", pat)
            violations.append(f"medical claim detected: {label}")
    return violations


def validate_product_output(output_dict: dict, input_keywords: Optional[List[str]], brand: Optional[str]) -> List[str]:
    violations: List[str] = []

    title = output_dict.get("title", "")
    bullets = output_dict.get("bullets", "")
    description = output_dict.get("description", "")
    meta_title = output_dict.get("meta_title", "")
    meta_description = output_dict.get("meta_description", "")

    # Run validations
    violations.extend(validate_title(title, brand))
    violations.extend(validate_bullets(bullets))
    violations.extend(validate_description_length(description, brand))
    violations.extend(validate_meta_title(meta_title))
    violations.extend(validate_meta_desc(meta_description))

    # Extract bullet text for medical + keyword checks
    bullet_content = ""
    if bullets:
        li_pattern = r'<li[^>]*>(.*?)</li>'
        li_matches = re.findall(li_pattern, bullets, re.IGNORECASE | re.DOTALL)
        bullet_content = " ".join(li_matches)

    violations.extend(validate_no_medical_claims(" ".join([title, description, meta_title, meta_description, bullet_content])))

    # Keyword presence check
    if input_keywords:
        joined = (" ".join([title, description, bullet_content])).lower()
        for kw in input_keywords:
            if kw and str(kw).lower() not in joined:
                violations.append(f"keyword not present: {kw}")

    return violations


# For backwards compatibility in tests
def validate_required_fields(rows: List[dict], required_fields: List[str]):
    issues = []
    for idx, row in enumerate(rows):
        for field in required_fields:
            if not row.get(field):
                issues.append({"row_index": idx, "field": field, "message": "Missing or empty"})
    return issues
