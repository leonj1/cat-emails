.PHONY: setup run

setup:
	@echo "Setting up the project..."
	pip install -r requirements.txt
	@echo "Setup complete. Make sure to add your credentials.json file to the project directory."

run:
	@echo "Running the Gmail Categorizer..."
	python gmail_categorizer.py

.DEFAULT_GOAL := run
