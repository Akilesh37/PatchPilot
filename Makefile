.PHONY: install test benchmark train-smoke api web dev clean

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install fastapi uvicorn pydantic sqlalchemy rank-bm25 pytest GitPython javalang rich peft datasets python-multipart
	cd apps/web && npm install

test:
	.venv/bin/pytest tests/ -v

benchmark:
	.venv/bin/python3 scripts/run_benchmarks.py

train-smoke:
	.venv/bin/python3 ml/training/train_lora.py --smoke-test --epochs 1 --output checkpoints/smoke_test_lora

api:
	.venv/bin/uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

web:
	cd apps/web && npm run dev

dev:
	make -j 2 api web

clean:
	rm -rf .pytest_cache .venv checkpoints/smoke_test_lora apps/web/.next datasets/fixtures/*/target
