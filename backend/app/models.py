"""Storage rows — decoupled per source (a new source = a new row type, never a
reshaping of the existing ones). Each carries the provenance mixin + a JSON payload
(the source's validated pydantic model). Cross-source concerns (health, change-log)
are their own tables.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.provenance import ProvenanceMixin


class FlightStatusRow(Base, ProvenanceMixin):
    __tablename__ = "flight_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    flight_number: Mapped[str] = mapped_column(index=True)  # "QR557"
    flight_date: Mapped[str] = mapped_column(index=True)    # local departure date "2026-07-12"
    payload: Mapped[dict] = mapped_column(JSON)

    __table_args__ = (UniqueConstraint("flight_number", "flight_date", name="uq_flight_date"),)


class AdvisoryRow(Base, ProvenanceMixin):
    __tablename__ = "advisory"

    id: Mapped[int] = mapped_column(primary_key=True)
    country_code: Mapped[str] = mapped_column(unique=True, index=True)  # ISO, e.g. "QA"
    payload: Mapped[dict] = mapped_column(JSON)


class CzibRow(Base, ProvenanceMixin):
    __tablename__ = "czib"

    id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(unique=True, index=True)  # "CZIB-2026-04"
    payload: Mapped[dict] = mapped_column(JSON)


class SourceHealthRow(Base):
    """Internal operational state per source — powers /health + failure alerts.
    Never exposed in the public API."""

    __tablename__ = "source_health"

    source: Mapped[str] = mapped_column(primary_key=True)
    last_attempt_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    last_success_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(nullable=True)


class ChangeLogRow(Base):
    """Generic append-only audit trail — written regardless of source shape."""

    __tablename__ = "change_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(index=True)
    entity_key: Mapped[str] = mapped_column(index=True)
    field: Mapped[str] = mapped_column()
    old_value: Mapped[str | None] = mapped_column(nullable=True)
    new_value: Mapped[str | None] = mapped_column(nullable=True)
    changed_at: Mapped[dt.datetime] = mapped_column()
