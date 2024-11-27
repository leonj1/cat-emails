# Include .env file if it exists
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Validate required environment variables
validate-env:
	@if [ -z "$(GMAIL_EMAIL)" ] || [ -z "$(GMAIL_PASSWORD)" ] || [ -z "$(CONTROL_API_TOKEN)" ]; then \
		echo "Error: Required environment variables are missing. Please set them in .env file:"; \
		echo "GMAIL_EMAIL, GMAIL_PASSWORD, and CONTROL_API_TOKEN"; \
		exit 1; \
	fi

.PHONY: build run clean test

# Docker image name
IMAGE_NAME = gmail-cleaner
TEST_IMAGE_NAME = gmail-cleaner-test

# Build the Docker image
build:
	docker build -t $(IMAGE_NAME) .

# Run the container with environment variables
run: validate-env
	@if [ -z "$(GMAIL_EMAIL)" ] || [ -z "$(GMAIL_PASSWORD)" ] || [ -z "$(CONTROL_API_TOKEN)" ]; then \
		echo "Error: Required environment variables are missing. Please set them in .env file:"; \
		echo "GMAIL_EMAIL, GMAIL_PASSWORD, and CONTROL_API_TOKEN"; \
		exit 1; \
	fi
	docker run --rm \
		-e GMAIL_EMAIL="$(GMAIL_EMAIL)" \
		-e GMAIL_PASSWORD="$(GMAIL_PASSWORD)" \
		-e CONTROL_API_TOKEN="$(CONTROL_API_TOKEN)" \
		$(IMAGE_NAME) \
		--base-url "10.1.1.144:11434" \
		--hours 2

# Run tests
test:
	docker build -t gmail-cleaner-test -f Dockerfile.test .
	docker run --rm gmail-cleaner-test python -m pytest tests/ -v

# Clean up Docker images
clean:
	docker rmi $(IMAGE_NAME) $(TEST_IMAGE_NAME)

# Build and run in one command
all: build run
