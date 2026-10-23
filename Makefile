.PHONY: run test eval clean

PROFILE ?= A
SAMPLE_MODE ?= true

run:
	SAMPLE_MODE=$(SAMPLE_MODE) python -m src.dd.main --profile $(PROFILE)

test:
	python -m pytest tests/ -v --tb=short

eval:
	python eval/run_eval.py

smoke-zetaris:
	python scripts/smoke_zetaris.py

smoke-nightshift:
	python scripts/smoke_nightshift.py

clean:
	rm -rf runs/ cache/ __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
