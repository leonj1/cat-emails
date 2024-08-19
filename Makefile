.PHONY: build run

build:
	@echo "Building Docker image..."
	docker build -t gmail-categorizer .

run:
	@echo "Running Gmail Categorizer in Docker..."
	docker run --env-file .env gmail-categorizer python gmail_categorizer.py --ollama-host http://10.1.1.212:11434 --ollama-host2 http://10.1.1.131:11434 --hours 43850

run-a:
	@echo "Running Gmail Categorizer in Docker..."
	docker run --env-file .env gmail-categorizer python gmail_categorizer.py --anthropic-api-key $(ANTHROPIC_API_KEY) --hours 730

.DEFAULT_GOAL := run
