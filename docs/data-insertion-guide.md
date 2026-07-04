# Data Insertion Guide

This guide answers: "the current dataset looks too small; how do we add more
without breaking the story?"

## Current Managed Data

| Location | Meaning |
|---|---|
| `out/foundry_seed/*.csv` | Foundry-loadable seed objects and link tables |
| `registry/suppliers.yaml` | Local synthetic supplier registry used by the engine |
| `adapter/mock.py` | Synthetic exposure/device corpus for local scoring |
| `out/foundry_action_chain.json` | Foundry action/readback audit evidence |
| `out/program_threat_view.json` | Program-centric reverse view result |
| `out/public_context/summary.json` | Optional public context snapshot, not main demo |

## Minimum Demo Data Shape

Keep these three evidence patterns visible:

1. **Multi-tier active path**
   - Example shape: `Supplier(T2) -> Supplier(T1) -> Prime -> Program`
   - Purpose: proves `subcontractsTo*` is needed.

2. **Cross-organization target**
   - Example shape: `CredentialExposure.of -> supplier Identity`, but
     `CredentialExposure.targets -> prime Domain`.
   - Purpose: proves `of` and `targets` must be separate.

3. **Volume-vs-active dominance**
   - Example shape: one supplier has many stale/recycled exposures; another has
     one active device/session path.
   - Purpose: proves banded triage is not raw volume sorting.

## Synthetic Scale-Up Targets

For a stronger page, add enough synthetic records to make the console feel
operational:

| Object | Target count | Why |
|---|---:|---|
| Supplier | 12-20 | enough for tier/minimap coverage |
| Domain | 25-50 | asset surface map: vpn, sso, mail, dev, web |
| Identity | 40-100 | entity resolution and org ownership |
| CredentialExposure | 120-300 | volume distribution and dedup story |
| InfectedDevice | 10-25 | active/stale distinction |
| RiskAssessment | one per supplier | ranking surface |
| CompromiseIncident | 3-5 open, several closed | audit stream and response flow |
| ProgramExposure | one per protected program | program view |

## Property Guidance

Use neutral fictional names and `*.example` domains. Do not use real supplier
names, real emails, real passwords, or real session artifacts.

Recommended `Domain.asset_type` values:

```text
vpn
sso
mail
groupware
dev
web
admin
```

Recommended `CredentialExposure.module` values:

```text
stealer-log
url-login-pass
breach
combo
```

Recommended `ThreatSource.kind` values:

```text
placeholder
public_context
vendor_public
synthetic_seed
```

## Public Context Insertion

Do not make NVD/KEV/MITRE/URLhaus first-class ontology objects yet. Put them in
decision components:

```json
{
  "public_context": {
    "asset_type": "vpn",
    "kev_matches": 12,
    "nvd_critical_vpn_results": 20,
    "techniques": ["T1078", "T1550"],
    "source_snapshot": "out/public_context/summary.json"
  }
}
```

Where to show it:
- target `Domain` inspector;
- `RiskAssessment.components`;
- `ProgramExposure.components`.

## CSV Update Order

When manually extending Foundry seed CSVs:

1. Add objects first:
   - `01_supplier.csv`
   - `04_domain.csv`
   - `05_identity.csv`
   - `06_credential_exposure.csv`
   - `07_infected_device.csv`
   - `08_threat_source.csv`
2. Add base links:
   - `23_link_owns.csv`
   - `25_link_belongs_to.csv`
   - `26_link_of.csv`
   - `27_link_targets.csv`
   - `28_link_sourced_from.csv`
   - `29_link_leaked.csv`
3. Add derived objects/links only after the engine can justify them:
   - `10_risk_assessment.csv`
   - `11_compromise_incident.csv`
   - `12_program_exposure.csv`
   - `13_notification_draft.csv`
   - `35-45_link_*`

## Visual Insertions

Add one network-style view to explain "what is monitored":

```text
Program
  <- Prime
    <- Supplier(T1)
      <- Supplier(T2)
        <- Domain assets
          <- Identity / CredentialExposure slots
```

Color rules:
- blue: real ontology object type;
- green: engine-computed result;
- yellow: public context;
- gray: synthetic seed entity;
- red: active incident path.

## Do Not Add

- raw credential values;
- real person emails;
- real supplier domains unless cleared;
- raw malicious URL lists in hosted pages;
- any automatic notification send action.
