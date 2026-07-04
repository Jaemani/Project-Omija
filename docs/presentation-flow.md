# Presentation Flow

Goal: make the demo feel like one operating system, not three disconnected
pages.

## One-Line Thesis

The entities are synthetic because credential exposure data is sensitive; the
system is real because the ontology, scoring engine, Foundry readbacks, action
chain, and page outputs are executable and inspectable.

## Recommended Order

### 1. Why Ontology Exists

Show the problem first:

```text
flat leak list -> cannot answer blast radius
```

Explain the three structural requirements:

- `of` vs `targets`: whose account vs what asset.
- `subcontractsTo*`: variable-depth supplier path.
- `traverses_*` and `cites`: auditability and review provenance.

Do not start with data feeds. Start with the reasoning gap.

### 2. Foundry Ontology Proof

Show Foundry Ontology Manager screenshots:

- Object Types: Supplier, Domain, Identity, CredentialExposure, InfectedDevice,
  RiskAssessment, CompromiseIncident, ProgramExposure, NotificationDraft.
- Link Types: `of`, `targets`, `belongs_to`, `owns`, `subcontractsTo`,
  `supplies`, `runs`, `traverses_*`, `cites`.
- Action Types/state transitions if visible.

Narration:

> This is not a custom chart model. These are Foundry ontology objects and links.
> The UI pages later are only different views over this graph.

### 3. What Is Managed And Watched

Open:

```text
out/data_coverage_map.html
```

Use this as the first "system screen." It answers:

- what is synthetic seed;
- what is public context;
- what is engine-computed;
- what is live Foundry/readback;
- what remains locked because it would be sensitive.

Key sentence:

> This is the steady map of what Omija knows, what it computes, and what it
> intentionally does not read until policy approval exists.

### 4. Steady-State Console

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

### 5. Incident / Case Study Page

Open:

```text
out/omija_demo.html
```

This is the "when something happens" page.

Explain provenance chips:

- `LIVE`: Foundry/readback evidence.
- `ENGINE`: computed by the code now.
- `SEED`: fictional org/credential/device entities.
- `FRAME`: labeled presentation framing only.
- `PUBLIC_CONTEXT`: public non-sensitive context, if shown.

Key sentence:

> The data entities are synthetic, but the causal chain is real: signal slot,
> identity, target, supplier path, program impact, decision object, review draft.

### 6. Program Reverse View

Open only if the judge asks, "Can a program owner see exposure from their side?"

```text
out/program_threat_view.html
```

Plain explanation:

> The incident page starts from a supplier and walks forward to programs. This
> page starts from a program and walks backward to the suppliers and incidents
> contributing risk. It proves the same ontology can serve both CERT analysts
> and program owners.

If time is short, skip this page. It is a depth proof, not the main story.

## Data Question Answer

If asked "why not use real leaked data?":

> Real leaked credentials are victim data. Putting them in a hosted demo or
> recording would create a new exposure surface. So we use synthetic entities to
> prove the engine, and public context data to prove the threat landscape. The
> private feed slot is a locked contract boundary, not a missing feature.

If asked "what public data is real?":

> CISA KEV, NVD, MITRE ATT&CK, URLhaus aggregate counts, and HIBP breach
> metadata can be used as public context. They explain why VPN/SSO/mail/dev
> assets matter; they do not replace credential exposure evidence.

## File Order For Demo

1. Foundry screenshots, manual.
2. `out/data_coverage_map.html`
3. `out/omija_console_home.html`
4. `out/omija_demo.html`
5. `out/program_threat_view.html` only if needed.

