.PHONY: build

build:
	@echo "Building Docker image..."
	docker build -t gmail-categorizer .

skip:
	@echo "Cleaning up SkipInbox label..."
	docker run --env-file .env gmail-categorizer python gmail_categorizer.py --ollama-host http://10.1.1.144:11434 --ollama-host2 http://10.1.1.212:11434 --skip --hours 150000

run:
	@echo "Running Gmail Categorizer..."
	docker run --env-file .env gmail-categorizer python gmail_categorizer.py --ollama-host http://10.1.1.212:11434 --ollama-host2 http://10.1.1.144:11434 --hours 50000

run-a:
	@echo "Running Gmail Categorizer in Anthropic ..."
	docker run --env-file .env gmail-categorizer python gmail_categorizer.py --anthropic-api-key $(ANTHROPIC_API_KEY) --hours 500

.DEFAULT_GOAL := run
