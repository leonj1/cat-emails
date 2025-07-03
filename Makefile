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

.PHONY: build run clean test service-build service-run service-stop service-logs

# Docker image name
IMAGE_NAME = gmail-cleaner
TEST_IMAGE_NAME = gmail-cleaner-test
SERVICE_IMAGE_NAME = gmail-cleaner-service
CONSOLIDATOR_IMAGE_NAME = gmail-label-consolidator
EMAIL_TEST_IMAGE_NAME = gmail-email-test

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
		--hours $(or $(HOURS),2)

# Build the service Docker image
service-build:
	docker build -t $(SERVICE_IMAGE_NAME) -f Dockerfile.service .

# Run the service container
service-run: validate-env
	@echo "Starting Gmail Cleaner Service..."
	@echo "Configuration:"
	@echo "  - Scan interval: $(or $(SCAN_INTERVAL),2) minutes"
	@echo "  - Hours to look back: $(or $(HOURS),2)"
	@echo "  - Summaries enabled: $(or $(ENABLE_SUMMARIES),true)"
	@docker stop $(SERVICE_IMAGE_NAME) 2>/dev/null || true
	@docker rm $(SERVICE_IMAGE_NAME) 2>/dev/null || true
	docker run -d \
		--name $(SERVICE_IMAGE_NAME) \
		-e GMAIL_EMAIL="$(GMAIL_EMAIL)" \
		-e GMAIL_PASSWORD="$(GMAIL_PASSWORD)" \
		-e CONTROL_API_TOKEN="$(CONTROL_API_TOKEN)" \
		-e HOURS=$(or $(HOURS),2) \
		-e SCAN_INTERVAL=$(or $(SCAN_INTERVAL),2) \
		-e ENABLE_SUMMARIES=$(or $(ENABLE_SUMMARIES),true) \
		-e SUMMARY_RECIPIENT_EMAIL=$(or $(SUMMARY_RECIPIENT_EMAIL),$(GMAIL_EMAIL)) \
		-e SMTP_USERNAME="$(SMTP_USERNAME)" \
		-e SMTP_PASSWORD="$(SMTP_PASSWORD)" \
		--restart unless-stopped \
		$(SERVICE_IMAGE_NAME)
	@echo "Service started. Use 'make service-logs' to view logs."

# Stop the service container
service-stop:
	@echo "Stopping Gmail Cleaner Service..."
	docker stop $(SERVICE_IMAGE_NAME)
	docker rm $(SERVICE_IMAGE_NAME)
	@echo "Service stopped."

# View service logs
service-logs:
	docker logs -f $(SERVICE_IMAGE_NAME)

# Run tests
test:
	docker build -t $(TEST_IMAGE_NAME) -f Dockerfile.test .
	docker run --rm $(TEST_IMAGE_NAME)

# Clean up Docker images
clean:
	docker rmi $(IMAGE_NAME) $(TEST_IMAGE_NAME) $(SERVICE_IMAGE_NAME)

# Build and run in one command
all: build run

# Build consolidator image
consolidator-build:
	docker build -t $(CONSOLIDATOR_IMAGE_NAME) -f Dockerfile.consolidator .

# Check label consolidation
check-consolidate: consolidator-build
	@if [ -z "$(GMAIL_EMAIL)" ] || [ -z "$(GMAIL_PASSWORD)" ]; then \
		echo "Error: Required environment variables are missing. Please set them in .env file:"; \
		echo "GMAIL_EMAIL and GMAIL_PASSWORD"; \
		exit 1; \
	fi
	@echo "Checking Gmail label consolidation..."
	@echo "Maximum labels: $(or $(MAX_LABELS),25)"
	@docker run --rm \
		-e GMAIL_EMAIL="$(GMAIL_EMAIL)" \
		-e GMAIL_PASSWORD="$(GMAIL_PASSWORD)" \
		$(CONSOLIDATOR_IMAGE_NAME) \
		--max-labels $(or $(MAX_LABELS),25)

# Build email test image
email-test-build:
	docker build -t $(EMAIL_TEST_IMAGE_NAME) -f Dockerfile.email-test .

# Run email integration test
test-email-integration: email-test-build
	@if [ -z "$(MAILTRAP_KEY)" ]; then \
		echo "Error: MAILTRAP_KEY environment variable is required"; \
		echo "Set it with: export MAILTRAP_KEY='your-api-token'"; \
		exit 1; \
	fi
	@echo "Running email integration test in Docker..."
	@echo "Sending test email to: leonj1@gmail.com"
	@docker run --rm \
		-e MAILTRAP_KEY="$(MAILTRAP_KEY)" \
		$(EMAIL_TEST_IMAGE_NAME)

# Run mailfrom.dev SMTP integration test
test-mailfrom-integration: email-test-build
	@if [ -z "$(SMTP_USERNAME)" ] || [ -z "$(SMTP_PASSWORD)" ]; then \
		echo "Error: SMTP_USERNAME and SMTP_PASSWORD environment variables are required"; \
		echo "Set them with:"; \
		echo "  export SMTP_USERNAME='your-smtp-username'"; \
		echo "  export SMTP_PASSWORD='your-smtp-password'"; \
		exit 1; \
	fi
	@echo "Running mailfrom.dev SMTP integration test in Docker..."
	@echo "Sending test email to: leonj1@gmail.com"
	@docker run --rm \
		--entrypoint python \
		-e SMTP_USERNAME="$(SMTP_USERNAME)" \
		-e SMTP_PASSWORD="$(SMTP_PASSWORD)" \
		$(EMAIL_TEST_IMAGE_NAME) \
		tests/test_mailfrom_integration.py
