SHELL := /bin/bash
export REPO

########################################################################
# Optionale Remote-Repositories (können überschrieben werden)
########################################################################
REPO_BASE ?=
REPO_BUILDER ?=
REPO_DEV ?=
REPO_RELEASE ?=
IQ_BRAND_NAME ?= IQ Flow
IQ_SITE_NAME ?= iq_site

########################################################################
# Versionsdefinitionen (stabil – basierend auf kurzem Inhalts-Hash der Datei)
########################################################################
# Versionsdatei für dev und release:
VERSION := $(shell cat delivery/container-version)
# Für base: Gekürzter MD5-Hash der Dockerfile.base (ändert sich nur bei Änderung des Inhalts)
BASE_HASH := $(shell md5sum Dockerfile.base 2>/dev/null | cut -d' ' -f1 | cut -c1-8 || echo 0)
# Für builder: Gekürzter MD5-Hash der Dockerfile.builder
BUILDER_HASH := $(shell md5sum Dockerfile.builder 2>/dev/null | cut -d' ' -f1 | cut -c1-8 || echo 0)
# Effektiver Hash für builder: wenn sich entweder Base oder Builder ändert, muss Builder neu gebaut werden
# Wir kombinieren dafür beide Hashes
EFFECTIVE_BUILDER_HASH := $(shell echo "$(BASE_HASH)-$(BUILDER_HASH)" | md5sum | cut -d' ' -f1 | cut -c1-8)

# Lokale Image-Namen (ohne überflüssige Leerzeichen)
BASE_IMAGE      := {{ cookiecutter.image_prefix }}-base:$(BASE_HASH)
BUILDER_IMAGE   := {{ cookiecutter.image_prefix }}-builder:$(EFFECTIVE_BUILDER_HASH)
DEV_IMAGE       := {{ cookiecutter.image_prefix }}-dev:$(VERSION)
RELEASE_IMAGE   := {{ cookiecutter.image_prefix }}-release:$(VERSION)

########################################################################
# Hilfsfunktion: ensure_image_efficiently
########################################################################
# Parameter:
#   $1: Lokaler Image-Name (z.B. iq-base:<tag>)
#   $2: Optionaler Remote-Repository-Pfad (z.B. REPO_BASE)
#   $3: Build-Befehl (z.B. docker build -f Dockerfile.base -t $(BASE_IMAGE) .)
#   $4: Force-Flag (0 oder 1) - wenn 1, wird der Build erzwungen
#
# Diese Funktion:
#   - Prüft, ob das Image lokal vorhanden ist.
#   - Falls nicht: Prüft, ob es eine Remote-Referenz gibt.
#   - Prüft mit docker manifest inspect, ob das Image remote verfügbar ist.
#   - Wenn remote verfügbar, verwendet --build-arg IMAGE_SOURCE=[remote-url] für den Build.
#   - Falls remote nicht verfügbar, wird das Image mit Standardkonfiguration gebaut.
define ensure_image_efficiently
	@echo "Checking image $(1)..."
	@if [ "$(4)" = "1" ]; then \
		echo "Force rebuild of $(1)"; \
		$(3); \
	elif docker image inspect $(1) > /dev/null 2>&1; then \
		echo "Image $(1) already exists locally."; \
	else \
		NAME=$$(echo "$(1)" | cut -d: -f1); \
		TAG=$$(echo "$(1)" | cut -d: -f2); \
		REMOTE=""; \
		SKIP_BUILD=""; \
		if [ -n "$(2)" ]; then \
			REMOTE=$$(echo "$(2)" | grep -q ":" && echo "$(2)" || echo "$(2):$$TAG"); \
			echo "Checking if $$REMOTE is available..."; \
			if docker manifest inspect "$$REMOTE" > /dev/null 2>&1; then \
				echo "Remote image $$REMOTE is available"; \
				echo "Skipping build of $(1)"; \
				SKIP_BUILD="1"; \
			else \
				echo "Remote image $$REMOTE is not available"; \
			fi; \
		elif [ -n "$(REPO)" ]; then \
			REMOTE="$(REPO)/$$NAME:$$TAG"; \
			echo "Checking if $$REMOTE is available..."; \
			if docker manifest inspect "$$REMOTE" > /dev/null 2>&1; then \
				echo "Remote image $$REMOTE is available"; \
				echo "Skipping build of $(1)"; \
				SKIP_BUILD="1"; \
			else \
				echo "Remote image $$REMOTE is not available"; \
			fi; \
		fi; \
		if [ -z "$$SKIP_BUILD" ]; then \
			echo "Building image $(1), with: $(3)..."; \
			$(3); \
			if [ "$(PUSH)" = "1" ] && [ -n "$$REMOTE" ]; then \
				echo "Pushing $(1) to $$REMOTE..."; \
				docker tag $(1) "$$REMOTE"; \
				docker push "$$REMOTE"; \
				LATEST=$$(echo "$$REMOTE" | sed 's/:[^:]*$$/:latest/'); \
				docker tag $(1) "$$LATEST"; \
				docker push "$$LATEST"; \
			fi; \
		fi; \
	fi
endef

########################################################################
# Phony Targets
########################################################################
.PHONY: base builder dev release add-version test run-release stop-release clean-release

BUILD_ARGS := --build-arg IQ_BRAND_NAME="$(IQ_BRAND_NAME)" --build-arg IQ_SITE_NAME=$(IQ_SITE_NAME)

# base: Baut bzw. prüft das Base-Image und taggt es zusätzlich als latest.
base:
	$(call ensure_image_efficiently,$(BASE_IMAGE),$(REPO_BASE),docker build $(BUILD_ARGS) -f Dockerfile.base -t $(BASE_IMAGE) .,$(if $(findstring $@,$(MAKECMDGOALS)),$(FORCE),0))
	@if docker image inspect $(BASE_IMAGE) > /dev/null 2>&1; then \
		docker tag $(BASE_IMAGE) {{ cookiecutter.image_prefix }}-base:latest; \
		echo "Tagged $(BASE_IMAGE) as iq-base:latest"; \
	fi

# builder: Baut bzw. prüft das Builder-Image und taggt es zusätzlich als latest.
builder: base
	$(eval FULL_BASE_IMAGE := $(if $(REPO_BASE),$(REPO_BASE)/$(BASE_IMAGE),$(if $(REPO),$(REPO)/$(BASE_IMAGE),$(BASE_IMAGE))))
	@echo "Using BASE_IMAGE_SOURCE=$(FULL_BASE_IMAGE)"
	@echo "Would execute: docker build -f Dockerfile.builder -t $(BUILDER_IMAGE) --build-arg BASE_IMAGE_SOURCE=$(FULL_BASE_IMAGE) ."
	$(call ensure_image_efficiently,$(BUILDER_IMAGE),$(REPO_BUILDER),docker build $(BUILD_ARGS) -f Dockerfile.builder -t $(BUILDER_IMAGE) --build-arg BASE_IMAGE_SOURCE=$(FULL_BASE_IMAGE) .,$(if $(findstring $@,$(MAKECMDGOALS)),$(FORCE),0))
	@if docker image inspect $(BUILDER_IMAGE) > /dev/null 2>&1; then \
		docker tag $(BUILDER_IMAGE) {{ cookiecutter.image_prefix }}-builder:latest; \
		echo "Tagged $(BUILDER_IMAGE) as iq-builder:latest"; \
	fi

# dev: Baut (falls nötig) zuerst base und builder und anschließend das Dev-Image.
dev: base builder
	$(eval FULL_BUILDER_IMAGE := $(if $(REPO_BUILDER),$(REPO_BUILDER)/$(BUILDER_IMAGE),$(if $(REPO),$(REPO)/$(BUILDER_IMAGE),$(BUILDER_IMAGE))))
	$(eval FULL_BASE_IMAGE := $(if $(REPO_BASE),$(REPO_BASE)/$(BASE_IMAGE),$(if $(REPO),$(REPO)/$(BASE_IMAGE),$(BASE_IMAGE))))
	$(call ensure_image_efficiently,$(DEV_IMAGE),$(REPO_DEV),docker build $(BUILD_ARGS) -f Dockerfile.dev -t $(DEV_IMAGE) --target final --build-arg BUILDER_IMAGE_SOURCE=$(FULL_BUILDER_IMAGE) --build-arg BASE_IMAGE_SOURCE=$(FULL_BASE_IMAGE) .,$(if $(findstring $@,$(MAKECMDGOALS)),$(FORCE),0))
	@if docker image inspect $(DEV_IMAGE) > /dev/null 2>&1; then \
		docker tag $(DEV_IMAGE) {{ cookiecutter.image_prefix }}-dev:latest; \
		echo "Tagged $(DEV_IMAGE) as iq-dev:latest"; \
	fi

# release: Baut (falls nötig) zuerst base und builder und anschließend das Release-Image.
release: base dev
	$(eval FULL_BASE_IMAGE := $(if $(REPO_BASE),$(REPO_BASE)/$(BASE_IMAGE),$(if $(REPO),$(REPO)/$(BASE_IMAGE),$(BASE_IMAGE))))
	$(eval FULL_DEV_IMAGE := $(if $(REPO_DEV),$(REPO_DEV)/$(DEV_IMAGE),$(if $(REPO),$(REPO)/$(DEV_IMAGE),$(DEV_IMAGE))))
	$(call ensure_image_efficiently,$(RELEASE_IMAGE),$(REPO_RELEASE),docker build $(BUILD_ARGS) -f Dockerfile.release -t $(RELEASE_IMAGE) --target final --build-arg BASE_IMAGE_SOURCE=$(FULL_BASE_IMAGE) --build-arg DEV_IMAGE_SOURCE=$(FULL_DEV_IMAGE) . ,$(if $(findstring $@,$(MAKECMDGOALS)),$(FORCE),0))
	@if docker image inspect $(RELEASE_IMAGE) > /dev/null 2>&1; then \
		docker tag $(RELEASE_IMAGE) {{ cookiecutter.image_prefix }}-release:latest; \
		echo "Tagged $(RELEASE_IMAGE) as iq-release:latest"; \
	fi

########################################################################
# Test Target
########################################################################
# Usage:
#   make test                   - Run all tests with default settings
#   make test APP=iq_core       - Run tests for a specific app
#   make test MODULE=app.module - Run tests for a specific module
#   make test DOCTYPE=MyType    - Run tests for a specific doctype
#   make test TEST=test_func    - Run a specific test function
#   make test SECTION=Auth      - Run tests for a specific section
#   make test CONTINUE=1        - Continue running tests even after failures
#
# Environment variables:
#   DBMS:     Database system to use (postgres or mariadb)
#   APP:      Filter tests by app
#   SECTION:  Only run a specific SECTION
#   CONTINUE: Set to 1 to continue on errors (default is to stop on first error)
#
#   IQ_SITE_NAME: needs to start with "test_" (default: test_iq_site)
#   PG_HOST:  PostgreSQL host (default: localhost)
#   PG_PORT:  PostgreSQL port (default: 5432)
#   PG_SUPER_USER: Needs also to start with "test_" (default: test_iq_su)
#   PG_SUPER_USER_PW:
#   PG_SCHEMA: PG Schema name (default: iq_schema)
test:
	$(eval override IQ_SITE_NAME := $(if $(filter test_%,$(IQ_SITE_NAME)),$(IQ_SITE_NAME),test_{{ cookiecutter.image_prefix }}_site))
	$(eval override DBMS := $(if $(DBMS),$(DBMS),postgres))
	$(eval override PG_SUPER_USER := $(if $(filter test_%,$(PG_SUPER_USER)),$(PG_SUPER_USER),test_{{ cookiecutter.image_prefix }}_su))
	
	@echo "Starting tests with database: $(DBMS), using site name: $(IQ_SITE_NAME)"
	@if [ "$(DBMS)" = "postgres" ]; then \
		# first switch to bench dir \
		cd ../../; \
		# Check if $IQ_SITE_NAME exists already \
		if [ ! -d "sites/$(IQ_SITE_NAME)" ]; then \
			echo "Creating test site $(IQ_SITE_NAME)..."; \
			IQ_ADMIN_PW=admin \
			IQ_SITE_NAME=$(IQ_SITE_NAME) \
			bash apps/iq_core/.devcontainer/bin/init_site.sh; \
		fi; \
		echo "Running tests..."; \
		{ \
			TEST_CMD="bench --site $(IQ_SITE_NAME) run-iq-tests"; \
			if [ -n "$(APP)" ]; then \
				TEST_CMD="$$TEST_CMD --app $(APP)"; \
			fi; \
			if [ -n "$(MODULE)" ]; then \
				TEST_CMD="$$TEST_CMD --module $(MODULE)"; \
			fi; \
			if [ -n "$(DOCTYPE)" ]; then \
				TEST_CMD="$$TEST_CMD --doctype $(DOCTYPE)"; \
			fi; \
			if [ -n "$(TEST)" ]; then \
				TEST_CMD="$$TEST_CMD --test $(TEST)"; \
			fi; \
			if [ -n "$(SECTION)" ]; then \
				TEST_CMD="$$TEST_CMD --section $(SECTION)"; \
				fi; \
			if [ -n "$(CONTINUE)" ] && [ "$(CONTINUE)" = "1" ]; then \
				TEST_CMD="$$TEST_CMD --continue-on-error"; \
			fi; \
			echo "Executing: $$TEST_CMD"; \
			eval $$TEST_CMD; \
		} \
	elif [ "$(DBMS)" = "mariadb" ]; then \
		echo "Using MariaDB database for tests"; \
		# Here would be MariaDB-specific test site creation and execution \
		echo "MariaDB testing not implemented yet"; \
	else \
		echo "Unknown database type: $(DBMS)."; \
	fi

########################################################################
# Version bumping Targets
########################################################################
add-version:
	@current_version=`cat delivery/container-version`; \
	IFS=. read major minor patch <<< "$$current_version"; \
	if [ -z "$(VERSION_COMPONENT)" ]; then \
		echo "Current version: $$current_version"; \
		echo -e "Select component to increment\n\t[m]ajor\n\t[f]eature\n\t[b]ugfix: "; \
		read -p "Choose: m, f, b (default: feature) " component; \
		case $$component in \
			m) component_type="major" ;; \
			f) component_type="feature" ;; \
			b) component_type="bugfix" ;; \
			*) echo "Invalid selection. Using feature as default."; component_type="feature" ;; \
		esac; \
	else \
		component_type="$(VERSION_COMPONENT)"; \
	fi; \
	if [ "$$component_type" = "major" ]; then \
	  new_major=$$((major + 1)); \
	  new_version="$$new_major.0.0"; \
	  echo "Incrementing major version: $$current_version -> $$new_version"; \
	elif [ "$$component_type" = "bugfix" ]; then \
	  new_patch=$$((patch + 1)); \
	  new_version="$$major.$$minor.$$new_patch"; \
	  echo "Incrementing bugfix version: $$current_version -> $$new_version"; \
	elif [ "$$component_type" = "feature" ]; then \
	  new_minor=$$((minor + 1)); \
	  new_version="$$major.$$new_minor.0"; \
	  echo "Incrementing feature version: $$current_version -> $$new_version"; \
	else \
	  echo "Invalid component type: $$component_type. Using feature as default."; \
	  new_minor=$$((minor + 1)); \
	  new_version="$$major.$$new_minor.0"; \
	  echo "Incrementing feature version: $$current_version -> $$new_version"; \
	fi; \
	echo $$new_version > delivery/container-version; \
	sed -i 's/__version__ = "[0-9]*\.[0-9]*\.[0-9]*"/__version__ = "'$$new_version'"/' iq_core/__init__.py; \
	echo "Updated version in delivery/container-version and iq_core/__init__.py to $$new_version"; \
	if [ "$(COMMIT)" = "1" ]; then \
		git add delivery/container-version {{ cookiecutter.app_name }}/__init__.py; \
		git commit -m "upd: Bump version to $$new_version"; \
		echo "Committed version bump"; \
	fi

########################################################################
# Docker Compose Targets for Release Environment
########################################################################
run-release:
	@echo "Configuration is ready."
	@chmod +x ./ops/scripts/run_release_helper.sh
	@./ops/scripts/run_release_helper.sh $(ENV_FILE)

stop-release:
	@echo "Stopping dockerized environment..."
	@chmod +x ./ops/scripts/stop_release_helper.sh
	@./ops/scripts/stop_release_helper.sh

clean-release:
	@echo "Cleaning dockerized environment..."
	@chmod +x ./ops/scripts/clean_release_helper.sh
	@./ops/scripts/clean_release_helper.sh

