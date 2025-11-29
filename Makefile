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

.PHONY: build run clean test service-build service-run service-stop service-logs api-build api-run api-stop api-logs summary-morning summary-evening summary-weekly summary-monthly api-health

# Docker image name
IMAGE_NAME = gmail-cleaner
TEST_IMAGE_NAME = gmail-cleaner-test
SERVICE_IMAGE_NAME = gmail-cleaner-api
CONSOLIDATOR_IMAGE_NAME = gmail-label-consolidator
EMAIL_TEST_IMAGE_NAME = gmail-email-test
API_IMAGE_NAME = gmail-cleaner-api


# Build the service Docker image
build:
	docker build -t $(SERVICE_IMAGE_NAME) -f Dockerfile.service .

# Run the service container
start: validate-env
	@echo "Starting Gmail Cleaner Service..."
	@echo "Configuration:"
	@echo "  - Scan interval: $(or $(SCAN_INTERVAL),2) minutes"
	@echo "  - Hours to look back: $(or $(HOURS),2)"
	@echo "  - Summaries enabled: $(or $(ENABLE_SUMMARIES),true)"
	@echo "  - Morning summary: $(or $(MORNING_HOUR),5):$(or $(MORNING_MINUTE),30) ET"
	@echo "  - Evening summary: $(or $(EVENING_HOUR),16):$(or $(EVENING_MINUTE),30) ET"
	@echo "  - Primary Ollama host: $(or $(OLLAMA_HOST_PRIMARY),100.100.72.86:11434)"
	@echo "  - Secondary Ollama host: $(or $(OLLAMA_HOST_SECONDARY),100.91.167.71:11434)"
	@docker stop $(SERVICE_IMAGE_NAME) 2>/dev/null || true
	@docker rm $(SERVICE_IMAGE_NAME) 2>/dev/null || true
	docker run -d \
		--name $(SERVICE_IMAGE_NAME) \
		-e GMAIL_EMAIL="$(GMAIL_EMAIL)" \
		-e GMAIL_PASSWORD="$(GMAIL_PASSWORD)" \
		-e CONTROL_API_TOKEN="$(CONTROL_API_TOKEN)" \
		-e HOURS=$(or $(HOURS),120) \
		-e SCAN_INTERVAL=$(or $(SCAN_INTERVAL),5) \
		-e ENABLE_SUMMARIES=$(or $(ENABLE_SUMMARIES),true) \
		-e SUMMARY_RECIPIENT_EMAIL=$(or $(SUMMARY_RECIPIENT_EMAIL),$(GMAIL_EMAIL)) \
		-e SMTP_USERNAME="$(SMTP_USERNAME)" \
		-e SMTP_PASSWORD="$(SMTP_PASSWORD)" \
		-e MAILTRAP_API_TOKEN="$(MAILTRAP_API_TOKEN)" \
		-e OLLAMA_HOST_PRIMARY=$(or $(OLLAMA_HOST_PRIMARY),100.100.72.86:11434) \
		-e OLLAMA_HOST_SECONDARY=$(or $(OLLAMA_HOST_SECONDARY),100.91.167.71:11434) \
		-e MORNING_HOUR=$(or $(MORNING_HOUR),5) \
		-e MORNING_MINUTE=$(or $(MORNING_MINUTE),30) \
		-e EVENING_HOUR=$(or $(EVENING_HOUR),16) \
		-e EVENING_MINUTE=$(or $(EVENING_MINUTE),30) \
		-e REQUESTYAI_API_KEY="$(REQUESTY_API_KEY)" \
		-e REQUESTY_API_URL="$(REQUESTY_API_URL)" \
		--restart unless-stopped \
		$(SERVICE_IMAGE_NAME)
	@echo "Service started. Use 'make service-logs' to view logs."

# Stop the service container
stop:
	@echo "Stopping Gmail Cleaner Service..."
	docker stop -t 0 $(SERVICE_IMAGE_NAME) || true
	docker rm -f $(SERVICE_IMAGE_NAME) || true
	@echo "Service stopped."

restart: stop start

# View service logs
logs:
	docker logs -f $(SERVICE_IMAGE_NAME)

# Build the API Docker image
api-build:
	docker build -t $(API_IMAGE_NAME) -f Dockerfile.api .

# Run the API container
api-run:
	@echo "Starting Gmail Cleaner API..."
	@echo "Configuration:"
	@echo "  - API Port: $(or $(API_PORT),8000)"
	@echo "  - API Key Required: $(if $(API_KEY),Yes,No)"
	@mkdir -p email_summaries
	@docker stop $(API_IMAGE_NAME) 2>/dev/null || true
	@docker rm $(API_IMAGE_NAME) 2>/dev/null || true
	docker run -d \
		--name $(API_IMAGE_NAME) \
		-p $(or $(API_PORT),8000):8000 \
		-v $(shell pwd)/email_summaries:/app/email_summaries \
		-e API_KEY="$(API_KEY)" \
		-e GMAIL_EMAIL="$(GMAIL_EMAIL)" \
		-e SUMMARY_RECIPIENT_EMAIL=$(or $(SUMMARY_RECIPIENT_EMAIL),$(GMAIL_EMAIL)) \
		-e MAILTRAP_API_TOKEN="$(MAILTRAP_API_TOKEN)" \
		-e REQUESTYAI_API_KEY="$(REQUESTYAI_API_KEY)" \
		-e OPENAI_API_KEY="$(OPENAI_API_KEY)" \
		--restart unless-stopped \
		$(API_IMAGE_NAME)
	@echo "API started on port $(or $(API_PORT),8000). Use 'make api-logs' to view logs."
	@echo "API documentation available at: http://localhost:$(or $(API_PORT),8000)/docs"


# Stop the API container
api-stop:
	@echo "Stopping Gmail Cleaner API..."
	docker stop $(API_IMAGE_NAME)
	docker rm $(API_IMAGE_NAME)
	@echo "API stopped."

# View API logs
api-logs:
	docker logs -f $(API_IMAGE_NAME)

# Force send morning summary
summary-morning:
	@echo "Triggering morning summary..."
	@if [ -n "$(API_KEY)" ]; then \
		curl -X POST http://localhost:$(or $(API_PORT),8000)/api/summaries/morning \
			-H "X-API-Key: $(API_KEY)" \
			-H "Content-Type: application/json" \
			-s | jq '.' || echo "Failed to trigger morning summary"; \
	else \
		curl -X POST http://localhost:$(or $(API_PORT),8000)/api/summaries/morning \
			-H "Content-Type: application/json" \
			-s | jq '.' || echo "Failed to trigger morning summary"; \
	fi

# Force send evening summary
summary-evening:
	@echo "Triggering evening summary..."
	@if [ -n "$(API_KEY)" ]; then \
		curl -X POST http://localhost:$(or $(API_PORT),8000)/api/summaries/evening \
			-H "X-API-Key: $(API_KEY)" \
			-H "Content-Type: application/json" \
			-s | jq '.' || echo "Failed to trigger evening summary"; \
	else \
		curl -X POST http://localhost:$(or $(API_PORT),8000)/api/summaries/evening \
			-H "Content-Type: application/json" \
			-s | jq '.' || echo "Failed to trigger evening summary"; \
	fi

# Force send weekly summary
summary-weekly:
	@echo "Triggering weekly summary..."
	@if [ -n "$(API_KEY)" ]; then \
		curl -X POST http://localhost:$(or $(API_PORT),8000)/api/summaries/weekly \
			-H "X-API-Key: $(API_KEY)" \
			-H "Content-Type: application/json" \
			-s | jq '.' || echo "Failed to trigger weekly summary"; \
	else \
		curl -X POST http://localhost:$(or $(API_PORT),8000)/api/summaries/weekly \
			-H "Content-Type: application/json" \
			-s | jq '.' || echo "Failed to trigger weekly summary"; \
	fi

# Force send monthly summary
summary-monthly:
	@echo "Triggering monthly summary..."
	@if [ -n "$(API_KEY)" ]; then \
		curl -X POST http://localhost:$(or $(API_PORT),8000)/api/summaries/monthly \
			-H "X-API-Key: $(API_KEY)" \
			-H "Content-Type: application/json" \
			-s | jq '.' || echo "Failed to trigger monthly summary"; \
	else \
		curl -X POST http://localhost:$(or $(API_PORT),8000)/api/summaries/monthly \
			-H "Content-Type: application/json" \
			-s | jq '.' || echo "Failed to trigger monthly summary"; \
	fi

# Check API health
api-health:
	@echo "Checking API health..."
	@curl -s http://localhost:$(or $(API_PORT),8000)/api/health | jq '.' || echo "API is not responding"

# Run tests
test:
	docker build -t $(TEST_IMAGE_NAME) -f Dockerfile.test .
	docker run --rm $(TEST_IMAGE_NAME)

# Clean up Docker images
clean:
	docker rmi $(IMAGE_NAME) $(TEST_IMAGE_NAME) $(SERVICE_IMAGE_NAME) $(API_IMAGE_NAME)

# Build and run in one command
all: build start

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

# Run PendingRollbackError integration test with MySQL
test-pending-rollback-integration:
	@echo "Starting MySQL container for integration tests..."
	docker compose -f docker-compose.test.yml up -d mysql-test
	@echo "Waiting for MySQL to be healthy..."
	@timeout 60 sh -c 'until docker compose -f docker-compose.test.yml exec -T mysql-test mysqladmin ping -h localhost -u root -prootpassword 2>/dev/null; do sleep 2; done'
	@echo "Running PendingRollbackError integration tests..."
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit integration-test
	@echo "Cleaning up..."
	docker compose -f docker-compose.test.yml down -v

# Clean up integration test containers
test-integration-clean:
	docker compose -f docker-compose.test.yml down -v --remove-orphans
