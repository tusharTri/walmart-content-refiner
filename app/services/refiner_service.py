from typing import Dict, List, Any
from app.models import ProductInput, ProductOutput
from app.services import validator
from app.config import get_logger


def _sanitize_banned(text: str) -> str:
    t = text or ""
    for w in validator.BANNED_WORDS:
        import re
        t = re.sub(rf"\b{w}\b", "", t, flags=re.IGNORECASE)
    return " ".join(t.split())


def _safe_words(text: str) -> List[str]:
    return [w for w in (text or "").split() if w]


from typing import Optional


def _ensure_word_count(desc: str, target_min: int = 120, target_max: int = 160, extra_phrases: Optional[List[str]] = None) -> str:
    words = _safe_words(desc)
    extra_phrases = extra_phrases or []
    # pad up to min
    idx = 0
    while len(words) < target_min and extra_phrases:
        phrase_words = _safe_words(extra_phrases[idx % len(extra_phrases)])
        if not phrase_words:
            idx += 1
            if idx > 8 * len(extra_phrases):
                break
            continue
        # add a short phrase but avoid overshooting too much
        needed = target_min - len(words)
        words.extend(phrase_words[: max(1, min(len(phrase_words), needed))])
        idx += 1
        if idx > 8 * len(extra_phrases):
            break
    # trim to max
    if len(words) > target_max:
        words = words[:target_max]
    return " ".join(words)


def _gen_attribute_sentences(attrs: Dict[str, Any]) -> List[str]:
    sentences: list[str] = []
    for k, v in (attrs or {}).items():
        value = ", ".join(map(str, v)) if isinstance(v, list) else str(v)
        if not value:
            continue
        sentences.append(f"Includes {k}: {value}.")
    return sentences


def _build_initial_output(inp: ProductInput) -> Dict[str, Any]:
    brand = inp.brand.strip()
    base_title = f"{brand} {inp.product_type}".strip()

    # Bullets: prefer current bullets; sanitize, trim, pad to 8; fill from attributes if needed
    bullets = [b for b in inp.current_bullets if b]
    bullets = [_sanitize_banned(b)[:85] for b in bullets if _sanitize_banned(b)]
    attr_bullets: list[str] = []
    for k, v in (inp.attributes or {}).items():
        value = ", ".join(map(str, v)) if isinstance(v, list) else str(v)
        if value:
            attr_bullets.append(_sanitize_banned(f"{k}: {value}")[:85])
    for b in attr_bullets:
        if len(bullets) >= 8:
            break
        if b and b not in bullets:
            bullets.append(b)
    while len(bullets) < 8:
        bullets.append("")
    bullets = bullets[:8]

    # Description: start from current_description; ensure brand present
    desc = _sanitize_banned(inp.current_description.strip())
    if brand.lower() not in desc.lower():
        desc = f"{brand} " + desc

    # Attributes to weave into meta and description
    keywords: List[str] = []
    for v in (inp.attributes or {}).values():
        if isinstance(v, (str, int, float)):
            keywords.append(str(v))
        elif isinstance(v, list):
            keywords.extend([str(x) for x in v])
        elif isinstance(v, dict):
            keywords.extend([str(x) for x in v.values()])

    extra_kw = ", ".join(sorted({k for k in keywords if k}))
    attr_sentences = _gen_attribute_sentences(inp.attributes if isinstance(inp.attributes, dict) else {})
    if extra_kw and extra_kw.lower() not in desc.lower():
        desc = desc + f" Features include: {extra_kw}."
    desc = _ensure_word_count(desc, 120, 160, extra_phrases=attr_sentences)

    # Simple meta
    meta_title = (base_title)[:70]
    meta_description = desc[:160]

    return {
        "title": base_title[:150],
        "bullets": bullets,
        "description": desc,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "violations": [],
    }


def _attempt_fix(output: Dict[str, Any], brand: str) -> Dict[str, Any]:
    # Remove banned words and enforce lengths
    output["title"] = _sanitize_banned(output.get("title", ""))[:150]
    if brand and brand.lower() not in output["title"].lower():
        output["title"] = f"{brand} " + output["title"]
    output["meta_title"] = _sanitize_banned(output.get("meta_title", ""))[:70]
    output["meta_description"] = _sanitize_banned(output.get("meta_description", ""))[:160]

    # Bullets
    bullets = [_sanitize_banned(str(b))[:85] for b in (output.get("bullets") or [])]
    bullets = bullets[:8]
    while len(bullets) < 8:
        bullets.append("")
    output["bullets"] = bullets

    # Description word count fix towards 130 words
    desc = _sanitize_banned(output.get("description", ""))
    if brand and brand.lower() not in desc.lower():
        desc = f"{brand} " + desc
    # Use attribute sentences to pad if needed
    output_attrs = {}
    desc = _ensure_word_count(desc, 120, 160)
    output["description"] = desc
    return output


def refine_product(input_data: ProductInput) -> ProductOutput:
    logger = get_logger()
    # Initial draft
    draft = _build_initial_output(input_data)

    # Validate and attempt up to 2 fixes
    for _ in range(2):
        violations = validator.validate_product_output(
            draft, input_keywords=list((input_data.attributes or {}).values()), brand=input_data.brand
        )
        if not violations:
            break
        draft["violations"] = violations
        draft = _attempt_fix(draft, input_data.brand)

    output = ProductOutput(**{
        "title": draft.get("title", ""),
        "bullets": draft.get("bullets", [])[:8],
        "description": draft.get("description", ""),
        "meta_title": draft.get("meta_title", "")[:70],
        "meta_description": draft.get("meta_description", "")[:160],
        "violations": list(draft.get("violations", [])),
    })
    return output


def fix_output_violations(original: Dict[str, Any], violations: List[str], brand: str) -> ProductOutput:
    # Start from original and only fix specified violations
    draft = {
        "title": original.get("title", ""),
        "bullets": list(original.get("bullets", [])),
        "description": original.get("description", ""),
        "meta_title": original.get("meta_title", ""),
        "meta_description": original.get("meta_description", ""),
        "violations": list(original.get("violations", [])),
    }

    vset = {v.lower() for v in violations}

    if any("banned" in v for v in vset):
        draft["title"] = _sanitize_banned(draft["title"]) or draft["title"]
        draft["meta_title"] = _sanitize_banned(draft["meta_title"]) or draft["meta_title"]
        draft["meta_description"] = _sanitize_banned(draft["meta_description"]) or draft["meta_description"]
        draft["description"] = _sanitize_banned(draft["description"]) or draft["description"]
        draft["bullets"] = [_sanitize_banned(str(b)) for b in draft.get("bullets", [])]

    if any("bullets" in v for v in vset):
        bs = [str(b)[:85] for b in (draft.get("bullets") or [])][:8]
        while len(bs) < 8:
            bs.append("")
        draft["bullets"] = bs

    if any("description" in v for v in vset):
        if brand and brand.lower() not in (draft.get("description") or "").lower():
            draft["description"] = f"{brand} " + (draft.get("description") or "")
        draft["description"] = _ensure_word_count(draft.get("description") or "", 120, 160)

    if any("meta title" in v for v in vset):
        draft["meta_title"] = (draft.get("meta_title") or "")[:70]
    if any("meta description" in v for v in vset):
        draft["meta_description"] = (draft.get("meta_description") or "")[:160]

    if any("brand" in v for v in vset):
        if brand and brand.lower() not in (draft.get("title") or "").lower():
            draft["title"] = f"{brand} " + (draft.get("title") or "")
        if brand and brand.lower() not in (draft.get("description") or "").lower():
            draft["description"] = f"{brand} " + (draft.get("description") or "")

    out = ProductOutput(**{
        "title": draft["title"][:150],
        "bullets": (draft.get("bullets") or [])[:8],
        "description": draft.get("description") or "",
        "meta_title": draft.get("meta_title") or "",
        "meta_description": draft.get("meta_description") or "",
        "violations": [],
    })
    # Re-validate to capture remaining violations
    remaining = validator.validate_product_output(out.dict(), None, brand)
    out.violations = remaining
    return out
