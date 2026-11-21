# Kuku AI Generalist Lab

Three small, rerunnable prototypes prepared for the Kuku AI Generalist assignment. The placement-cell instruction was to complete all three problems, so the application keeps them in separate tabs. Human review remains part of each workflow.

## Included

- `app.py` — Streamlit application with all three tabs.
- `problem1_promos/` — timestamp parser, heuristic promo-window ranker, optional OpenAI evaluator, and tests.
- `problem2_legal/` — narrow rental security-deposit information organiser and refund-request drafter, with test cases.
- `problem3_continuity/` — timestamp and continuity-note review checks, with tests.
- `.env.example` — safe template for local API configuration.
- `SOLUTION_NOTES.md`, `SOLUTION_DOC.pdf`, `WALKTHROUGH_SCRIPT.txt` — explanation and interview preparation.

The confidential screenplay ZIP is intentionally not embedded in this project. Upload the supplied ZIP locally in the Promo Finder and Script Continuity QA tabs. Do not publish the screenplay pack or generated screenplay-derived outputs to a public repository.

## Setup (Windows)

1. Extract this ZIP into a folder.
2. Open the folder in File Explorer.
3. Double-click `start_windows.bat`.

Or run manually from Command Prompt in the project folder:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit (normally `http://localhost:8501`). Python 3.10+ is recommended.

## Optional OpenAI setup (Problem 1 only)

1. Copy `.env.example` to a new file named `.env` in this folder.
2. Put your own key in `OPENAI_API_KEY`.
3. Keep `.env` private; it is excluded by `.gitignore`.
4. Confirm `OPENAI_MODEL` is a model enabled for your API project. If needed, change it to the exact model ID shown in your OpenAI API account.
5. Restart Streamlit, upload the screenplay ZIP in Promo Finder, run the heuristic shortlist, then click **Evaluate top 10 with OpenAI**.

Cost controls include a maximum of 10 candidates per run, bounded screenplay excerpts, structured JSON output, output-token limits, a preflight estimated budget, usage-based cost estimation and a local cache. The heuristic score is retained. Hybrid score is 40% heuristic + 60% LLM. Failed LLM evaluations are not assigned a fake hybrid score; they are labelled as heuristic-only fallbacks.

The displayed cost is an estimate based on configured per-token rates and returned usage. Verify current model pricing independently; actual billing can differ. The API key and model access are controlled by your OpenAI account.

## Problem 1 — Find the Promos

Upload a ZIP containing timestamped `.txt` screenplay files. The Python baseline extracts candidate 20–60 second windows and ranks them using text-based signals. The optional OpenAI layer evaluates only the top 10 heuristic candidates for hook strength, emotional intensity, conflict/tension, cliffhanger strength and standalone clarity. It returns schema-constrained JSON, explanations and a comparison CSV/JSON.

Limitations: text alone cannot assess acting, facial expressions, visuals, music, shot composition or real audience performance. A human editor must preview candidate footage before publishing.

## Problem 2 — Rental Legal Helper

This is a deliberately narrow India-focused prototype for rental security-deposit disputes. It organises a tenant's account, identifies evidence to collect, suggests practical next steps and drafts a polite refund request. It is a rules-based information and drafting aid, not a lawyer and not a legal opinion. It does not cite statutes or case law; do not treat the output as legal advice. Users must verify dates, amounts, agreement clauses and local law, and seek qualified local advice where appropriate.

The UI presents the extracted case information in plain-language sections rather than raw JSON. Follow-up questions are limited to information that appears missing from the submitted account.

## Problem 3 — Script Continuity QA

Upload the same screenplay ZIP in the Script Continuity QA tab. The checker processes `.txt` files and reviews missing scene boundaries, backwards scene ordering, possible overlaps, timestamp entries outside the final scene envelope, and continuity-note terms that may need human review. It exports CSV and JSON.

A zero-flag result means the current rules did not detect a timestamp issue; it does not prove that the story is perfectly continuous. Continuity-note mismatches are review prompts, not automatic errors.

## Tests

Run these from the project folder:

```bash
set PYTHONPATH=problem1_promos
python problem1_promos\test_promo.py
python problem1_promos\test_llm_ranker.py
set PYTHONPATH=problem2_legal
python problem2_legal\test_legal.py
set PYTHONPATH=problem3_continuity
python problem3_continuity\test_qc.py
```

The included tests cover candidate duration, hybrid-score calculation, cost estimation, structured-response validation, rental-case handling, urgent-risk escalation and detection of a synthetic out-of-range timestamp. The supplied 50-episode screenplay ZIP was also processed during development: 50 episode files were read, 3,727 timed entries were parsed, 100 promo candidates were generated, and the continuity checker returned 50 episode rows with zero timestamp flags under its current rules. These are rule-based test observations, not proof of perfect output quality.

## Confidentiality and version control

- Do not commit `.env`, API keys, screenplay source files or screenplay-derived outputs to a public GitHub repository.
- `.gitignore` excludes `.env`, `input_pack/`, `outputs/`, virtual environments and Python cache files.
- Keep assignment files and deliverables in the private submission location specified by the placement cell.
