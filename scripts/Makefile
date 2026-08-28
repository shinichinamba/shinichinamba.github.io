# Build entry points.
#
# Kept inside scripts/ deliberately: _config.yml already excludes "scripts",
# so this file is never copied into _site. A Makefile at the repository root
# would be published as a static file (as docs/package-lock.json shows).
#
# Usage:  make -C scripts all

PY ?= python3
ROOT := $(CURDIR)/..

.PHONY: all validate data cv site verify check clean help

help:
	@echo "make -C scripts <target>"
	@echo "  validate  check every authored input, generate nothing"
	@echo "  data      regenerate _data/cv/*.yml"
	@echo "  cv        build all four CV profiles and publish the short PDFs"
	@echo "  all       validate + data + cv"
	@echo "  site      all + jekyll build"
	@echo "  verify    site + post-build assertions"
	@echo "  check     report drift without writing (CI / pre-commit)"

validate:
	cd $(ROOT) && $(PY) scripts/validate_cv_data.py

data:
	cd $(ROOT) && $(PY) scripts/build_site_data.py

cv:
	cd $(ROOT) && $(PY) scripts/build_cv.py --profile all --publish

all:
	cd $(ROOT) && $(PY) scripts/build_all.py

site:
	cd $(ROOT) && $(PY) scripts/build_all.py --jekyll

verify:
	cd $(ROOT) && $(PY) scripts/build_all.py --verify

check:
	cd $(ROOT) && $(PY) scripts/build_site_data.py --check

test:
	cd $(ROOT) && $(PY) -m unittest discover -s tests -v

clean:
	rm -rf $(ROOT)/build
