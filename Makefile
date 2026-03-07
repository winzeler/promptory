# SAM Makefile-based build — controls exactly what gets packaged for Lambda

.PHONY: build-ApiFunction build-CleanupFunction

PIP_PLATFORM = --platform manylinux2014_x86_64 --only-binary=:all: --implementation cp --python-version 3.12

build-ApiFunction:
	pip install -r requirements.txt -t $(ARTIFACTS_DIR)/ $(PIP_PLATFORM)
	cp -r server $(ARTIFACTS_DIR)/server
	cp -r scripts $(ARTIFACTS_DIR)/scripts
	cp VERSION $(ARTIFACTS_DIR)/VERSION

build-CleanupFunction:
	pip install -r requirements.txt -t $(ARTIFACTS_DIR)/ $(PIP_PLATFORM)
	cp -r server $(ARTIFACTS_DIR)/server
	cp -r scripts $(ARTIFACTS_DIR)/scripts
	cp VERSION $(ARTIFACTS_DIR)/VERSION
