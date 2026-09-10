Home Page
==========

   Amphimixis is an automated project intelligence and evaluation tool for
   performance and migration readiness. It helps inspect a project for existing
   infrastructure such as CI, tests, benchmarks, dependencies, and build scripts,
   then runs builds and collects performance data for further comparison.

   Amphimixis uses ``perf`` for profiling and produces a cross-table with two
   builds per CPU event for comparison.

Features
--------

.. grid:: 1 1 4 4

   .. grid-item-card:: Analysis
      :text-align: center

      Inspect CI, tests, benchmarks, build config and dependencies.

   .. grid-item-card:: Building
      :text-align: center

      Build with configured recipes and platforms.

   .. grid-item-card:: Profiling
      :text-align: center

      Run executables and collect timing and ``perf`` statistics.

   .. grid-item-card:: Comparison
      :text-align: center

      Produce a cross-table per CPU event.

Requirements
------------

See :doc:`usage_guide` for the full list of required tools and system dependencies.

Quick Start
-----------

.. include:: ../usage_guide.md
   :parser: myst_parser.sphinx_
   :start-after: ## Quick Start
   :end-before: ## Choose an installation method

.. toctree::
   :maxdepth: 2
   :caption: Getting Started
   :hidden:

   usage_guide
   config_instruction
   input

.. toctree::
   :maxdepth: 2
   :caption: For Users
   :hidden:

   usage_examples
   migration_readiness_methodology

.. toctree::
   :maxdepth: 2
   :caption: Support
   :hidden:

   troubleshooting

.. toctree::
   :maxdepth: 1
   :caption: Technical
   :hidden:

   api/index
