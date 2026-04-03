"""Enrichment pipeline stages — Stage Runner pattern.

Each stage implements the EnrichmentStage protocol and is auto-wrapped
by StageRunner for notify/timing/error handling.
"""
