from pydantic import BaseModel, ValidationError
from typing import List


class ValidationIssue(BaseModel):
    row_index: int
    field: str
    message: str


def validate_required_fields(rows: List[dict], required_fields: List[str]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    for idx, row in enumerate(rows):
        for field in required_fields:
            if not row.get(field):
                issues.append(ValidationIssue(row_index=idx, field=field, message="Missing or empty"))
    return issues
