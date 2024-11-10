.PHONY: build run clean

# Docker image name
IMAGE_NAME = gmail-cleaner

# Build the Docker image
build:
	docker build -t $(IMAGE_NAME) .

# Run the container with environment variables
run:
	docker run --rm \
		-e GMAIL_EMAIL="$(GMAIL_EMAIL)" \
		-e GMAIL_PASSWORD="$(GMAIL_PASSWORD)" \
		$(IMAGE_NAME) \
		--hours $(or $(HOURS),2)

# Clean up Docker images
clean:
	docker rmi $(IMAGE_NAME)

# Build and run in one command
all: build run
