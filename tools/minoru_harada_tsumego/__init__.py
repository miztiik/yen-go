"""Harada tsumego archive crawler and cataloger.

Crawls the Wayback Machine archive of 'Tsumego - Life and Death
Problems of Go by Minoru Harada' (1996-2020, ~1183 weekly problems).

Each weekly problem has two difficulty levels (Elementary + Intermediate)
with problem images, correct answer images, and wrong answer images.
All content is GIF images — no SGF exists at source.

Usage:
    python -m tools.minoru_harada_tsumego discover     # Build catalog from index
    python -m tools.minoru_harada_tsumego download      # Download images from catalog
    python -m tools.minoru_harada_tsumego status         # Show progress
"""
