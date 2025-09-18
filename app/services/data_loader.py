import pandas as pd
import json
from typing import List, Dict, Any


def _safe_parse_json(cell: Any) -> Any:
    if isinstance(cell, (dict, list)):
        return cell
    if isinstance(cell, str):
        txt = cell.strip()
        if not txt:
            return {}
        try:
            return json.loads(txt)
        except Exception:
            return {"raw": txt}
    return {}


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "attributes" in df.columns:
        df["attributes"] = df["attributes"].apply(_safe_parse_json)
    if "current_bullets" in df.columns:
        df["current_bullets"] = df["current_bullets"].apply(normalize_bullets)
    return df


def save_csv(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)


def normalize_bullets(cell: Any) -> List[str]:
    if cell is None:
        return []
    if isinstance(cell, list):
        return [str(v).strip() for v in cell if str(v).strip()]
    if isinstance(cell, str):
        text = cell.strip()
        if not text:
            return []
        parts = [p.strip() for p in re_split_multidelim(text, ["\n", ";", "|"]) if p.strip()]
        return parts
    return []


def re_split_multidelim(text: str, delimiters: List[str]) -> List[str]:
    pattern = "|".join(map(lambda d: re_escape_regex(d), delimiters))
    import re as _re
    return _re.split(pattern, text)


def re_escape_regex(s: str) -> str:
    import re as _re
    return _re.escape(s)
