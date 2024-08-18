.PHONY: build run

build:
	@echo "Building Docker image..."
	docker build -t gmail-categorizer .

run:
	@echo "Running Gmail Categorizer in Docker..."
	docker run --env-file .env gmail-categorizer python gmail_categorizer.py --ollama-host http://10.1.1.212:11434

.DEFAULT_GOAL := run
