# Claude Prompt: Palantir MCP Data Lineage Upgrade

Use this prompt for Claude/Opus when Palantir MCP access is available.

```text
You are working on Project Omija in /Users/jaeman/Codes/D4D/Project-Omija.

Goal:
Prepare a finals-ready Palantir/Foundry data lineage proof. First-round judges liked the concept but wanted explicit data lineage and a real approved StealthMole API data flow. The StealthMole hackathon API is already filtered and may be used in the demo.

Do not expose API keys, JWTs, raw provider envelopes, or reusable secret material. Show provider-to-ontology-to-decision lineage with safe/sanitized row-level fields.

Current constraints:
- Static pages are in out/.
- Existing pages: omija_console_home.html, data_evidence_brief.html, data_coverage_map.html, omija_demo.html, data_lineage_live.html.
- Approved hackathon provider records may be represented in the static demo as sanitized lineage rows.
- Codex owns the StealthMole private connector and normalization boundary.
- You own page/design/Foundry MCP verification and should not fetch or display API secrets/provider envelopes.
- Foundry schema/readback may have backing dataset schema issues. Do not overclaim full Foundry E2E if still blocked.

Required output:
1. Inspect docs/finals-data-lineage-upgrade.md first.
2. Update out/data_lineage_live.html if needed:
   - StealthMole API run summary and sanitized row-level lineage.
   - Raw envelope private/ignored step.
   - Normalization boundary.
   - Normalized objects: CredentialExposure, InfectedDevice, ThreatSource, Identity, Domain.
   - Links: of, targets, sourced_from, leaked, compromises, subcontracts_to, supplies, runs, evidenced_by, cites.
   - Engine decisions: RiskAssessment, CompromiseIncident, ProgramExposure, NotificationDraft.
   - Withheld fields proof: API key/JWT/raw payload/reusable secret material not exported.
3. Ensure nav contains "데이터 계보" or "Lineage".
4. If Palantir MCP can inspect Foundry:
   - Verify object types, link types, action types relevant to Omija.
   - Record what lineage can be proven in Foundry: backing datasets, object type datasource, link type datasource, action run/readback.
   - Do not read or display API secrets/provider envelopes.
5. Update docs/review/finals-foundry-lineage-check.md if new Foundry facts are found.

Design requirements:
- This is an operational lineage page, not a marketing page.
- Make the flow visually obvious: Provider -> Private Raw -> Normalization -> Ontology -> Engine -> Foundry/Human Action.
- Use labels: LIVE_PROVIDER, PRIVATE_RAW, NORMALIZED, ONTOLOGY, ENGINE, LIVE_FOUNDRY, LOCKED_SECRET.
- Include clear "not confirmed breach" and "API secrets/raw provider envelopes not exported" wording.
- Keep mobile responsive.

Safe wording:
"Approved StealthMole hackathon records are ingested live, normalized into Omija ontology objects, and traced through every decision object by lineage. API secrets and raw provider envelopes are not exported."

Forbidden claims:
- We store API credentials or raw provider envelopes.
- targets means successful login.
- Band A means confirmed compromise.
- Foundry full E2E readback is solved unless verified.

After changes:
- Run make build if needed.
- Verify pages render locally.
- Do not commit unless asked.
```
