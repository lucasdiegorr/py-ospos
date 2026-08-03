"""Validate that the shared domain schema builds and persists in Postgres."""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (registers all models on Base.metadata)
from app.db import Base
from app.domain.money import to_cents


@pytest.mark.skipif(not os.getenv("OSPOS_DATABASE_URL"), reason="requires a database")
def test_create_all_and_basic_persist() -> None:
    engine = create_engine(os.environ["OSPOS_DATABASE_URL"], pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        from app.models.payment import PaymentMethod

        session.add(PaymentMethod(id="cash", name="Cash", is_enabled=True))
        session.commit()

        rows = session.execute(text("SELECT id FROM payment_methods WHERE id = 'cash'")).all()
        assert rows and rows[0][0] == "cash"

    engine.dispose()


def test_money_conversion() -> None:
    assert to_cents("12.50") == 1250
