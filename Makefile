.PHONY: setup run build docker-run

setup:
	@echo "Setting up the project..."
	pip install -r requirements.txt
	@echo "Setup complete."

run:
	@echo "Running the Gmail Categorizer..."
	python gmail_categorizer.py

build:
	@echo "Building Docker image..."
	docker build -t gmail-categorizer .

docker-run:
	@echo "Running Gmail Categorizer in Docker..."
	docker run --env-file .env gmail-categorizer

.DEFAULT_GOAL := run
