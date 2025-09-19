"""
Pydantic Data Models for Walmart Content Refiner

This module defines the data structures used throughout the application
for type safety, validation, and API serialization.

Author: Walmart Content Refiner Team
Version: 1.0.0
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
import json


class ProductInput(BaseModel):
    brand: str
    product_type: str = Field(..., description="Product type or category name")
    attributes: Union[Dict[str, Any], str] = Field(default_factory=dict)
    current_description: str
    current_bullets: Union[List[str], str] = Field(default_factory=list)

    @validator("attributes", pre=True)
    def parse_attributes(cls, value: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return {}
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
                return {"value": parsed}
            except Exception:
                # Not valid JSON; return as a single attribute bucket
                return {"raw": text}
        return {}

    @validator("current_bullets", pre=True)
    def normalize_bullets_input(cls, value: Union[str, List[str]]) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            # Split on newlines or semicolons or pipes
            parts = [p.strip() for p in re_split_multidelim(text, ["\n", ";", "|"]) if p.strip()]
            return parts
        return []


class ProductOutput(BaseModel):
    title: str
    bullets: str  # HTML string format: <li>...</li><li>...</li>
    description: str
    meta_title: str
    meta_description: str
    violations: List[str] = Field(default_factory=list)


def re_split_multidelim(text: str, delimiters: List[str]) -> List[str]:
    pattern = "|".join(map(lambda d: re_escape_regex(d), delimiters))
    import re as _re
    return _re.split(pattern, text)


def re_escape_regex(s: str) -> str:
    import re as _re
    return _re.escape(s)
