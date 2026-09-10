"""Sphinx configuration for the Amphimixis documentation."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
_pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
version = _pyproject["project"]["version"]
release = version

project = "Amphimixis"
author = "Amphimixis contributors"
copyright = "2026, Amphimixis contributors"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_sitemap",
    "sphinx_design",
    "sphinx_copybutton",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
    ".yml": "markdown",
}

root_doc = "index"

nitpicky = True
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}
add_module_names = False
autodoc_typehints = "both"
autodoc_preserve_defaults = True
python_use_unqualified_type_names = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3.12", None),
}

myst_enable_extensions = [
    "colon_fence",
]
myst_heading_anchors = 4

templates_path = ["_templates"]
html_theme = "furo"
html_theme_options = {
    "source_repository": "https://github.com/Amphimixis/amphimixis",
    "source_branch": "main",
    "source_directory": "docs/sphinx",
    "sidebar_hide_name": True,
    "light_logo": "logo-light.png",
    "dark_logo": "logo-dark.png",
}

html_title = "Amphimixis"
html_short_title = "Amphimixis"
html_baseurl = "https://amphimixis.org/"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
