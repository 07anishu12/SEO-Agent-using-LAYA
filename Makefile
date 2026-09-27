.PHONY: dev down test clean

# Start full development stack (Docker infra + native backend, worker, beat, frontend)
dev:
	./scripts/dev.sh

# Stop and tear down Docker infra containers (Postgres, Redis, MinIO)
down:
	./scripts/dev.sh --full-down

# Run automated test suites
test:
	PYTHONPATH=. pytest tests/ -v

# Clean pycache and build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf frontend/.next frontend/node_modules/.cache
