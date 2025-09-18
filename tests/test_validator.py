from app.services.validator import validate_required_fields


def test_validate_required_fields_flags_missing():
    rows = [
        {"product_id": "1", "title": "A", "description": ""},
        {"product_id": "", "title": "", "description": "desc"},
    ]
    issues = validate_required_fields(rows, ["product_id", "title", "description"])
    assert len(issues) == 3
    fields = sorted([i.field for i in issues])
    assert fields == ["description", "product_id", "title"]
