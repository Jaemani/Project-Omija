# Presentation Flow

Goal: make the demo feel like one operating system, not disconnected HTML pages.

## One-Line Thesis

The entities are synthetic because credential exposure data is sensitive. The system is real because the ontology, scoring engine, Foundry readbacks, action chain, and page outputs are executable and inspectable.

## Recommended Order

### 1. Why Ontology Exists

Start with the reasoning gap:

```text
flat leak list -> cannot answer blast radius
```

Explain three structural requirements:

- `of` vs `targets`: whose account vs which asset.
- `subcontractsTo*`: variable-depth supplier path.
- `traverses_*` and `cites`: auditability and provenance.

Do not start with data feeds. Start with why a feed row is not a decision.

### 2. Foundry Ontology Proof

Show Foundry Ontology Manager screenshots:

- Object Types: `Supplier`, `Domain`, `Identity`, `CredentialExposure`, `InfectedDevice`, `RiskAssessment`, `CompromiseIncident`, `ProgramExposure`, `NotificationDraft`.
- Link Types: `of`, `targets`, `belongs_to`, `owns`, `subcontractsTo`, `supplies`, `runs`, `traverses_*`, `cites`.
- Action Types and state transitions if visible.

Narration:

> This is not a custom chart model. These are Foundry ontology objects and links. The pages later are just different views over the same graph.

### 3. Input Provider Role Map

Open:

```text
out/stealthmole_role_map.html
```

Use this bridge screen between ontology proof and operating console. It answers:

- how CL becomes `CredentialExposure`;
- how CDS becomes `InfectedDevice`;
- how DT/TT become `ThreatSource`;
- why the adapter boundary exists before Foundry objects;
- why Omija is a reasoning engine, not a feed viewer.

Key sentence:

> StealthMole provides signals. Omija turns those signals into ontology-backed decisions: supplier risk, incident paths, program exposure, and reviewed notification drafts.

### 4. What Is Managed And Watched

Open:

```text
out/data_coverage_map.html
```

Use this as the first system map. It answers:

- what is synthetic seed;
- what is public context;
- what is engine-computed;
- what is live Foundry/readback evidence;
- what remains locked because it would be sensitive.

Key sentence:

> This map shows what Omija knows, what it computes, and what it intentionally does not read until policy approval exists.

### 5. Steady-State Console

Open:

```text
out/omija_console_home.html
```

Use it as the analyst's normal screen:

- coverage;
- quiet proof;
- feed status;
- action audit stream;
- sensitive review slot locked.

This removes the "static post-incident report" feeling.

### 6. Incident / Case Study Page

Open:

```text
out/omija_demo.html
```

This is the "when something happens" page. Explain provenance chips:

- `LIVE`: Foundry/readback evidence.
- `ENGINE`: computed by code.
- `SEED`: synthetic organization, credential, and device entities.
- `FRAME`: labeled presentation framing only.
- `PUBLIC_CONTEXT`: public non-sensitive context, if shown.

Key sentence:

> The data entities are synthetic, but the causal chain is real: signal slot, identity, target, supplier path, program impact, decision object, review draft.

### 7. Program Reverse View

Open only if a judge asks, "Can a program owner see exposure from their side?"

```text
out/program_threat_view.html
```

Plain explanation:

> The incident page starts from a supplier and walks forward to programs. This page starts from a program and walks backward to suppliers and incidents contributing risk.

If time is short, skip this page. It is depth proof, not the main story.

## Data Question Answer

If asked "why not use real leaked data?":

> Real leaked credentials are victim data. Putting them in a hosted demo or recording would create a new exposure surface. So we use synthetic entities to prove the engine, and public context data to prove the threat landscape. The private feed slot is a locked contract boundary, not a missing feature.

If asked "what public data is real?":

> CISA KEV, NVD, MITRE ATT&CK, URLhaus aggregate counts, and HIBP breach metadata can be used as public context. They explain why VPN/SSO/mail/dev assets matter; they do not replace credential exposure evidence.

## File Order For Demo

1. Foundry screenshots, manual.
2. `out/stealthmole_role_map.html`
3. `out/data_coverage_map.html`
4. `out/omija_console_home.html`
5. `out/omija_demo.html`
6. `out/program_threat_view.html` only if needed.
