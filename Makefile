.PHONY: test test-api test-worker run-api run-web worker-pb worker-apple

test: test-api test-worker

test-api:
	pytest api/tests

test-worker:
	pytest worker/tests

run-api:
	cd api && uvicorn app.main:app --reload --port 8000

run-web:
	cd web && npm run dev

worker-pb:
	cd worker && python -m worker.main --retailer pb-tech

worker-apple:
	cd worker && python -m worker.main --retailer apple
