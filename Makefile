.PHONY: run ui test eval clean audit smoke-zetaris smoke-nightshift

PROFILE ?= A
SAMPLE_MODE ?= true
PORT ?= 7860

# ── CLI pipeline run ────────────────────────────────────────────────
run:
	SAMPLE_MODE=$(SAMPLE_MODE) python -m src.dd.main --profile $(PROFILE)

# ── Web UI (FastAPI + static frontend) ─────────────────────────────
ui:
	SAMPLE_MODE=true uvicorn app.server:app --reload --port $(PORT)

# ── Tests ───────────────────────────────────────────────────────────
test:
	python -m pytest tests/ -v --tb=short

# ── Eval ────────────────────────────────────────────────────────────
eval:
	python -m src.dd.eval

# ── Compliance & Judging Audit ──────────────────────────────────────
audit:
	python scripts/audit.py

# ── Smoke tests ─────────────────────────────────────────────────────
smoke-zetaris:
	python scripts/smoke_zetaris.py

smoke-nightshift:
	python scripts/smoke_nightshift.py

# ── Clean ───────────────────────────────────────────────────────────
clean:
	python -c "import shutil, os, glob; [shutil.rmtree(p, ignore_errors=True) for p in glob.glob('runs/run_*') + glob.glob('**/__pycache__', recursive=True) + ['.pytest_cache']]"
