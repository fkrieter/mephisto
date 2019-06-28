#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import os
import sys

if sys.version_info < (3, 3):
    from mock import Mock as MagicMock
else:
    from unittest.mock import MagicMock


class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()

    # Placeholder class
    class PH:
        pass


# https://stackoverflow.com/a/22023805/10986034
os.environ["SPHINX_BUILD"] = "1"

sys.path.insert(0, os.path.abspath("../../mephisto/"))

MOCK_MODULES = ["ROOT"]
MOCK_CLASSES = ["TH1D", "TH2D", "TPad", "TCanvas", "TLatex", "TLegend"]
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

for cls in MOCK_CLASSES:
    setattr(sys.modules["ROOT"], cls, Mock.PH)

autodoc_mock_imports = ["numpy", "root_numpy", "scipy"]

# -- Project information -----------------------------------------------------

project = u"Mephisto"
copyright = u"2019"
author = u"fkrieter"

version = u""
release = u""

# -- General configuration ---------------------------------------------------

extensions = ["sphinx.ext.autodoc", "sphinx.ext.viewcode", "sphinx.ext.autosummary"]

autodoc_default_flags = ["members"]
autodoc_member_order = "bysource"
autosummary_generate = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# The language for content autogenerated by Sphinx.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "monokai"


# -- Options for HTML output -------------------------------------------------

import sphinx_theme

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_theme.get_html_theme_path()]

# Theme options are theme-specific and customize the look and feel of a theme further.
html_theme_options = {
    "style_nav_header_background": "#333333",
    "collapse_navigation": False,
}
html_logo = "mephisto-logo.png"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory.
# html_static_path = ["_static"]

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
# html_sidebars = {}

# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = "{}_help".format(project)


# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',
    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',
    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files.
latex_documents = [
    (
        master_doc,
        "{}.tex".format(project),
        u"{} Documentation".format(project),
        author,
        "manual",
    )
]

# -- Options for manual page output ------------------------------------------

# One entry per manual page.
man_pages = [(master_doc, project, u"{} Documentation".format(project), [author], 1)]


# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files.
texinfo_documents = [
    (
        master_doc,
        project,
        u"{} Documentation".format(project),
        author,
        project,
        "One line description of project.",
        "Miscellaneous",
    )
]
