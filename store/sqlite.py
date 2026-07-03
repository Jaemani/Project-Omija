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
    criticality TEXT                                 -- numeric 1..3 (registry) or label
);
CREATE TABLE IF NOT EXISTS prime (
    id          TEXT PRIMARY KEY,
    name        TEXT
);
CREATE TABLE IF NOT EXISTS program (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    sensitivity TEXT
);
CREATE TABLE IF NOT EXISTS supplies (               -- Supplier supplies Prime (N:M)
    supplier_id TEXT REFERENCES supplier(id),
    prime_id    TEXT REFERENCES prime(id),
    PRIMARY KEY (supplier_id, prime_id)
);
CREATE TABLE IF NOT EXISTS runs (                   -- Prime runs Program (N:M)
    prime_id    TEXT REFERENCES prime(id),
    program_id  TEXT REFERENCES program(id),
    PRIMARY KEY (prime_id, program_id)
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
-- CorrelateExposure provenance: why an Exposure is attributed to a Supplier
-- (email-domain match basis). No score/decision without a basis row (§5).
CREATE TABLE IF NOT EXISTS exposure_match (
    exposure_ref TEXT PRIMARY KEY REFERENCES credential_exposure(id),
    identity_ref TEXT REFERENCES identity(id),
    domain_ref   TEXT REFERENCES domain(fqdn),
    supplier_id  TEXT REFERENCES supplier(id),
    match_basis  TEXT,                             -- human-readable provenance
    matched_at   INTEGER
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

    def upsert_prime(self, *, id: str, name: str) -> None:
        self.conn.execute(
            "INSERT INTO prime(id,name) VALUES(?,?) "
            "ON CONFLICT(id) DO UPDATE SET name=excluded.name",
            (id, name),
        )
        self.conn.commit()

    def upsert_program(self, *, id: str, name: str, sensitivity: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO program(id,name,sensitivity) VALUES(?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET name=excluded.name, "
            "sensitivity=excluded.sensitivity",
            (id, name, sensitivity),
        )
        self.conn.commit()

    def link_supplies(self, *, supplier_id: str, prime_id: str) -> None:
        """Supplier supplies Prime (N:M)."""
        self.conn.execute(
            "INSERT INTO supplies(supplier_id,prime_id) VALUES(?,?) "
            "ON CONFLICT(supplier_id,prime_id) DO NOTHING",
            (supplier_id, prime_id),
        )
        self.conn.commit()

    def link_runs(self, *, prime_id: str, program_id: str) -> None:
        """Prime runs Program (N:M)."""
        self.conn.execute(
            "INSERT INTO runs(prime_id,program_id) VALUES(?,?) "
            "ON CONFLICT(prime_id,program_id) DO NOTHING",
            (prime_id, program_id),
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

    # -- CorrelateExposure support (email-domain → Supplier) ----------------

    def registered_domains(self) -> dict[str, str]:
        """{fqdn: supplier_id} for every owned Domain (correlation key set)."""
        rows = self.conn.execute("SELECT fqdn, supplier_id FROM domain").fetchall()
        return {r["fqdn"]: r["supplier_id"] for r in rows}

    def exposures_for_correlation(self) -> list[dict]:
        """(exposure_id, source_ref, identity_id, email) for every Exposure —
        the input to `CorrelateExposure`."""
        rows = self.conn.execute(
            "SELECT e.id AS exposure_id, e.source_ref, i.id AS identity_id, i.email "
            "FROM credential_exposure e JOIN identity i ON e.identity_ref = i.id "
            "ORDER BY e.id"
        ).fetchall()
        return [dict(r) for r in rows]

    def attach_identity_domain(self, identity_id: str, domain_ref: str) -> None:
        """Confirm Identity belongs_to Domain (set by correlation, not ingest)."""
        self.conn.execute(
            "UPDATE identity SET domain_ref=? WHERE id=?", (domain_ref, identity_id)
        )
        self.conn.commit()

    def record_correlation(
        self, *, exposure_ref: str, identity_ref: str, domain_ref: str,
        supplier_id: str, match_basis: str, matched_at: int,
    ) -> None:
        """Persist CorrelateExposure provenance (match basis)."""
        self.conn.execute(
            "INSERT INTO exposure_match("
            "exposure_ref,identity_ref,domain_ref,supplier_id,match_basis,matched_at"
            ") VALUES(?,?,?,?,?,?) ON CONFLICT(exposure_ref) DO UPDATE SET "
            "identity_ref=excluded.identity_ref, domain_ref=excluded.domain_ref, "
            "supplier_id=excluded.supplier_id, match_basis=excluded.match_basis, "
            "matched_at=excluded.matched_at",
            (exposure_ref, identity_ref, domain_ref, supplier_id, match_basis, matched_at),
        )
        self.conn.commit()

    def correlations(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM exposure_match ORDER BY exposure_ref"
        ).fetchall()
        return [dict(r) for r in rows]

    def unmatched_exposures(self) -> list[dict]:
        """Exposures whose Identity was never attributed to a Domain/Supplier."""
        rows = self.conn.execute(
            "SELECT e.id, e.module, e.source_ref, i.email "
            "FROM credential_exposure e JOIN identity i ON e.identity_ref = i.id "
            "WHERE i.domain_ref IS NULL ORDER BY e.id"
        ).fetchall()
        return [dict(r) for r in rows]

    # -- read-back ---------------------------------------------------------

    def suppliers(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id,name,tier,criticality FROM supplier ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]

    def primes(self) -> list[dict]:
        rows = self.conn.execute("SELECT id,name FROM prime ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def programs(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id,name,sensitivity FROM program ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]

    def propagation_for_supplier(self, supplier_id: str) -> list[dict]:
        """Supplier → Prime → Program propagation rows (ontology.md §2 upward
        path). One row per (prime, program); program may be NULL if a prime runs
        no program."""
        rows = self.conn.execute(
            "SELECT s.prime_id, p.name AS prime_name, "
            "       r.program_id, pg.name AS program_name, pg.sensitivity "
            "FROM supplies s "
            "JOIN prime p        ON s.prime_id = p.id "
            "LEFT JOIN runs r    ON r.prime_id = p.id "
            "LEFT JOIN program pg ON r.program_id = pg.id "
            "WHERE s.supplier_id = ? "
            "ORDER BY s.prime_id, r.program_id",
            (supplier_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    _EXP_SELECT = """
        SELECT e.id, e.module, e.secret_type, e.masked_value, e.secret_present,
               e.host, e.observed_at, e.fetched_at, e.source, e.source_ref,
               e.confidence, e.is_mock, i.email, i.username, i.domain_ref,
               d.supplier_id, dev.malware, dev.infected_at, dev.has_session_cookie,
               dev.account_type, m.match_basis, ts.kind AS threat_kind,
               ts.name AS threat_name
        FROM credential_exposure e
        JOIN identity i           ON e.identity_ref = i.id
        LEFT JOIN domain d        ON i.domain_ref = d.fqdn
        LEFT JOIN infected_device dev ON dev.exposure_ref = e.id
        LEFT JOIN exposure_match m    ON m.exposure_ref = e.id
        LEFT JOIN threat_source ts    ON e.threat_ref = ts.id
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
