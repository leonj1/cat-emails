.PHONY: build run clean test

# Docker image name
IMAGE_NAME = gmail-cleaner
TEST_IMAGE_NAME = gmail-cleaner-test

# Build the Docker image
build:
	docker build -t $(IMAGE_NAME) .

# Build the test Docker image
build-test:
	docker build -t $(TEST_IMAGE_NAME) -f Dockerfile.test .

# Run the container with environment variables
run:
	docker run --rm \
		-e GMAIL_EMAIL="$(GMAIL_EMAIL)" \
		-e GMAIL_PASSWORD="$(GMAIL_PASSWORD)" \
		$(IMAGE_NAME) \
		--hours $(or $(HOURS),2)

# Run the tests in Docker
test: build-test
	docker run --rm $(TEST_IMAGE_NAME)

# Clean up Docker images
clean:
	docker rmi $(IMAGE_NAME) $(TEST_IMAGE_NAME)

# Build and run in one command
all: build run
