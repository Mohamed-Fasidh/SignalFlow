from types import SimpleNamespace
from datetime import datetime, timezone
from app.services.scoring import score_signals


def test_score_is_explainable_and_capped():
    signals = [
        SimpleNamespace(id="1", signal_type="compliance_requirement",
            description="SOC 2 required", source_name="job-posting",
            confidence=100, occurred_at=datetime.now(timezone.utc)),
        SimpleNamespace(id="2", signal_type="security_hiring",
            description="Hiring security engineer", source_name="careers",
            confidence=100, occurred_at=datetime.now(timezone.utc)),
    ]
    score, reasons = score_signals(signals)
    assert score == 45
    assert len(reasons) == 2
    assert reasons[0]["evidence"] == "SOC 2 required"


def test_old_signals_decay():
    from datetime import timedelta
    signals = [SimpleNamespace(id="1", signal_type="funding", description="Old funding",
        source_name="demo", confidence=100,
        occurred_at=datetime.now(timezone.utc) - timedelta(days=120))]
    score, _ = score_signals(signals)
    assert score == 4
