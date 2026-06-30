<div align="center">
<img src="assets/sulcus_logo_sm.png" width="140" alt="Sulcus"/>

# Sulcus.pro
### Autonomous Corporate Intelligence — NovaCorp

*A live, multi-department operational intelligence prototype: real Supabase-backed event data, a dual-gate guardrail engine, a circadian memory-consolidation loop, and a Claude-powered chat layer.*

</div>

---

## What this is (v2)

Sulcus.pro v2 simulates **NovaCorp**, a B2B SaaS company, across 8 departments (Engineering, Product, Sales, Marketing, Finance, HR, Legal, DevOps). A standalone generator seeds a 10-tick operational story arc into Supabase — normal operations, emerging problems, a cross-department crisis, then resolution — and the Streamlit app reads that live data to drive department dashboards, an evolving calendar, an audit trail, and a Claude-powered chat agent.

v2 keeps the original evaluation engine intact and replaces everything around it:

| Kept (untouched evaluation logic) | Replaced (data layer, ingestion, UI) |
|---|---|
| `sulcus/schemas.py` — Pydantic v2 data contracts | `supabase_setup.sql` / `supabase_client.py` — the data layer |
| `sulcus/guardrails.py` — Gate 1 schema shield + Gate 2 grounding loop | `generator.py` — standalone NovaCorp event generator (batch + `--schedule` live mode) |
| `sulcus/circadian.py` — nightly consolidation loop (now tag-driven, not hardcoded IDs) | `sulcus/ingestion.py` — `SupabaseConnector` replacing the old mock connectors |
| `sulcus/state_engine.py` — tick state machine | `sulcus/storyline.py` — builds the canvas from real events instead of a fixed script |
| | `app.py` — full 3-column rebuild: live event feed, department tabs, evolving calendar, chat |

### The four pillars

| Pillar | Module | What it does |
|---|---|---|
| **The Ears** — Ingestion | `sulcus/ingestion.py` | Polls the Supabase `events` table per tick and converts rows into canonical `IngestionEvent`s. |
| **The Storyline** — State Engine | `sulcus/state_engine.py` | Tick state machine. Each `advance()` ingests new events, runs guardrails, writes the audit trail. |
| **The Shields** — Dual Guardrails | `sulcus/guardrails.py` | **Gate 1**: live Pydantic v2 schema validation (+ a deliberately malformed payload quarantined to prove the shield is live). **Gate 2**: token-grounded faithfulness + context-precision scoring against the real event corpus. |
| **The Brain** — Circadian Loop | `sulcus/circadian.py` | Fires at Tick 8 (the resolution/pivot phase): sweeps events tagged `contradiction`, tombstones events tagged `obsolete_on_pivot`, rewrites the knowledge graph. |

---

## Run it locally

### 1. Set up Supabase

1. Create a Supabase project.
2. Open the SQL Editor and run `supabase_setup.sql` — it creates `events`, `audit_log`, `chat_history`, their indexes, and open RLS policies suitable for a demo.
3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in:

```toml
SUPABASE_URL = "your-project-url"
SUPABASE_KEY = "your-anon-or-publishable-key"
ANTHROPIC_API_KEY = "your-key"   # optional — can also be entered in the app UI
```

`.streamlit/secrets.toml` is gitignored — never commit it.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Seed NovaCorp's event data

```bash
python generator.py
```

This inserts 60+ events spanning all 8 departments and ticks 0-9 (normal operations -> problems emerging -> crisis -> resolution).

Optionally, run it in live mode in a separate terminal to keep inserting 2-3 new events every 5 minutes (uses APScheduler, runs independently of the Streamlit app):

```bash
python generator.py --schedule
```

### 4. Run the app

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Using the app

- **Sidebar** — filter by department, source, and risk level; use the tick slider or the **Advance** button to move through the story; **Reset** returns to Tick 0. Per-department live event counts update as you move through ticks.
- **Left panel** — the live event feed: source/department/risk badges, actor, full event text, and a "View Risk" expander with the risk rationale. A red banner appears when a critical event is active.
- **Center panel** — one tab per department (KPIs + filtered event cards + a Healthy/At Risk/Critical status), plus an **Audit Trail** tab showing the Temporal Brain history grouped by tick.
- **Right panel** — enter a demo Anthropic API key (stored only in `st.session_state`, never logged), browse the evolving July 2026 calendar (color-coded by risk, click a date to see that day's events), and chat with Sulcus, which is grounded in the last 20 real NovaCorp events.
- **Bottom** — the Transparency Center: Schema Errors, Faithfulness Score, Hallucination Suppression, and total Events Processed, plus the live Gate 1 / Gate 2 / Circadian terminal log.

---

## Project layout

```
sulcus/                       (repo root)
├── app.py                    # Streamlit UI — 3-column layout, filters, chat, calendar
├── generator.py               # Standalone NovaCorp event generator (batch + --schedule)
├── supabase_setup.sql         # events / audit_log / chat_history schema + indexes + RLS
├── supabase_client.py         # shared Supabase client (st.secrets or env vars)
├── requirements.txt
├── README.md
├── .streamlit/
│   ├── config.toml            # dark theme, violet primary
│   └── secrets.toml.example   # copy to secrets.toml and fill in
├── assets/
│   ├── sulcus_logo.png
│   └── sulcus_logo_sm.png
└── sulcus/                    # the engine package (evaluation logic kept intact)
    ├── schemas.py              # Pydantic v2 models
    ├── ingestion.py            # SupabaseConnector + append-only stream
    ├── storyline.py            # builds the per-tick canvas from real events
    ├── guardrails.py           # Gate 1 schema shield + Gate 2 eval loop
    ├── circadian.py            # tag-driven nightly consolidation
    ├── state_engine.py         # tick state machine
    └── generative_ui.py        # brand header, terminal console, audit timeline
```

---

## Notes

- No emojis anywhere in the UI, code, or copy — only plain text and color-coded badges.
- All Supabase queries handle empty results and connection failures gracefully (the app runs, with empty panels, even with no Supabase credentials configured).
- The chat panel never crashes if no Anthropic API key is available — it shows a plain message asking for one instead.
- `generator.py` has no Streamlit import and runs fully standalone (cron job, background worker, or a second terminal next to `streamlit run app.py`).
