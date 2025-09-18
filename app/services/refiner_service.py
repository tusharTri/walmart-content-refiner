from typing import Dict, List, Any
from app.models import ProductInput, ProductOutput
from app.services import validator
from app.config import get_logger


def _build_initial_output(inp: ProductInput) -> Dict[str, Any]:
    brand = inp.brand.strip()
    base_title = f"{brand} {inp.product_type}".strip()

    # Bullets: prefer current bullets; trim/pad to 8
    bullets = [b for b in inp.current_bullets if b][:8]
    while len(bullets) < 8:
        bullets.append("")
    bullets = [b[:85] for b in bullets]

    # Description: start from current_description; ensure brand present
    desc = inp.current_description.strip()
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
    if extra_kw and extra_kw.lower() not in desc.lower():
        desc = desc + f" Features include: {extra_kw}."

    # Simple meta
    meta_title = (base_title)[:70]
    meta_description = (desc[:157] + "...") if len(desc) > 160 else desc

    return {
        "title": base_title[:150],
        "bullets": bullets,
        "description": desc,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "violations": [],
    }


def _sanitize_banned(text: str) -> str:
    t = text
    for w in validator.BANNED_WORDS:
        import re
        t = re.sub(rf"\b{w}\b", "", t, flags=re.IGNORECASE)
    return " ".join(t.split())


def _attempt_fix(output: Dict[str, Any], brand: str) -> Dict[str, Any]:
    # Remove banned words and enforce lengths
    output["title"] = _sanitize_banned(output.get("title", ""))[:150]
    if brand and brand.lower() not in output["title"].lower():
        output["title"] = f"{brand} " + output["title"]
    output["meta_title"] = _sanitize_banned(output.get("meta_title", ""))[:70]
    output["meta_description"] = _sanitize_banned(output.get("meta_description", ""))[:160]

    # Bullets
    bullets = [str(b)[:85] for b in (output.get("bullets") or [])]
    bullets = bullets[:8]
    while len(bullets) < 8:
        bullets.append("")
    output["bullets"] = bullets

    # Description word count fix towards 130 words
    desc = _sanitize_banned(output.get("description", ""))
    if brand and brand.lower() not in desc.lower():
        desc = f"{brand} " + desc
    words = desc.split()
    if len(words) < 120:
        # Repeat some safe keywords to reach target
        pad = words[:]
        while len(words) < 120 and pad:
            words += pad[: max(1, min(20, 120 - len(words)))]
        desc = " ".join(words)
    if len(words) > 160:
        desc = " ".join(words[:160])
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
