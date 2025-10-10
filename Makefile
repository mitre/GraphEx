# You can provide this variable when making to install the dependencies of a different directory
# e.g.: make all PLUGINS_DIR=/some/other/path
ifndef PLUGINS_DIR
override PLUGINS_DIR = ../graphex_plugins
endif

STARTING_DIR:=${CURDIR}

highlight = \033[1;36m
reset = \033[0m

help:
	@echo "Usage: make ${highlight}<command>${reset}"
	@echo "Commands:"
	@echo "\t${highlight}all${reset}: Build and install GraphEX locally."
	@echo "\t${highlight}build${reset}: Build the package for distribution or installation."
	@echo "\t${highlight}install${reset}: Install the built package locally."
	@echo "\t${highlight}remove${reset}: Remove the local installed package."
	@echo "\t${highlight}run${reset}: Build and run the GraphEX server (production build)."
	@echo "\t${highlight}run-dev${reset}: Build and run the GraphEX server (hot-reload for development)."
	@echo "\t${highlight}install-plugins${reset}: Install all plugins/packages from a directory (provide the 'PLUGINS_DIR' variable)."
	@echo "\t${highlight}docs${reset}: Build the HTML documentation."

all: remove build install

build:
	@cd frontend && npm install
	@cd frontend && npm run build
	$(MAKE) docs
	python3 -m build --wheel

install:
	pip install dist/*.whl --force-reinstall

remove:
	rm -rf dist build
	pip uninstall -y mitre-graphex

run-dev: docs
	@cd frontend && npm install
	@cd frontend && npm run dev-server

install-plugins:
	@for d in $(shell ls ${PLUGINS_DIR}); do cd ${STARTING_DIR} && cd ${PLUGINS_DIR}/$${d} && make all; done

docs:
	@cd frontend && node convertMarkdown.js
	@mkdir -p graphex/website/docs
	@cp -r docs/html graphex/website/docs

.PHONY: all build install install-plugins remove run run-dev docs