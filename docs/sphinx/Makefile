# Minimal makefile for Sphinx documentation with uv.

SPHINXBUILD ?= uv run sphinx-build
SOURCEDIR = .
BUILDDIR = build
SPHINXOPTS ?= -W --keep-going

.PHONY: html clean linkcheck

html:
	$(SPHINXBUILD) -M html $(SOURCEDIR) $(BUILDDIR) $(SPHINXOPTS)

clean:
	rm -rf $(BUILDDIR)

linkcheck:
	$(SPHINXBUILD) -M linkcheck $(SOURCEDIR) $(BUILDDIR) $(SPHINXOPTS)
