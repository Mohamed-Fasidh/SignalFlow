import pytest
from app.services.normalization import normalize_domain


def test_normalizes_url_and_www():
    assert normalize_domain("https://www.Example.com/path") == "example.com"


@pytest.mark.parametrize("value", ["", "not-a-domain", "https://", "bad domain.com"])
def test_rejects_invalid_domain(value):
    with pytest.raises(ValueError):
        normalize_domain(value)


@pytest.mark.parametrize("value", [
    "https://user:secret@example.com",
    "https://127.0.0.1",
    "example..com",
    "-bad.example",
    "bad-.example",
    "example.com:99999",
])
def test_rejects_unsafe_or_malformed_domains(value):
    with pytest.raises(ValueError):
        normalize_domain(value)
