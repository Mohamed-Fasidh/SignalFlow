from datetime import datetime, timezone
from app.models.entities import BuyingSignal

WEIGHTS = {
    "compliance_requirement": 25,
    "security_hiring": 20,
    "enterprise_expansion": 20,
    "funding": 15,
    "icp_fit": 10,
    "other": 0,
}


def score_signals(signals: list[BuyingSignal]) -> tuple[int, list[dict]]:
    now = datetime.now(timezone.utc)
    total = 0
    reasons: list[dict] = []
    for signal in signals:
        if getattr(signal, "archived_at", None) is not None:
            continue
        occurred = signal.occurred_at
        if occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=timezone.utc)
        age_days = max(0, (now - occurred).days)
        base = WEIGHTS.get(signal.signal_type, 0)
        freshness = 1.0 if age_days <= 30 else 0.6 if age_days <= 90 else 0.25
        confidence = signal.confidence / 100
        points = round(base * freshness * confidence)
        if points:
            total += points
            reasons.append({
                "signal_id": str(signal.id),
                "type": signal.signal_type,
                "points": points,
                "evidence": signal.description,
                "source": signal.source_name,
                "age_days": age_days,
            })
    return min(total, 100), reasons
