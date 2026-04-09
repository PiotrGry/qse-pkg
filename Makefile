# QSE - Quality Score Engine
# Reproducible benchmark targets

PYTHON := python3
SCRIPTS := scripts
ARTIFACTS := artifacts/benchmark
CLONE_DIR ?= /tmp/qse-benchmark-repos

.PHONY: help install build test benchmark benchmark-python benchmark-java benchmark-go \
        pin-commits sonar known-good-bad reproduce clean-clones

help:
	@echo "QSE Makefile targets:"
	@echo "  install          Install QSE in development mode"
	@echo "  build            Build Rust scanner (qse-core)"
	@echo "  test             Run pytest suite"
	@echo "  benchmark        Run full benchmark (Python+Java+Go)"
	@echo "  benchmark-python Run Python-80 benchmark only"
	@echo "  benchmark-java   Run Java-80 benchmark only"
	@echo "  benchmark-go     Run Go-80 benchmark only"
	@echo "  pin-commits      Pin HEAD commits in repo list JSONs"
	@echo "  known-good-bad   Run known-good vs known-bad validation"
	@echo "  sonar            Run SonarQube cross-validation"
	@echo "  reproduce        Full reproduction from scratch"
	@echo "  clean-clones     Remove cloned repos"

install:
	$(PYTHON) -m pip install -e .

build:
	export PATH="$$HOME/.cargo/bin:$$PATH" && \
	$(PYTHON) -m maturin develop --release -m qse-py/Cargo.toml

test:
	$(PYTHON) -m pytest tests/ -x -q

# --- Benchmarks ---

benchmark: benchmark-python benchmark-java benchmark-go

benchmark-python:
	$(PYTHON) $(SCRIPTS)/agq_multilang_benchmark.py \
		--repos-file $(SCRIPTS)/repos_oss80_benchmark.json \
		--repos-dir $(CLONE_DIR)/python \
		--output-json $(ARTIFACTS)/reproduced_python80.json \
		--output-md $(ARTIFACTS)/reproduced_python80.md

benchmark-java:
	$(PYTHON) $(SCRIPTS)/agq_multilang_benchmark.py \
		--repos-file $(SCRIPTS)/repos_java80_benchmark.json \
		--repos-dir $(CLONE_DIR)/java \
		--output-json $(ARTIFACTS)/reproduced_java80.json \
		--output-md $(ARTIFACTS)/reproduced_java80.md

benchmark-go:
	$(PYTHON) $(SCRIPTS)/agq_multilang_benchmark.py \
		--repos-file $(SCRIPTS)/repos_go80_benchmark.json \
		--repos-dir $(CLONE_DIR)/go \
		--output-json $(ARTIFACTS)/reproduced_go80.json \
		--output-md $(ARTIFACTS)/reproduced_go80.md

# --- Validation ---

pin-commits:
	$(PYTHON) $(SCRIPTS)/pin_commits.py --all

known-good-bad:
	$(PYTHON) $(SCRIPTS)/known_good_bad_validation.py

sonar:
	docker-compose up -d sonar-qse
	@echo "Waiting for SonarQube to start..."
	@sleep 30
	$(PYTHON) $(SCRIPTS)/sonar_cross_validation.py

# --- Reproduction ---

reproduce: pin-commits
	bash $(SCRIPTS)/reproduce_benchmark.sh

clean-clones:
	rm -rf $(CLONE_DIR)
