.PHONY: build publish publish-test clean install dev

# Install in development mode
dev:
	pip install -e .

# Install build tools
install-build:
	pip install build twine

# Build sdist and wheel
build: clean install-build
	python -m build

# Publish to PyPI
publish: build
	twine upload dist/*

# Publish to Test PyPI first (recommended for first-time)
publish-test: build
	twine upload --repository testpypi dist/*

# Clean build artifacts
clean:
	rm -rf dist/ build/ *.egg-info olympus_cli/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Check package before publishing
check: build
	twine check dist/*
