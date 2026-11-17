import uuid
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.entities import Account, BuyingSignal
from app.services.scoring import score_signals

TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def main():
    with SessionLocal() as db:
        db.info["tenant_id"] = TENANT_ID
        account = db.scalar(select(Account).where(
            Account.tenant_id == TENANT_ID, Account.domain == "northstar.example"))
        if not account:
            account = Account(
                tenant_id=TENANT_ID, name="Northstar Cloud (Demo)",
                domain="northstar.example", industry="B2B SaaS",
                employee_count=180, country="DE",
                description="Synthetic demo company; not a real prospect."
            )
            db.add(account)
            db.flush()
            db.add_all([
                BuyingSignal(tenant_id=TENANT_ID, account_id=account.id,
                    signal_type="security_hiring",
                    description="Synthetic demo: company posted a Security Engineer role.",
                    source_name="demo-fixture", confidence=90),
                BuyingSignal(tenant_id=TENANT_ID, account_id=account.id,
                    signal_type="enterprise_expansion",
                    description="Synthetic demo: company announced enterprise expansion.",
                    source_name="demo-fixture", confidence=80),
                BuyingSignal(tenant_id=TENANT_ID, account_id=account.id,
                    signal_type="compliance_requirement",
                    description="Synthetic demo: public procurement brief references SOC 2.",
                    source_name="demo-fixture", confidence=95),
            ])
            db.flush()
        account.score, account.score_reasons = score_signals(account.signals)
        db.commit()
        print(f"Demo tenant ID: {TENANT_ID}")
        print(f"Demo account ID: {account.id}")
        print(f"Score: {account.score}")


if __name__ == "__main__":
    main()
