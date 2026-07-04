# Demo Script

D4D Hackathon Track 2/3: OSINT and defense-intelligence data fusion for
defense supply-chain credential exposure early warning.

Data boundary:

- public OSINT feeds are real public data;
- Foundry credential seed is synthetic;
- StealthMole live credential ingestion is only claimed after authorized
  registry and successful auth;
- notification output is a draft, not a sent message.

## Preparation

```bash
uv sync
uv run pytest -q
uv run python scripts/intelligence_demo.py
open out/intelligence_demo.html
```

Fallback:

```bash
uv run python scripts/final_demo_check.py --full
open out/foundry_demo.html
```

## Three-Minute Flow

### Problem

Defense supply chains span prime contractors and many first- and second-tier
suppliers. Attackers often start at the edge: leaked supplier credentials,
infostealer-infected devices, and exposed access surfaces. A flat list of leaks
does not answer the operational question: which supplier creates a live path to
a protected program?

### Solution

Project Omija connects credential exposure, identity, domain ownership,
supplier relationships, prime contractors, and programs in a Foundry ontology.
The model separates `of` from `targets`:

- `of`: whose account was exposed;
- `targets`: what asset that account appears able to access.

That distinction lets the graph show a supplier account targeting a prime VPN,
SSO, mail, or admin asset.

### Live Demo

1. Open `out/intelligence_demo.html`.
2. Show public OSINT counts from NVD, CISA KEV, MITRE ATT&CK, and URLhaus.
3. Show the active path and impacted programs.
4. Run:

```bash
uv run python scripts/foundry_blast_radius.py exp:micro-h:active
```

5. Explain that the notification is an approval-gated draft.

### Close

The system does not rank by volume alone. It prioritizes active paths where an
exposed supplier identity can reach a sensitive target asset and a prime
program. Public OSINT explains why the target asset class matters, while the
ontology explains blast radius and response ownership.

## Do Not Claim

- Do not claim synthetic seed credentials are real leaked data.
- Do not claim StealthMole live ingestion succeeded while `/user/quotas` returns
  `401`.
- Do not claim a notification was sent.
