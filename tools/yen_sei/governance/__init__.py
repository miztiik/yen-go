"""Governance module: config-driven curation rules for yen-sei training data.

Three components:
- ``config_loader``: Load and validate ``curation_config.json``.
- ``teaching_signal``: Extract per-puzzle signals from raw SGF text.
- ``tier_classifier``: Apply config rules to assign Gold/Silver/Bronze/Drop.
"""
