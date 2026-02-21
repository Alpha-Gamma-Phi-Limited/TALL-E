.PHONY: test test-api test-worker run-api run-web worker-pb worker-apple worker-all

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

# Run ingestion for every retailer sequentially. Failures are logged but do not
# stop the run. Uses a 1 s inter-request delay for politeness.
WORKER_RETAILERS := \
	pb-tech jb-hi-fi noel-leeming noel-leeming-home \
	harvey-norman harvey-norman-home \
	apple \
	mighty-ape mighty-ape-home \
	heathcotes heathcotes-home \
	chemist-warehouse chemist-warehouse-supplements \
	bargain-chemist bargain-chemist-supplements \
	life-pharmacy \
	mecca sephora supplements-co-nz \
	animates petdirect pet-co-nz \
	farmers farmers-home \
	the-warehouse the-warehouse-home

worker-all:
	@cd worker && \
	PASS=0; FAIL=0; FAILED_LIST=""; \
	echo "Starting full ingestion run — $(words $(WORKER_RETAILERS)) retailers"; \
	for r in $(WORKER_RETAILERS); do \
		echo ""; \
		echo "=== $$r ==="; \
		if python -m worker.main \
			--retailer $$r \
			--request-delay-seconds 1.0 \
			--max-fetch-retries 3 \
			--retry-backoff-seconds 1.5 \
			--max-products 120; then \
			PASS=$$((PASS+1)); \
		else \
			FAIL=$$((FAIL+1)); FAILED_LIST="$$FAILED_LIST $$r"; \
			echo "FAILED: $$r"; \
		fi; \
	done; \
	echo ""; \
	echo "=== Summary: $$PASS passed, $$FAIL failed ==="; \
	if [ -n "$$FAILED_LIST" ]; then echo "Failed retailers:$$FAILED_LIST"; fi
