"""SQLite implementation of `OntologyStore` (architecture.md §7 fallback).

Validation / insurance store only — AIP (Foundry + OSDK) is the spine (ADR-0003).
Tables mirror the ontology objects and their links (foreign keys), so the same
graph reads that OSDK will serve are exercised locally today.
"""

from __future__ import annotations

import sqlite3

from adapter.base import Exposure

_SCHEMA = """
CREATE TABLE IF NOT EXISTS supplier (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    tier        INTEGER,
    criticality TEXT
);
CREATE TABLE IF NOT EXISTS domain (
    fqdn        TEXT PRIMARY KEY,
    supplier_id TEXT REFERENCES supplier(id)        -- Supplier owns Domain
);
CREATE TABLE IF NOT EXISTS identity (
    id          TEXT PRIMARY KEY,                    -- resolved (entity resolution)
    email       TEXT,
    username    TEXT,
    domain_ref  TEXT                                 -- Identity belongs_to Domain
);
CREATE TABLE IF NOT EXISTS threat_source (
    id          TEXT PRIMARY KEY,
    kind        TEXT,
    name        TEXT
);
CREATE TABLE IF NOT EXISTS credential_exposure (
    id             TEXT PRIMARY KEY,
    module         TEXT,
    secret_type    TEXT,
    masked_value   TEXT,                             -- masked only; never raw
    secret_present INTEGER,
    host           TEXT,
    observed_at    INTEGER,
    fetched_at     INTEGER,
    source         TEXT,
    source_ref     TEXT,                             -- provenance handle
    confidence     REAL,
    is_mock        INTEGER,
    identity_ref   TEXT REFERENCES identity(id),     -- Exposure of Identity
    threat_ref     TEXT REFERENCES threat_source(id) -- Exposure sourced_from ThreatSource
);
CREATE TABLE IF NOT EXISTS infected_device (
    id                 TEXT PRIMARY KEY,
    exposure_ref       TEXT REFERENCES credential_exposure(id),  -- Device leaked Exposure
    identity_ref       TEXT REFERENCES identity(id),             -- Device compromises Identity
    malware            TEXT,
    infected_at        INTEGER,
    has_session_cookie INTEGER,
    account_type       TEXT,
    os                 TEXT
);
"""


def _identity_id(exp: Exposure) -> str:
    key = exp.identity.email or exp.identity.username or f"anon:{exp.source_ref}"
    return f"id:{key}"


class SqliteOntologyStore:
    """`OntologyStore` backed by SQLite. Use `:memory:` for ephemeral runs."""

    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.init_schema()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SqliteOntologyStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- schema / writes ---------------------------------------------------

    def init_schema(self) -> None:
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def upsert_supplier(
        self, *, id: str, name: str, tier: int, criticality: str
    ) -> None:
        self.conn.execute(
            "INSERT INTO supplier(id,name,tier,criticality) VALUES(?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET name=excluded.name, tier=excluded.tier, "
            "criticality=excluded.criticality",
            (id, name, tier, criticality),
        )
        self.conn.commit()

    def upsert_domain(self, *, fqdn: str, supplier_id: str) -> None:
        self.conn.execute(
            "INSERT INTO domain(fqdn,supplier_id) VALUES(?,?) "
            "ON CONFLICT(fqdn) DO UPDATE SET supplier_id=excluded.supplier_id",
            (fqdn, supplier_id),
        )
        self.conn.commit()

    def write_exposure(self, exp: Exposure, *, domain: str | None = None) -> str:
        c = self.conn
        ident_id = _identity_id(exp)

        # Identity — entity resolution: same email/username → one row.
        c.execute(
            "INSERT INTO identity(id,email,username,domain_ref) VALUES(?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "email=COALESCE(excluded.email, identity.email), "
            "username=COALESCE(excluded.username, identity.username), "
            "domain_ref=COALESCE(excluded.domain_ref, identity.domain_ref)",
            (ident_id, exp.identity.email, exp.identity.username, domain),
        )

        # ThreatSource (provenance).
        threat_id = f"ts:{exp.module}"
        c.execute(
            "INSERT INTO threat_source(id,kind,name) VALUES(?,?,?) "
            "ON CONFLICT(id) DO NOTHING",
            (threat_id, exp.threat_kind, f"stealthmole:{exp.module}"),
        )

        # CredentialExposure (masked only).
        c.execute(
            "INSERT INTO credential_exposure("
            "id,module,secret_type,masked_value,secret_present,host,observed_at,"
            "fetched_at,source,source_ref,confidence,is_mock,identity_ref,threat_ref"
            ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO NOTHING",
            (
                exp.id, exp.module, exp.secret.type, exp.secret.masked_value,
                int(exp.secret.present), exp.host, exp.observed_at, exp.fetched_at,
                exp.source, exp.source_ref, exp.confidence, int(exp.is_mock),
                ident_id, threat_id,
            ),
        )

        # InfectedDevice — only when stealer signal present (cds active fields).
        d = exp.device
        if any(v is not None for v in (d.infected_at, d.malware, d.has_session_cookie)):
            c.execute(
                "INSERT INTO infected_device("
                "id,exposure_ref,identity_ref,malware,infected_at,"
                "has_session_cookie,account_type,os"
                ") VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
                (
                    f"dev:{exp.source_ref}", exp.id, ident_id, d.malware,
                    d.infected_at,
                    None if d.has_session_cookie is None else int(d.has_session_cookie),
                    d.account_type, d.os,
                ),
            )

        c.commit()
        return exp.id

    # -- read-back ---------------------------------------------------------

    def suppliers(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id,name,tier,criticality FROM supplier ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]

    _EXP_SELECT = """
        SELECT e.id, e.module, e.secret_type, e.masked_value, e.secret_present,
               e.host, e.observed_at, e.source, e.source_ref, e.confidence,
               e.is_mock, i.email, i.username, i.domain_ref, d.supplier_id,
               dev.malware, dev.infected_at, dev.has_session_cookie,
               dev.account_type
        FROM credential_exposure e
        JOIN identity i           ON e.identity_ref = i.id
        LEFT JOIN domain d        ON i.domain_ref = d.fqdn
        LEFT JOIN infected_device dev ON dev.exposure_ref = e.id
    """

    def exposures_for_supplier(self, supplier_id: str) -> list[dict]:
        rows = self.conn.execute(
            self._EXP_SELECT + " WHERE d.supplier_id = ? ORDER BY e.id",
            (supplier_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def all_exposures(self) -> list[dict]:
        rows = self.conn.execute(self._EXP_SELECT + " ORDER BY e.id").fetchall()
        return [dict(r) for r in rows]

    def infected_devices(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM infected_device ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]


# SqliteOntologyStore structurally implements OntologyStore.
from .base import OntologyStore as _OntologyStore  # noqa: E402

_PROTOCOL_CHECK: type[_OntologyStore] = SqliteOntologyStore
