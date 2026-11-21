# Kuku AI Generalist Lab

Three small, rerunnable prototypes built for the Kuku AI Generalist assignment, combined in one Streamlit app. Each prototype sits in its own tab, and a human reviewer stays in the loop for every result.

**Live demo:** [kuku-fm-ai-generalist.streamlit.app](https://kuku-fm-ai-generalist-g8shuwk4u5p8yh7jqkjsma.streamlit.app/)

---

## Contents

- [Overview](#overview)
- [Features](#features)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Problem details](#problem-details)
- [Testing](#testing)
- [Confidentiality and version control](#confidentiality-and-version-control)
- [Limitations](#limitations)

---

## Overview

| Tab | Problem | What it does |
|-----|---------|--------------|
| 🎬 Promo Finder | Find the promos | Ranks 20–60 second windows in timestamped screenplays as promo candidates, with an optional OpenAI review of the top 10 |
| 🏠 Rental Legal Helper | Rental deposit disputes (India) | Organises a tenant's account, lists evidence to collect, suggests next steps and drafts a refund request |
| 🧾 Continuity QA | Script continuity | Flags timestamp problems and continuity-note terms that need human review |

The baseline for every tab works without paid APIs. The only optional paid component is the OpenAI evaluation in Problem 1.

## Features

- Upload a screenplay ZIP, with protection against unsafe file paths inside the archive.
- Transparent heuristic ranking, so scores can be reproduced.
- Optional LLM evaluation with cost controls: a 10-candidate cap, bounded excerpts, structured JSON output, token limits, a preflight budget check and a local cache.
- Hybrid scoring: 40% heuristic and 60% LLM. Failed evaluations are labelled as heuristic-only fallbacks and are never given a made-up hybrid score.
- Plain-language case summaries and an editable draft letter for the rental helper.
- CSV and JSON exports for the promo and continuity results.

## Project structure

```
kuku_ai_generalist/
├── .streamlit/
│   └── config.toml           # Light theme settings
├── problem1_promos/          # Timestamp parser, heuristic ranker, OpenAI evaluator, tests
├── problem2_legal/           # Rental deposit organiser and refund-request drafter, tests
├── problem3_continuity/      # Timestamp and continuity checks, tests
├── validation/               # Validation material
├── outputs/                  # Generated results (git-ignored)
├── app.py                    # Streamlit app (all three tabs)
├── requirements.txt          # Python dependencies
├── .env.example              # Template for local API configuration
├── .env                      # Your private keys (git-ignored, not committed)
├── .gitignore
└── README.md
```

The confidential screenplay ZIP is not included. Upload it in the app.

## Getting started

Python 3.10 or later is recommended.

### Setup

Windows (Command Prompt):

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL that Streamlit prints, normally `http://localhost:8501`.

## Configuration

The OpenAI evaluation is optional and affects Problem 1 only.

1. Copy `.env.example` to a new file named `.env` in the project folder.
2. Fill in the values below.
3. Restart Streamlit.

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | none (LLM button stays disabled) |
| `OPENAI_MODEL` | Model ID enabled for your API project | set in `app.py` |
| `OPENAI_RUN_BUDGET_USD` | Maximum estimated spend per evaluation run | `0.25` |

Keep `.env` private. It is excluded by `.gitignore`. Confirm that `OPENAI_MODEL` matches the exact model ID shown in your OpenAI account.

The cost shown in the app is an estimate based on configured per-token rates and the usage returned by the API. Check current pricing independently, because actual billing can differ.

## Deployment

The app is deployed on Streamlit Community Cloud:
[kuku-fm-ai-generalist.streamlit.app](https://kuku-fm-ai-generalist-g8shuwk4u5p8yh7jqkjsma.streamlit.app/)

Notes for the hosted version:

- Add secrets (`OPENAI_API_KEY` and any other variables above) in the app's **Settings → Secrets** panel. Do not commit a `.env` file.
- The screenplay pack is not stored in the repository, so the bundled-pack buttons do not appear. Upload the ZIP in each tab instead.
- Hosted files are not private. Do not upload confidential screenplays to a public deployment unless you are permitted to.
- Files written to `outputs/` on the host are temporary and may disappear when the app restarts.

## Problem details

### Problem 1: Find the promos

Upload a ZIP of timestamped `.txt` screenplay files. The Python baseline extracts candidate 20–60 second windows and ranks them using text-based signals.

The optional OpenAI layer evaluates only the top 10 heuristic candidates on hook strength, emotional intensity, conflict and tension, cliffhanger strength, and standalone clarity. It returns schema-constrained JSON with explanations, plus a comparison CSV and JSON.

Text alone cannot judge acting, facial expressions, visuals, music, shot composition or real audience performance. An editor must preview the footage before anything is published.

### Problem 2: Rental Legal Helper

A deliberately narrow, India-focused prototype for rental security-deposit disputes. It:

- organises the tenant's account into a plain-language case summary,
- identifies evidence to collect and facts still to confirm,
- suggests practical next steps,
- drafts a polite, editable refund request.

It is a rules-based information and drafting aid. It is not a lawyer and does not give legal opinions or cite statutes or case law. Verify all dates, amounts, agreement clauses and local law, and seek qualified local advice where appropriate. Follow-up questions are limited to information that appears to be missing from the submitted account.

### Problem 3: Script Continuity QA

Processes the `.txt` files in an uploaded ZIP and checks for:

- missing scene boundaries,
- scenes that run backwards in time,
- possible overlaps,
- timestamps outside the final scene envelope,
- continuity-note terms that may need human review.

Results can be exported as CSV and JSON. A zero-flag result means the current rules found no timestamp issue. It does not prove the story is continuous, and continuity-note matches are review prompts, not errors.

## Testing

Run from the project folder. On Windows (Command Prompt):

```bash
set PYTHONPATH=problem1_promos
python problem1_promos\test_promo.py
python problem1_promos\test_llm_ranker.py
set PYTHONPATH=problem2_legal
python problem2_legal\test_legal.py
set PYTHONPATH=problem3_continuity
python problem3_continuity\test_qc.py
```

On macOS / Linux, use `export PYTHONPATH=...` and forward slashes.

The tests cover:

- candidate duration,
- hybrid-score calculation,
- cost estimation,
- structured-response validation,
- rental-case handling and urgent-risk escalation,
- detection of a synthetic out-of-range timestamp.

During development the supplied 50-episode pack was also processed: 50 episode files were read, 3,727 timed entries were parsed, 100 promo candidates were generated, and the continuity checker returned 50 episode rows with zero timestamp flags under its current rules. These are rule-based observations, not proof of output quality.

## Confidentiality and version control

- Do not commit `.env`, API keys, screenplay source files or screenplay-derived outputs to a public repository.
- `.gitignore` excludes `.env`, `input_pack/`, `outputs/`, virtual environments and Python cache files.
- Keep assignment files and deliverables in the private submission location specified by the placement cell.

## Limitations

- Promo ranking relies on text patterns and cannot assess anything visual or audible.
- The LLM adds narrative interpretation but can be wrong or inconsistent, so scores are advisory.
- The rental helper covers one narrow scenario and is not legal advice.
- The continuity checker is rule-based and will miss issues outside its rules.
- Every output is a draft for human review.