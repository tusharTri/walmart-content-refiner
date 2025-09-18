from app.services.validator import (
    count_words,
    check_banned_words,
    validate_title,
    validate_meta_title,
    validate_meta_desc,
    validate_description_length,
    validate_bullets,
    validate_no_medical_claims,
    validate_product_output,
)


def test_count_words():
    assert count_words("one two three") == 3
    assert count_words("") == 0


def test_check_banned_words():
    assert check_banned_words("Premium quality knife") == ["knife", "premium"]
    assert check_banned_words("great product") == []


def test_validate_title():
    v = validate_title("Brand X Product Title", brand="Brand X")
    assert v == []
    v2 = validate_title("a" * 151, brand="b")
    assert any("exceeds 150" in s for s in v2)
    assert any("brand missing" in s for s in v2)


def test_validate_meta_title_and_desc():
    assert validate_meta_title("Short Title") == []
    assert any("exceeds" in s for s in validate_meta_title("a" * 71))
    assert validate_meta_desc("a" * 160) == []
    assert any("exceeds" in s for s in validate_meta_desc("a" * 161))


def test_validate_description_length_and_bullets():
    desc = "word " * 130
    assert validate_description_length(desc, brand=None) == []
    bullets = ["b" * 10] * 8
    assert validate_bullets(bullets) == []
    too_long = ["x" * 90] + ["b"] * 7
    v = validate_bullets(too_long)
    assert any("exceeds 85" in s for s in v)


def test_validate_no_medical_claims():
    assert validate_no_medical_claims("This helps you sleep") == []
    assert validate_no_medical_claims("This will cure headaches") != []


def test_validate_product_output():
    output = {
        "title": "Acme Widget - Blue",
        "bullets": ["compact", "durable", "lightweight", "easy to use", "stylish", "energy efficient", "warranty included", "great value"],
        "description": "word " * 125,
        "meta_title": "Acme Widget",
        "meta_description": "Affordable widget by Acme",
    }
    violations = validate_product_output(output, input_keywords=["widget"], brand="Acme")
    assert isinstance(violations, list)
