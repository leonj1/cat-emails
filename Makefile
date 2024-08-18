.PHONY: build run

build:
	@echo "Building Docker image..."
	docker build -t gmail-categorizer .

run:
	@echo "Running Gmail Categorizer in Docker..."
	docker run --env-file .env gmail-categorizer

.DEFAULT_GOAL := run
