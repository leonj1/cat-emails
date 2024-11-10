.PHONY: build

build:
	@echo "Building Docker image..."
	docker build -t gmail-categorizer .

run:
	@echo "Running Gmail Categorizer..."
	docker run --env-file .env gmail-categorizer python gmail_categorizer.py --ollama-host http://10.1.1.212:11434 --ollama-host2 http://10.1.1.144:11434 --hours 50000

.DEFAULT_GOAL := run
