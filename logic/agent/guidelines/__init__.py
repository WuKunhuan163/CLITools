"""Layered agent guidelines — composable conventions and ecosystem knowledge.

Two categories:
  (1) conventions — development norms (experience, brain, search, fix, infrastructure)
  (2) ecosystem — structural knowledge (architecture, tools, commands, symmetric patterns)

Layers extend both categories incrementally. TOOL provides the base;
OPENCLAW (and others) add on top without replacing.

Usage:
    from logic.agent.guidelines import compose_guidelines

    # TOOL-level only
    guidelines = compose_guidelines()

    # With OPENCLAW layer
    guidelines = compose_guidelines(layers=["openclaw"])
"""
from logic.agent.guidelines.engine import compose_guidelines  # noqa: F401
