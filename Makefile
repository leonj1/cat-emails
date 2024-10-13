.PHONY: build run run-api

CONTAINER_NAME=gmail-categorizer
PORT=4300

build:
	@echo "Building Docker image..."
	docker build -t gmail-categorizer .

run:
	@echo "Running Gmail Categorizer and FastAPI..."
	docker run --rm --name $(CONTAINER_NAME) --env-file .env -p $(PORT):8000 gmail-categorizer

stop:
	@echo "Stopping container..."
	docker stop -t 0 $(CONTAINER_NAME) || true
	docker rm -f $(CONTAINER_NAME) || true

.DEFAULT_GOAL := run