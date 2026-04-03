#!/usr/bin/env python3
"""Consolidate 738 Go puzzle collections into ~150 canonical collections.

Reads config/collections.json, applies slug-mapping rules, merges aliases,
and writes the consolidated result back.

Usage:
    python tools/consolidate_collections.py [--dry-run]
"""

import json
import sys
from pathlib import Path

from tools.core.atomic_write import atomic_write_json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
COLLECTIONS_PATH = ROOT / "config" / "collections.json"

# ── Slug Mapping ──────────────────────────────────────────────────────────
# Maps every existing slug → canonical slug.
# If a slug maps to itself, it stays as a canonical collection.
# If it maps to another slug, it's absorbed (name+aliases merge into target).

SLUG_MAP: dict[str, str] = {}

# ── I. TECHNIQUE COLLECTIONS ─────────────────────────────────────────────

# 1. life-and-death
for s in [
    "essential-life-and-death", "life-and-death", "life-and-death-problems",
    "life-and-death-puzzles", "life-and-death-questions", "l-d-problems",
    "the-life-and-death-collection", "life", "eyes-life-and-death",
    "life-and-death-interesting-problems", "life-death-auto-response",
    "capture-life-death-easy", "elementary-life-death-spanish",
    "life-death-problems-french", "life-and-death-quiz-4",
    "a-live-and-death-problem-2021vsgo", "life-death-capture-problems",
    "death", "to-live", "absolute-basics-i-life-death-and-capturing",
    "pim-class-t-boss-life-death-easy-life", "critical-moment-of-life-and-death-1",
    "life-death-for-beginners", "introduction-of-life-and-death",
    "life-and-death-status-big-eye",
]:
    SLUG_MAP[s] = "life-and-death"

# 2. corner-life-and-death
for s in ["corner-life-and-death", "corner-life-death-german"]:
    SLUG_MAP[s] = "corner-life-and-death"

# 3. life-and-death-second-line
SLUG_MAP["life-and-death-on-the-second-line"] = "life-and-death-second-line"

# 4. tesuji-training
for s in [
    "tesuji-training", "tesuji", "tesuji-problems", "tesuji-spree",
    "basic-tesuji-1", "basic-tesuji-2", "basic-techniques-of-go-tesuji-examples",
    "tesuji-strength", "tesuji-for-beginners", "tesuji-for-pre-intermediate",
    "tactics-tutor", "tesuji-for-alive", "tesuji-capturing",
    "tesuji-problems-collection-intermediate-advanced",
    "crush-oshi-tsubushi-14-kyu-10-kyu", "haengma-and-tesuji",
    "super-tesuji-exchanges", "ertai-tesuji-level-5", "crane-nest-tesuji",
    "original-tesuji-problem-by-takumi-go", "tesuji-dictionary",
]:
    SLUG_MAP[s] = "tesuji-training"

# 5. ladder-problems
for s in [
    "ladder-problems", "ladder-review", "ladder", "ladder-after-atari",
    "loose-ladder", "kageyama-ladder-drills",
    "ladders-dutch-go-magazine-1-25", "ladders-dutch-go-magazine-26-50",
    "ladders-dutch-go-magazine-51-75", "ladders-dutch-go-magazine-76-100",
    "ladders-dutch-go-magazine-126-145",
]:
    SLUG_MAP[s] = "ladder-problems"

# 6. net-problems
for s in [
    "net-problems", "geta-technique", "net-for-beginner", "net-after-atari",
    "net-hard", "net-technique-drills", "geta-capture-drills",
]:
    SLUG_MAP[s] = "net-problems"

# 7. ko-problems
for s in ["ko-problems", "ko-rule", "double-ko", "ko-2"]:
    SLUG_MAP[s] = "ko-problems"

# 8. snapback-problems
for s in [
    "snapback-problems", "snapback", "snap-back-to-kill", "snapback-for-twice",
    "snapback-technique", "snapback-drills", "snapback-after-atari",
    "snapback-and-throw-in-for-beginner", "snapback-and-throw-in-for-elementary",
]:
    SLUG_MAP[s] = "snapback-problems"

# 9. nakade-problems
for s in [
    "nakade-problems", "beginner-guide-to-nakade", "basic-nakade-and-eyespace-defects",
]:
    SLUG_MAP[s] = "nakade-problems"

# 10. capturing-race
for s in [
    "capturing-race", "capturing-races", "capturing-race3", "capturing-race4",
    "capturing-race5", "capturing-race6", "capture-race-drills",
    "capture-race-elementary-2", "tesuji-semeai", "semeai-drills",
]:
    SLUG_MAP[s] = "capturing-race"

# 11. capture-problems (NEW)
for s in [
    "capture-problems", "capture-concept", "basic-captures", "capturing",
    "capture-101-weiqi", "capture-skills-for-beginner",
    "capture-by-shunt-bao-chi-15-10k", "capture-by-divide",
    "krun-capturing-basics", "krun-capturing", "tsumego-hero-easy-capture",
    "easy-capture-for-beginner", "pim-capture", "pim-how-to-capture",
    "capture-spanish", "capture-drills-vn", "train-your-capture-skills",
    "capturing-tactics", "capturing-fundamentals", "beginner-guide-to-capturing",
    "advanced-capturing", "capture-towards-the-first-line",
    "capture-towards-own-stone", "capture-direction-drills",
    "capture-opportunity-on-7", "problem-tsumegohero-easy-capture",
    "eat-time", "eat-me-if-you-can", "capture-exercises-1",
    "captures-and-eyes-revision", "capture-two-recapture-one-to-live",
    "easy-capture-difficulty-11k",
]:
    SLUG_MAP[s] = "capture-problems"

# 12. eye-shape-mastery
for s in [
    "eye-shape-mastery", "living-eye-shapes", "dead-eye-shapes",
    "killable-eye-shapes", "makes-eyes", "false-eyes", "two-eyes-to-live",
    "basic-living-and-dead-eye-shapes", "eye-shape-fundamentals",
    "killable-eye-shapes-collection", "destroy-an-eye", "closes-the-door",
]:
    SLUG_MAP[s] = "eye-shape-mastery"

# 13. sacrifice-techniques
SLUG_MAP["sacrifice-techniques"] = "sacrifice-techniques"
SLUG_MAP["sacrifise-puzzle"] = "sacrifice-techniques"

# 14. seki-problems
for s in [
    "seki-problems", "seki-with-one-eye-each", "seki-without-any-eyes", "seki-drills",
]:
    SLUG_MAP[s] = "seki-problems"

# 15. liberty-shortage
for s in [
    "liberty-shortage", "liberties-problems", "reducing-liberties-2", "pim-liberty",
]:
    SLUG_MAP[s] = "liberty-shortage"

# 16. endgame-problems
for s in [
    "endgame-problems", "endgame-essentials", "precise-endgame",
    "fourth-line-endgame", "learning-endgame",
    "endgame-problem-on-5-5-board-by-fukui-masaaki",
]:
    SLUG_MAP[s] = "endgame-problems"

# 17. shape-problems
for s in [
    "shape-problems", "shape", "shapes", "shape-play",
    "basic-shape-recognition", "basic-shape-recognition-2", "beginning-shapes",
    "basic-shapes-for-15-20-kyu", "shape-up-problem-sets", "make-shape",
    "common-shapes-you-should-know", "shape-correction-drills",
    "beautiful-shapes", "basic-shapes", "number-shape-1-5", "number-shape-6-10",
    "opening-shapes", "250317-life-death-shapes",
    "alex-basic-shapes-and-motion-collection",
]:
    SLUG_MAP[s] = "shape-problems"

# 18. connection-problems
for s in [
    "connection-problems", "connection", "connecting-the-edge",
    "connection-drills", "connecting-stones", "pim-class-t-boss-4-basic-connections",
    "connect-and-cut-1",
]:
    SLUG_MAP[s] = "connection-problems"

# 19. cutting-problems
for s in ["cutting-problems", "cutting"]:
    SLUG_MAP[s] = "cutting-problems"

# 20. kill-problems
for s in [
    "kill-problems", "to-kill", "tesuji-for-kill",
    "pim-class-t-boss-life-death-easy-kill", "killing-exercise-1",
]:
    SLUG_MAP[s] = "kill-problems"

# 21. living-problems
SLUG_MAP["living-problems"] = "living-problems"

# 22. escape-problems
for s in [
    "escape-problems", "escape-after-atari", "escape-piece2024",
    "pim-find-the-way-to-escape",
]:
    SLUG_MAP[s] = "escape-problems"

# 23. under-the-stones
SLUG_MAP["under-the-stones"] = "under-the-stones"

# 24. vital-point
for s in ["vital-point", "urgent-point-and-big-point"]:
    SLUG_MAP[s] = "vital-point"

# 25. connect-underneath
SLUG_MAP["connect-underneath"] = "connect-underneath"

# 26. opening-problems (NEW)
for s in [
    "opening-problems", "opening", "training-for-openings",
    "extend-on-the-side", "approach-the-corner",
    "opening-size-9x9-good-and-bad-moves", "control-the-corner",
    "double-extension", "contact-play", "cooperation-of-third-and-forth-line",
    "limiting-the-influence", "corner-encloser",
]:
    SLUG_MAP[s] = "opening-problems"

# 27. double-atari-problems (NEW)
for s in [
    "double-atari-problems", "double-atari", "mutual-atari", "atari", "pim-atari",
    "continuous-atari",
]:
    SLUG_MAP[s] = "double-atari-problems"

# throw-in -> technique
SLUG_MAP["throw-in"] = "tesuji-training"

# ── II. AUTHOR COLLECTIONS ───────────────────────────────────────────────

# Cho Chikun (3 canonical volumes)
for s in [
    "cho-chikun-life-death-elementary",
    "cho-chikun-elementary-problems-from-200",
    "cho-chikun-an-encyclopedia-of-life-death-for-beginners",
    "cho-chikun-s-encyclopedia-of-life-and-death-part-1-elementary-pr",
    "cho-chikun-problems-spanish", "cho-chikun-life-and-death",
]:
    SLUG_MAP[s] = "cho-chikun-life-death-elementary"

for s in [
    "cho-chikun-life-death-intermediate", "ralph-cho-chikun-tsumegos-intermediate",
]:
    SLUG_MAP[s] = "cho-chikun-life-death-intermediate"

for s in [
    "cho-chikun-life-death-advanced",
    "chikun-all-about-life-and-death-volume-2-a-basic-dictionary-of-l",
]:
    SLUG_MAP[s] = "cho-chikun-life-death-advanced"

# Cho Nam Chul (different Korean pro)
SLUG_MAP["cho-nam-chul"] = "cho-nam-chul"

# Maeda (keep all 5 distinct)
for s in [
    "maeda-god-of-tsumego", "maeda-newly-selected-100", "maeda-tsumego-masterpieces",
    "maeda-beginners-tsumego-isbn-4-488-00004-5",
    "maeda-intermediate-tsumego-isbn-4-488-00005-3",
]:
    SLUG_MAP[s] = s  # identity

# James Davies (3 canonical)
for s in [
    "james-davies-tesuji", "tesuji-elementary-go-series-v-james-davies",
    "james-davies-tesuji-egs-vol-3", "james-davies-tesuji-tutorial",
]:
    SLUG_MAP[s] = "james-davies-tesuji"

SLUG_MAP["james-davies-life-death"] = "james-davies-life-death"

for s in [
    "james-davies-endgame",
    "the-endgame-elementary-go-series-tomoko-ogawa-and-james-davies",
    "ogawa-davies-the-endgame-egs-5",
]:
    SLUG_MAP[s] = "james-davies-endgame"

# Lee Changho
for s in ["lee-changho-tesuji", "lee-chang-ho-tesuji-encyclopedia-i"]:
    SLUG_MAP[s] = "lee-changho-tesuji"

# Bozulich
SLUG_MAP["bozulich-get-strong-at-life-and-death"] = "bozulich-life-and-death"
SLUG_MAP["bozulich-get-strong-at-the-endgame"] = "bozulich-endgame"
SLUG_MAP["bozulich-fuseki-problems"] = "bozulich-fuseki"

# Honinbo Shusai (merge 3 volumes)
for s in [
    "honinbo-shusai-curious-mechanics-of-life-death-igo-kenkyukai-1-1",
    "honinbo-shusai-curious-mechanics-of-life-death-igo-kenkyukai-2-1",
    "honinbo-shusai-curious-mechanics-of-life-death-igo-kenkyukai-3-1",
]:
    SLUG_MAP[s] = "honinbo-shusai-life-death"

# Yang Yilun
SLUG_MAP["yang-yilun-ingenious-life-death-puzzles-vol-1-2"] = "yang-yilun-life-death"

# Wang Zhipeng
SLUG_MAP["life-and-death-1000-problems-by-wang-zhipeng"] = "wang-zhipeng-life-death"

# Noguchi
SLUG_MAP["noguchi-90-fundamental-tsumego"] = "noguchi-fundamental-tsumego"

# Wang Zhi et al.
SLUG_MAP["wang-zhi-et-al-1000-tsumegos"] = "wang-zhi-tsumegos"

# Hyacinth
SLUG_MAP["100-of-hyacinth-life-death-problems"] = "hyacinth-life-death"
for s in [
    "hyacinth-lecture-problems-debt-collecting-1",
]:
    SLUG_MAP[s] = "hyacinth-life-death"

# Hashimoto (all 7 keep as-is)
for s in [
    "hashimoto-1-year-tsumego", "hashimoto-famous-creations-300",
    "hashimoto-moments-of-wind", "hashimoto-attack-and-protect",
    "hashimoto-53-stations", "hashimoto-enjoy-tsumego",
    "hashimoto-tsumego-millions",
]:
    SLUG_MAP[s] = s

# Fujisawa (3 keep + 1 new)
for s in [
    "fujisawa-tsumego-masterpiece", "fujisawa-tsumego-graded",
    "fujisawa-classroom",
]:
    SLUG_MAP[s] = s
SLUG_MAP["fujisawa-fuseki-exercises"] = "fujisawa-fuseki"

# Go Seigen
for s in ["go-seigen-tsumego-dojo", "go-seigen-evil-moves"]:
    SLUG_MAP[s] = s

# Ishida, Ishigure, Yamada, Kobayashi
SLUG_MAP["ishida-tsumego-masterpieces"] = "ishida-tsumego-masterpieces"
SLUG_MAP["ishigure-basic-tsumego"] = "ishigure-basic-tsumego"
SLUG_MAP["yamada-tsumego-collection"] = "yamada-tsumego-collection"
SLUG_MAP["kobayashi-basic-tesuji"] = "kobayashi-basic-tesuji"
SLUG_MAP["segoe-tesuji-dictionary"] = "segoe-tesuji-dictionary"

# Other individual author collections
SLUG_MAP["tetsuo-tsumego"] = "tetsuo-tsumego"
SLUG_MAP["jennica-tsumego"] = "jennica-tsumego"
SLUG_MAP["in-seong-hwang-8d-problems"] = "in-seong-hwang-problems"
SLUG_MAP["qi-tsumego"] = "qi-tsumego"
SLUG_MAP["kubomatsu-pamphlet"] = "kubomatsu-pamphlet"
SLUG_MAP["sadaharu-collection"] = "sadaharu-collection"
SLUG_MAP["fuiter-go-problems"] = "fuiter-problems"
SLUG_MAP["fran-library"] = "fran-go-library"
SLUG_MAP["fran-playground"] = "fran-go-library"
SLUG_MAP["golden-opportunities"] = "rin-kaiho-golden-opportunities"
SLUG_MAP["play-like-god-of-go-4"] = "general-practice"

# Nyudan (author book)
SLUG_MAP["nyudan-strongly-made-compulsory-tesuji-250-isbn-4818202770"] = "nyudan-tesuji-250"

# ── III. CLASSICAL COLLECTIONS ────────────────────────────────────────────

for s in [
    "gokyo-shumyo", "igo-hatsuyoron", "xuanxuan-qijing", "genran", "gokyo-seimyo",
]:
    SLUG_MAP[s] = s

SLUG_MAP["guanzi-pu"] = "guanzi-pu"
SLUG_MAP["guan-zi-pu-collection-volume-i"] = "guanzi-pu"

SLUG_MAP["shikatsu-myoki-life-and-death-brilliant-stratagems"] = "shikatsu-myoki"
SLUG_MAP["qi-jing-zhong-miao-easy-probems"] = "qi-jing-zhong-miao"
SLUG_MAP["the-book-of-pure-pleasures-and-forgotten-worries"] = "book-of-pure-pleasures"
SLUG_MAP["ancient-questions"] = "ancient-questions"

# ── IV. GRADED ESSENTIALS ─────────────────────────────────────────────────

for level in [
    "novice", "beginner", "elementary", "intermediate",
    "upper-intermediate", "advanced", "low-dan", "high-dan", "expert",
]:
    SLUG_MAP[f"{level}-essentials"] = f"{level}-essentials"

# Absorb generic beginner/basics into novice-essentials
for s in [
    "for-beginners", "go-basics", "go-basics-2", "how-to-play-go",
    "learn-to-play-go", "lets-go", "new-player-corse", "basic-rules-aago",
    "interactive-go-intro", "basics-tutorial", "joshua-basics-tutorial",
    "go-basics-french", "go-tutorial-french", "tutorial-collection-spanish",
    "introduction-to-go-serbian", "basic-terms-for-beginners",
    "a-beginner-guide-to-go", "beginner-guide", "amigo-no-igo-a-for-beginners",
    "joshua-tutorial-on-how-to-play-go", "learn-to-play-go-easy",
    "introduction-to-go-for-new-players-and-beginners",
    "basic-instinct-practice", "go-guide", "go-course", "basic-exercises",
    "basic-course-level-1", "fundamentals",
]:
    SLUG_MAP[s] = "novice-essentials"

# Absorb generic beginner collections into beginner-essentials
for s in [
    "beginner1", "beginner2", "1beginner-1", "beginner-course",
    "clossius-beginner-go-puzzles", "exercises-for-beginners",
    "beginner-go-concepts", "beginner-stuff", "beginner-quick-learn",
    "beginner-go-tutorial-volume-1", "beginner-brain-teasers-30kyu",
    "go-problems-for-beginners-30-25kyu",
    "the-best-collection-for-beginners-vol-1-30-20k", "week-1-beginner",
    "beginner-problems-french", "beginners-spanish",
    "a-few-beginner-examples-for-a-friend", "beginner-questions",
    "board-19-19-for-beginners", "the-wisdom-of-go-beginners",
    "beginners-question-collection", "puzzle-for-beginners",
    "intermidiate-puzzles-for-beginners-1", "20-25-kyu-problems-beginner-pack",
    "stone-development-for-beginners",
]:
    SLUG_MAP[s] = "beginner-essentials"

# Absorb elementary level
for s in [
    "elementary-problems", "graded-elementary-puzzles-for-kyu-players",
    "introduction-to-puzzles",
]:
    SLUG_MAP[s] = "elementary-essentials"

# Graded kyu-range collections → appropriate essentials
for s in [
    "puzzles-20-16kyu-vol2", "puzzles-20-15kyu-vol3", "20-15k",
]:
    SLUG_MAP[s] = "elementary-essentials"

SLUG_MAP["life-and-death-problems-collection-intermediate-advanced"] = "intermediate-essentials"
SLUG_MAP["life-death-training-10k-5k"] = "upper-intermediate-essentials"
SLUG_MAP["graded-go-problems-for-dan-players-life-death"] = "advanced-essentials"

# ── V. SCHOOL/CURRICULUM SERIES ───────────────────────────────────────────

# Rennes Go School
for s in [
    "rennes-go-school-30kyu", "rennes-go-school-25kyu", "rennes-go-school-20kyu",
    "rennes-go-school-15kyu", "rennes-go-school-10kyu",
    "rennes-go-school-life-death", "rennes-go-school-joseki-20kyu",
    "rennes-go-school-joseki-25kyu", "rennes-go-school-shapes",
]:
    SLUG_MAP[s] = "rennes-go-school"

# OGS Learn to Play
for s in [
    "o-g-s-learn-to-play-go-part-4-1-4-13", "o-g-s-learn-to-play-go-part-4-14-4-37",
    "o-g-s-learn-to-play-go-part-5-1-5-12", "o-g-s-learn-to-play-go-part-5-17-5-34",
    "o-g-s-learn-to-play-go-part-5-35-5-49", "o-g-s-learn-to-play-go-part-6-1-6-21",
    "o-g-s-learn-to-play-go-part-6-23-6-47", "o-g-s-learn-to-play-go-part-6-48-6-63",
    "o-g-s-learn-to-play-go-part-6-64-6-74", "o-g-s-learn-to-play-go-part-7-1-7-19",
    "o-g-s-learn-to-play-go-part-7-20-7-34",
]:
    SLUG_MAP[s] = "ogs-learn-to-play"

# Life & Death Training Series
for s in [
    "life-and-death-training-1", "life-and-death-training-2",
    "life-and-death-training-3", "life-and-death-training-5",
    "life-and-death-training-7", "life-and-death-training-8",
    "life-and-death-training-9", "life-and-death-training-10",
    "life-and-death-training-11", "life-and-death-training-12",
]:
    SLUG_MAP[s] = "life-death-training-series"

# PIM Go School
for s in [
    "pim-class-t-boss-tesuji-snapback-3-steps",
    "pim-class-t-boss-tesuji-net-ladder-midterm-retake-exam-m1",
    "pim-basic-tesuji-leader-net-snapback-and-apply-3-tactics",
    "pim-special-class-t-boss-apply-tesuji-rada-collection",
]:
    SLUG_MAP[s] = "pim-go-school"

# Introduction to Weiqi (Di Yansheng & Xu Ying)
for s in [
    "introduction-to-weiqi-by-di-yansheng-and-xu-ying-chapter-2-captu",
    "introduction-to-weiqi-by-di-yansheng-and-xu-ying-chapter-3-life",
    "introduction-to-weiqi-by-di-yansheng-and-xu-ying-chapter-4-gener",
    "introduction-to-weiqi-by-di-yansheng-and-xu-ying-chapter-5-basic",
    "introduction-to-weiqi-by-di-yansheng-and-xu-ying-chapter-7-basic",
    "introduction-to-weiqi-by-di-yansheng-and-xu-ying-chapter-8-conne",
    "introduction-to-weiqi-by-di-yansheng-and-xu-ying-chapter-11-shap",
]:
    SLUG_MAP[s] = "introduction-to-weiqi"

# Krun Go School
for s in [
    "basic-by-krun", "endgame1-by-krun", "endgame2-by-krun", "endgame3-by-krun",
]:
    SLUG_MAP[s] = "krun-go-school"

# 101Weiqi (collections not already absorbed into technique)
# Most 101Weiqi technique collections are already absorbed above
# This catches remainders
SLUG_MAP["101weiqi-drills"] = "101weiqi-drills"

# ── VI. QUIZ/DRILL SERIES ─────────────────────────────────────────────────

for s in [
    "quiz3", "quiz-1", "quiz-2", "quiz4", "quiz5", "quiz7", "quiz11",
    "quiz13", "quiz14", "quiz-15", "quiz16", "quiz17", "quiz18", "quiz20",
]:
    SLUG_MAP[s] = "1200igo-quizzes"

for s in [
    "30k-gohouse001", "30k-gohouse002", "30k-gohouse003",
    "30k-gohouse004", "30k-gohouse005", "30k-gohouse019",
]:
    SLUG_MAP[s] = "gohouse-30k"

for s in ["level-up-1", "level-up-2", "level-up-10"]:
    SLUG_MAP[s] = "level-up-series"

for s in [
    "taruc-practice-1", "taruc-practice-2", "taruc-practice-3",
    "taruc-practice-4", "taruc-practice-6", "taruc-practice-7",
]:
    SLUG_MAP[s] = "taruc-practice"

# ── VII. PUBLICATION SERIES ───────────────────────────────────────────────

for s in [
    "dutch-go-magazine-1979-80-17", "dutch-go-magazine-1982-83-20",
    "dutch-go-magazine-1984-21", "dutch-go-magazine-1987-24",
    "dutch-go-magazine-1989-26",
    "dutch-go-magazine-2014-16-bul-2-28-atorrante",
    "dutch-go-magazine-2020-22-bul-59-88-atorrante",
]:
    SLUG_MAP[s] = "dutch-go-magazine"

for s in [
    "british-go-journal-1967-1980-atorrante",
    "british-go-journal-2011-2020-atorrante",
]:
    SLUG_MAP[s] = "british-go-journal"

SLUG_MAP["aga-problems-of-the-week"] = "aga-problems"

# ── VIII. JOSEKI ──────────────────────────────────────────────────────────

for s in [
    "38-basic-joseki", "essential-joseki", "joseki-every-ddk-should-know",
    "joseki-1-25-invasion", "joseki-tutor-for-beginners",
    "joseki-for-beginners-12-1-ddk-to-sdk-each-in-4-parts-learn-black",
    "common-josekis-for-beginners", "joseki-101-for-pl-go-club",
    "somejoseki", "joseki-1-1", "joseki-problems-iscimenozgur",
    "small-joseki-collection", "ai-revolutionary-ai-jouseki",
    "joseki-and-joseki", "szpur-joseki-and-other-variations",
    "alphago-zero-joseki", "mistakes-in-joseki-1-15-kyu",
]:
    SLUG_MAP[s] = "joseki-problems"

for s in [
    "joseki-almost-antique-corner-sequences-0001-1000",
    "joseki-almost-antique-corner-sequences-1001-2000",
    "joseki-almost-antique-corner-sequences-2001-3000",
    "joseki-almost-antique-corner-sequences-3001-4000",
    "joseki-almost-antique-corner-sequences-4001-5000",
    "joseki-almost-antique-corner-sequences-5001-6000",
]:
    SLUG_MAP[s] = "joseki-antique-corner"

# ── IX. GO FORMATIONS (keep distinct) ────────────────────────────────────

SLUG_MAP["bamboo-joint"] = "bamboo-joint"
SLUG_MAP["door-group"] = "door-group"
SLUG_MAP["bridge-group"] = "bridge-group"
SLUG_MAP["tripod-group"] = "tripod-group"
SLUG_MAP["leaf-group"] = "leaf-group"
SLUG_MAP["comb-formation"] = "comb-formation"
SLUG_MAP["key-formation"] = "key-formation"
SLUG_MAP["carpenter-square"] = "carpenter-square"
SLUG_MAP["golden-chicken-standing-on-one-leg-easy"] = "golden-chicken"
SLUG_MAP["the-l-shape"] = "l-shape"
SLUG_MAP["elephant-eye"] = "elephant-eye"
SLUG_MAP["two-space-base"] = "two-space-base"
SLUG_MAP["miai"] = "miai"

# ── X. STRATEGY / GAME-PHASE ─────────────────────────────────────────────

for s in [
    "territory-and-area-scoring-1", "territory-and-area-scoring-2",
    "determine-who-wins-2", "enlarging-one-own-territory",
    "reducing-opponent-territory",
]:
    SLUG_MAP[s] = "territory-scoring"

for s in [
    "big-points-that-affect-fightings", "big-points-for-both-sides",
]:
    SLUG_MAP[s] = "influence-strategy"

for s in [
    "techniques-of-whole-board-thinking", "proper-and-common-moves",
    "thrid-line-and-fourth-line",
]:
    SLUG_MAP[s] = "whole-board-thinking"

for s in [
    "correcting-my-breakpoints-size-9x9", "9x9collection",
    "moving-to-a-bigger-board-13x13-19x19-strategies", "9x9-opening",
]:
    SLUG_MAP[s] = "9x9-problems"

# ── XI. REGIONAL / CLUB ──────────────────────────────────────────────────

for s in [
    "homework-session-1-extra", "homework-session-2", "homework-session-3",
    "van-vuong-introduction", "hue-university-go-basics-1",
]:
    SLUG_MAP[s] = "vietnam-go-school"

SLUG_MAP["cambridge-practice-puzzles"] = "cambridge-go-club"
SLUG_MAP["turkey-library"] = "turkey-go-library"
SLUG_MAP["gostar-homeworks"] = "gostar-school"
SLUG_MAP["go-star"] = "gostar-school"
SLUG_MAP["lu-practice-problems"] = "lu-school"
SLUG_MAP["jim-class"] = "jim-class"
SLUG_MAP["falling-in-love-with-baduk-dahye-lee-jihee-baek"] = "falling-in-love-with-baduk"

# ── XII. BOOK-SPECIFIC ───────────────────────────────────────────────────

for s in [
    "graded-go-problems-for-beginners-volume-1", "graded-problems-beginners-1",
]:
    SLUG_MAP[s] = "graded-go-problems-beginners-1"

SLUG_MAP["a-basic-dictionary-of-life-and-death-volume-one"] = "basic-dictionary-life-death-1"
SLUG_MAP["encyclopedia-of-life-and-death-part-second"] = "encyclopedia-life-death-2"
SLUG_MAP["river-mountain-go-volume-1-oliver-richman"] = "river-mountain-go-1"
SLUG_MAP["the-internet-tumego-book"] = "internet-tsumego-book"
SLUG_MAP["the-art-of-go-series-i"] = "art-of-go-1"
SLUG_MAP["the-fundamentals-1"] = "the-fundamentals-1"
SLUG_MAP["golden-collection"] = "golden-collection"
SLUG_MAP["monday-tsumego"] = "monday-tsumego"
SLUG_MAP["two-choice-tsumego-9-19-kyu"] = "two-choice-tsumego"
SLUG_MAP["easy-serie"] = "gogameguru-easy"
SLUG_MAP["go-world-problems-incomplete-1999"] = "go-world-problems"
SLUG_MAP["basic-course-level-1"] = "novice-essentials"  # Go Squared

# Specific books with identifiable authors
SLUG_MAP["basic-tactical-fights-from-kano-books-1-and-2"] = "kano-tactical-fights"
SLUG_MAP["fundamentals-fighting-introduction"] = "general-practice"

# ── XIII. SYSTEM ──────────────────────────────────────────────────────────

SLUG_MAP["daily-warmup"] = "daily-warmup"
SLUG_MAP["weekly-challenge"] = "weekly-challenge"

# ── XIV. GENERAL PRACTICE (catch-all) ─────────────────────────────────────

for s in [
    "challenging-puzzles", "pregame-prep", "challenge", "random-exercises",
    "go-exercise", "cool-puzzle", "difficultish-puzzles", "my-easy-puzzles",
    "go-puzzles", "good-game", "motive", "magic", "problem-depository",
    "practical-tsumegos", "easy-tsumego", "reading-exercises",
    "assessment-problems", "review-problems", "easy-16", "homework",
    "30k-to-9d", "30-25k-trail", "tonmai-easy", "junior-go-0-2",
    "milk-go", "easy-haengma", "sophisticated-variations",
    "intermediate-lectures", "volume-2", "volume-2-part-1",
    "the-raccoon-dog-drums-his-belly", "monkey-climbing-the-mountain",
    "the-many-ways-to-go", "goodaa-for-the-good-people",
    "one-point-jump-to-the-center", "gt-go-w10", "ggs-2", "edges",
    "probes", "key-stones", "underneath-attachment",
    "alex-introduction-to-bad-results", "go-problems-french",
    "basic-shape-recognition", "japanese-tsumego",
    "ybc-big-or-urgent-mid-game-and-opening",
    "dgm-fuseki-puzzles-more",
]:
    SLUG_MAP[s] = "general-practice"

# Misc remaining
SLUG_MAP["basic-shape-recognition"] = "shape-problems"  # override
SLUG_MAP["japanese-tsumego"] = "life-and-death"  # override
SLUG_MAP["ybc-big-or-urgent-mid-game-and-opening"] = "opening-problems"  # override
SLUG_MAP["dgm-fuseki-puzzles-more"] = "opening-problems"  # override

SLUG_MAP["attacking-drills"] = "tesuji-training"
SLUG_MAP["life-death-course-1"] = "life-and-death"

# ── XV. ADDITIONAL DUTCH GO MAGAZINE ISSUES ─────────────────────────────
# All remaining individual issues → dutch-go-magazine
for s in [
    "dutch-go-magazine-1969-70-7", "dutch-go-magazine-1970-71-8",
    "dutch-go-magazine-1978-79-16", "dutch-go-magazine-1980-81-18",
    "dutch-go-magazine-1981-82-19", "dutch-go-magazine-1986-23",
    "dutch-go-magazine-1988-25", "dutch-go-magazine-1990-27",
    "dutch-go-magazine-1991-28", "dutch-go-magazine-1992-29",
    "dutch-go-magazine-1993-30", "dutch-go-magazine-1994-31",
    "dutch-go-magazine-1995-32", "dutch-go-magazine-1996-33",
    "dutch-go-magazine-1997-34", "dutch-go-magazine-1998-35",
    "dutch-go-magazine-2000-37", "dutch-go-magazine-2001-38",
    "dutch-go-magazine-2002-39", "dutch-go-magazine-2003-40",
    "dutch-go-magazine-2004-41", "dutch-go-magazine-2005-42",
    "dutch-go-magazine-2006-43", "dutch-go-magazine-2008-45",
    "dutch-go-magazine-2009-46", "dutch-go-magazine-2010-47",
    "dutch-go-magazine-2017-19-bul-29-58-atorrante",
    "dutch-go-magazine-2023-bul-88-107-atorrante",
    "dutch-go-errors",
]:
    SLUG_MAP[s] = "dutch-go-magazine"

# Additional British Go Journal issues
for s in [
    "british-go-journal-2001-2010-atorrante",
    "british-go-journal-2021-atorrante",
]:
    SLUG_MAP[s] = "british-go-journal"

# Go World additional
SLUG_MAP["go-world-problems-1999-2005"] = "go-world-problems"

# ── XVI. HASHIMOTO (Utaro) ISBN-BASED VOLUMES ───────────────────────────
# These are the same Hashimoto books identified by ISBN in OGS
for s in [
    "utaro-hashimoto-1-1979-isbn4-381-00570-8",
    "utaro-hashimoto-2-1979-isbn4-381-00570-8",
    "utaro-hashimoto-3-1979-isbn4-381-00570-8",
]:
    SLUG_MAP[s] = "hashimoto-1-year-tsumego"

for s in [
    "utaro-hashimoto-1-1980-isbn4-381-00571-6",
    "utaro-hashimoto-3-1980-isbn4-381-00571-6",
    "utaro-hashimoto-4-1980-isbn4-381-00571-6",
    "utaro-hashimoto-5-1980-isbn4-381-00571-6",
    "utaro-hashimoto-6-1980-isbn4-381-00571-6",
    "utaro-hashimoto-7-1980-isbn4-381-00571-6",
    "utaro-hashimoto-8-1980-isbn4-381-00571-6",
]:
    SLUG_MAP[s] = "hashimoto-famous-creations-300"

for s in [
    "utaro-hashimoto-1-1980-isbn4-381-00590-2",
    "utaro-hashimoto-2-1980-isbn4-381-00590-2",
    "utaro-hashimoto-3-1980-isbn4-381-00590-2",
    "utaro-hashimoto-4-1980-isbn4-381-00590-2",
]:
    SLUG_MAP[s] = "hashimoto-tsumego-millions"

SLUG_MAP["utaro-hashimoto-2-1979-isbn4-381-00570-8"] = "hashimoto-1-year-tsumego"

# ── XVII. ADDITIONAL LIFE & DEATH MAPPINGS ──────────────────────────────
for s in [
    "life-and-death-i-guess", "life-and-death-on-the-edge",
    "life-and-death-quiz-1", "life-and-death-quiz-2",
    "life-and-death-quiz-5", "life-and-death-quiz-9",
    "battle-of-one-eye", "six-die-but-eight-live",
    "line-of-death", "live-after-atari",
    "killing-the-l-group", "black-first-lives-forever2024",
    "45-kyu-direct-death-collection",
]:
    SLUG_MAP[s] = "life-and-death"

SLUG_MAP["life-and-death-training-13"] = "life-death-training-series"

# ── XVIII. ADDITIONAL ATARI / DOUBLE-ATARI MAPPINGS ─────────────────────
for s in [
    "com-double-atari", "elementary-double-atari",
    "first-line-atari", "atari-30k-25k-french",
    "atari-toward-friendly-stones", "lesson-1-atari",
    "take-the-atari",
]:
    SLUG_MAP[s] = "double-atari-problems"

# ── XIX. ADDITIONAL EYE-SHAPE MAPPINGS ──────────────────────────────────
for s in [
    "eyes-and-false-eyes", "false-eyes-spanish",
    "eye-destroying-drills", "eye-making-drills",
    "real-false-eyes-drills", "pim-2-eyes",
]:
    SLUG_MAP[s] = "eye-shape-mastery"

# ── XX. ADDITIONAL CAPTURE MAPPINGS ─────────────────────────────────────
for s in [
    "black-eats-white-first2024", "black-cuts-white-first2024",
]:
    SLUG_MAP[s] = "capture-problems"

# ── XXI. ADDITIONAL TESUJI MAPPINGS ─────────────────────────────────────
for s in [
    "crush-oshi-tsubushi-4-kyu-5-dan", "crush-oshi-tsubushi-9-kyu-5-kyu",
    "attack-pattern-drills", "empty-triangle-drills",
]:
    SLUG_MAP[s] = "tesuji-training"

# ── XXII. GRADED LEVEL MAPPINGS ─────────────────────────────────────────
for s in [
    "puzzles-for-30-25-kyu", "go-puzzles-25-20kyu",
    "go-exercises-ddk", "studies-for-the-elementary-player",
    "19-aug-2025-basic-01", "train-like-kyu-week-1",
]:
    SLUG_MAP[s] = "elementary-essentials"

for s in [
    "12-16-kyu-problems-pack-1", "20-18-kyu",
    "puzzles-20-15kyu", "for-16k-4k",
]:
    SLUG_MAP[s] = "intermediate-essentials"

for s in [
    "5-kyu-collection", "3-kyu-test-demo",
]:
    SLUG_MAP[s] = "upper-intermediate-essentials"

for s in [
    "2-dan-up", "how-to-become-a-dan",
]:
    SLUG_MAP[s] = "advanced-essentials"

SLUG_MAP["bgs-go-4k-1d"] = "advanced-essentials"

# ── XXIII. GO FORMATIONS (additional) ───────────────────────────────────
for s in [
    "rectangular-six-corner", "rectangular-six-edge",
    "rectangular-eight-1",
]:
    SLUG_MAP[s] = "shape-problems"

SLUG_MAP["double-tigers-mouth"] = "shape-problems"
SLUG_MAP["golden-chicken-standing-on-one-leg"] = "golden-chicken"
SLUG_MAP["mouse-stealing-oil"] = "tesuji-training"
SLUG_MAP["alphabet-gogeo-t-group"] = "shape-problems"

# ── XXIV. STRATEGY / TERRITORY / FORMATIONS ─────────────────────────────
for s in [
    "forth-line-formation", "second-line-formation",
    "second-line-formation-corner", "thrid-line-formation",
]:
    SLUG_MAP[s] = "shape-problems"

for s in [
    "protect-the-territory", "determine-who-wins-1",
]:
    SLUG_MAP[s] = "territory-scoring"

for s in [
    "take-the-base", "get-a-base",
]:
    SLUG_MAP[s] = "opening-problems"

# ── XXV. KO ADDITIONAL ─────────────────────────────────────────────────
SLUG_MAP["ko-loop-concept"] = "ko-problems"
SLUG_MAP["qi-liberty-number"] = "liberty-shortage"

# ── XXVI. AUTHOR COLLECTIONS (additional) ───────────────────────────────
SLUG_MAP["michael-redmond-9p-youtube-tsumegos"] = "michael-redmond-9p-youtube-tsumegos"
SLUG_MAP["nagahara-strategic-concepts-of-go-1972"] = "nagahara-strategic-concepts"
SLUG_MAP["nagahara-bozulich-handicap-go"] = "nagahara-bozulich-handicap-go"
SLUG_MAP["sung-ho-baek-the-master-of-haengma"] = "sung-ho-baek-haengma"
SLUG_MAP["the-direction-of-play-takeo-kajiwara"] = "kajiwara-direction-of-play"
SLUG_MAP["yilun-yang-fundamental-principles-of-go-problems"] = "yilun-yang-fundamental-principles"
SLUG_MAP["one-more-cho-intermediate"] = "cho-chikun-life-death-intermediate"
SLUG_MAP["river-mountain-tsumego-30-kyu"] = "river-mountain-go-1"
SLUG_MAP["korean-problem-academy-1"] = "korean-problem-academy-1"
SLUG_MAP["train-like-a-pro-kim-seong-rae"] = "train-like-a-pro-kim-seong-rae"
SLUG_MAP["5x5-problems-from-fukui-masaaki-8d"] = "5x5-problems-fukui-masaaki"
SLUG_MAP["go-seigen-jikyou-fusoku-isbn-4-416-79711-7"] = "go-seigen-tsumego-dojo"

# ── XXVII. CONNECTION / CUTTING ADDITIONAL ──────────────────────────────
for s in ["connect-and-cut-2", "connect-and-cut-3"]:
    SLUG_MAP[s] = "connection-problems"

# ── XXVIII. ENDGAME ADDITIONAL ──────────────────────────────────────────
SLUG_MAP["end-game-1"] = "endgame-problems"

# ── XXIX. MIDDLE GAME ──────────────────────────────────────────────────
SLUG_MAP["middle-game-problems"] = "whole-board-thinking"
SLUG_MAP["problems-from-pro-games"] = "whole-board-thinking"
SLUG_MAP["haengma-a-strengthen"] = "shape-problems"

# ── XXX. 9x9 ADDITIONAL ────────────────────────────────────────────────
SLUG_MAP["correcting-my-breakpoints-size-9x9-level-2"] = "9x9-problems"

# ── XXXI. SCHOOL / REGIONAL ADDITIONAL ──────────────────────────────────
SLUG_MAP["homework-session-4"] = "vietnam-go-school"
SLUG_MAP["go-class-homework"] = "general-practice"
SLUG_MAP["chinese-weiqi-homework-11"] = "general-practice"
SLUG_MAP["class-5-homework-corrected-mistakes-on-q4-5-and-11"] = "general-practice"
SLUG_MAP["go-fundamentals-german"] = "novice-essentials"
SLUG_MAP["basic-puzzles-dutch"] = "novice-essentials"
SLUG_MAP["go-presentation-dutch"] = "novice-essentials"
SLUG_MAP["go-presentation-farel"] = "novice-essentials"

# ── XXXII. CLASSICAL ADDITIONAL ─────────────────────────────────────────
SLUG_MAP["xuan-xuan-qijing"] = "xuanxuan-qijing"
SLUG_MAP["the-celestial-arsenal"] = "general-practice"

# ── XXXIII. REMAINING GENERAL PRACTICE ──────────────────────────────────
# These are genuinely miscellaneous / too generic to categorize
for s in [
    "actual-game-problems", "an-incomplete-set-of-go-flash-cards",
    "chance-problems-try-your-chance", "easy-peasy-go",
    "easy-peasy-puzzles", "fixed-patterns-pda",
    "hard-but-interesting", "hong-dojo-problems-c",
    "jp-problems", "junior-level-exersices",
    "lunch-time", "mistakes-in-my-games",
    "my-public-games-reviews-problems", "player-guide-to-go",
    "problem-collection-2", "questions-for-100",
    "steppingstones-to-go", "student-practice-box-1",
    "test-your-go-strenght", "the-go-problems-that-are-good",
    "the-theory-and-practice-of-go-problems",
    "go-school-problems", "go-problems-46",
    "two-choice-tsumego-9-19kyu",
    "20-questions-for-masters-1", "20-questions-for-masters-2",
    "fundamentals-flow-of-the-stones",
]:
    SLUG_MAP[s] = "general-practice"


# ── CANONICAL COLLECTION DEFINITIONS ─────────────────────────────────────
# These define the metadata for NEW canonical collections (those that don't
# exist yet as a slug in the input). Existing canonical collections inherit
# their metadata from the first matching input collection.

NEW_CANONICAL: dict[str, dict] = {
    "life-and-death": {
        "name": "Life and Death Problems",
        "description": "Comprehensive collection of life and death (tsumego) problems across all levels.",
        "curator": "Curated",
        "source": "mixed",
        "type": "technique",
        "ordering": "source",
        "tier": "editorial",
    },
    "capture-problems": {
        "name": "Capture Problems",
        "description": "Problems focusing on capturing techniques including basic captures, sacrifice captures, and advanced capture tactics.",
        "curator": "Curated",
        "source": "mixed",
        "type": "technique",
        "ordering": "source",
        "tier": "editorial",
    },
    "opening-problems": {
        "name": "Opening Problems",
        "description": "Opening (fuseki) problems covering corner approaches, extensions, influence, and whole-board strategy.",
        "curator": "Curated",
        "source": "mixed",
        "type": "technique",
        "ordering": "source",
        "tier": "editorial",
    },
    "double-atari-problems": {
        "name": "Double Atari Problems",
        "description": "Problems focusing on double atari, mutual atari, and continuous atari techniques.",
        "curator": "Curated",
        "source": "mixed",
        "type": "technique",
        "ordering": "source",
        "tier": "editorial",
    },
    "joseki-problems": {
        "name": "Joseki Problems",
        "description": "Joseki (corner sequence) problems for all levels, from basic to advanced.",
        "curator": "Curated",
        "source": "mixed",
        "type": "technique",
        "ordering": "source",
        "tier": "editorial",
    },
    "joseki-antique-corner": {
        "name": "JOSEKI: Almost Antique Corner Sequences",
        "description": "Comprehensive collection of classical corner sequences (6000+ positions) compiled by Atorrante.",
        "curator": "Atorrante",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "premier",
    },
    "james-davies-tesuji": {
        "name": "James Davies: Tesuji (Elementary Go Series)",
        "description": "Tesuji problems from James Davies' Elementary Go Series.",
        "curator": "James Davies",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "premier",
    },
    "james-davies-life-death": {
        "name": "James Davies: Life and Death (Elementary Go Series)",
        "description": "Life and death problems from James Davies' Elementary Go Series.",
        "curator": "James Davies",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "premier",
    },
    "james-davies-endgame": {
        "name": "James Davies & Ogawa: The Endgame (Elementary Go Series)",
        "description": "Endgame problems from Tomoko Ogawa and James Davies' Elementary Go Series.",
        "curator": "James Davies",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "premier",
    },
    "bozulich-life-and-death": {
        "name": "Bozulich: Get Strong at Life and Death",
        "description": "Life and death problems from Richard Bozulich's Get Strong series.",
        "curator": "Richard Bozulich",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "bozulich-endgame": {
        "name": "Bozulich: Get Strong at the Endgame",
        "description": "Endgame problems from Richard Bozulich's Get Strong series.",
        "curator": "Richard Bozulich",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "bozulich-fuseki": {
        "name": "Bozulich: 501 Fuseki Problems",
        "description": "Opening problems from Richard Bozulich's 501 Opening Problems.",
        "curator": "Richard Bozulich",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "premier",
    },
    "honinbo-shusai-life-death": {
        "name": "Honinbo Shusai: Curious Mechanics of Life and Death",
        "description": "Life and death problems from Honinbo Shusai (Igo Kenkyukai), 3 volumes.",
        "curator": "Honinbo Shusai",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "yang-yilun-life-death": {
        "name": "Yang Yilun: Ingenious Life and Death Puzzles",
        "description": "Life and death puzzles from Yang Yilun's Ingenious L&D series (Vol 1+2).",
        "curator": "Yang Yilun",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "premier",
    },
    "wang-zhipeng-life-death": {
        "name": "Wang Zhipeng: 1000 Life and Death Problems",
        "description": "1000 life and death problems by Wang Zhipeng.",
        "curator": "Wang Zhipeng",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "premier",
    },
    "noguchi-fundamental-tsumego": {
        "name": "Noguchi: 90 Fundamental Tsumego",
        "description": "90 fundamental tsumego problems by Motoki Noguchi.",
        "curator": "Motoki Noguchi",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "premier",
    },
    "hyacinth-life-death": {
        "name": "Hyacinth: Life and Death Problems",
        "description": "Life and death problems and lecture materials by Hyacinth.",
        "curator": "Hyacinth",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "in-seong-hwang-problems": {
        "name": "In-seong Hwang 8d Problems",
        "description": "Go problems by In-seong Hwang (8 dan).",
        "curator": "In-seong Hwang",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "premier",
    },
    "rennes-go-school": {
        "name": "Ecole de Go de Rennes",
        "description": "Comprehensive curriculum from the Rennes Go School covering 30k through 10k, joseki, life/death, and shapes.",
        "curator": "Ecole de Go de Rennes",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "premier",
    },
    "ogs-learn-to-play": {
        "name": "OGS: Learn to Play Go",
        "description": "Complete OGS Learn to Play Go course (parts 4-7) by Atorrante.",
        "curator": "Atorrante",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "premier",
    },
    "life-death-training-series": {
        "name": "Life and Death Training Series",
        "description": "Numbered life and death training series (死活訓練 1-12).",
        "curator": "Community",
        "source": "ogs",
        "type": "technique",
        "ordering": "source",
        "tier": "curated",
    },
    "pim-go-school": {
        "name": "PIM Go School (T.Boss)",
        "description": "Thai Go school curriculum by T.Boss covering tesuji, snapback, net, ladder, and applied tactics.",
        "curator": "T.Boss (PIM)",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "curated",
    },
    "introduction-to-weiqi": {
        "name": "Introduction to Weiqi (Di Yansheng & Xu Ying)",
        "description": "Comprehensive Weiqi textbook by Di Yansheng and Xu Ying covering capture, life/death, tactics, shapes, connection, and strategy.",
        "curator": "Di Yansheng & Xu Ying",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "curated",
    },
    "krun-go-school": {
        "name": "Krun Go School",
        "description": "Go problems series by Krun covering basics, capturing, and endgame.",
        "curator": "Krun",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "premier",
    },
    "1200igo-quizzes": {
        "name": "1200igo Quiz Series",
        "description": "Quiz series from 1200igo covering various Go topics.",
        "curator": "1200igo",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "curated",
    },
    "gohouse-30k": {
        "name": "Gohouse 30 Kyu Series",
        "description": "30 kyu beginner problems from Gohouse.",
        "curator": "Gohouse",
        "source": "ogs",
        "type": "graded",
        "ordering": "source",
        "tier": "curated",
    },
    "level-up-series": {
        "name": "Level Up Series",
        "description": "Progressive level-up problem series.",
        "curator": "Community",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "curated",
    },
    "taruc-practice": {
        "name": "TARUC Practice Series",
        "description": "Practice problem series from TARUC Go club.",
        "curator": "TARUC",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "curated",
    },
    "dutch-go-magazine": {
        "name": "Dutch Go Magazine Problems",
        "description": "Go problems from the Dutch Go Magazine (Het Paard) spanning 1979-2022.",
        "curator": "Dutch Go Association",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "curated",
    },
    "british-go-journal": {
        "name": "British Go Journal Problems",
        "description": "Go problems from the British Go Journal (1967-2020).",
        "curator": "British Go Association",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "curated",
    },
    "aga-problems": {
        "name": "AGA Problems of the Week",
        "description": "Weekly problems from the American Go Association.",
        "curator": "AGA",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "premier",
    },
    "territory-scoring": {
        "name": "Territory and Scoring Problems",
        "description": "Problems on territory counting, area scoring, and game judgment.",
        "curator": "Community",
        "source": "ogs",
        "type": "technique",
        "ordering": "source",
        "tier": "premier",
    },
    "influence-strategy": {
        "name": "Influence and Strategy Problems",
        "description": "Problems on limiting influence, big points, and strategic thinking.",
        "curator": "Community",
        "source": "ogs",
        "type": "technique",
        "ordering": "source",
        "tier": "premier",
    },
    "whole-board-thinking": {
        "name": "Whole Board Thinking",
        "description": "Problems on whole-board strategy and proper move selection.",
        "curator": "Community",
        "source": "ogs",
        "type": "technique",
        "ordering": "source",
        "tier": "curated",
    },
    "9x9-problems": {
        "name": "9x9 Board Problems",
        "description": "Problems specific to 9x9 board play including openings and corner fights.",
        "curator": "Community",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "premier",
    },
    "general-practice": {
        "name": "General Practice Problems",
        "description": "Mixed practice problems covering various Go topics.",
        "curator": "Community",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "curated",
    },
    "vietnam-go-school": {
        "name": "Vietnam Go School",
        "description": "Vietnamese Go school curriculum including homework and tutorials.",
        "curator": "Community",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "curated",
    },
    "cambridge-go-club": {
        "name": "Cambridge Go Club Practice",
        "description": "Practice puzzles from the Cambridge Go Club.",
        "curator": "Cambridge Go Club",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "premier",
    },
    "turkey-go-library": {
        "name": "Turkey Go Library",
        "description": "Go problem library from Turkey.",
        "curator": "Community",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "premier",
    },
    "gostar-school": {
        "name": "Gostar School",
        "description": "Homework and practice problems from Gostar.",
        "curator": "Gostar",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "curated",
    },
    "lu-school": {
        "name": "LU Practice Problems",
        "description": "Practice problems from London University Go club.",
        "curator": "LU",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "premier",
    },
    "falling-in-love-with-baduk": {
        "name": "Falling in Love with Baduk (Dahye Lee & Jihee Baek)",
        "description": "Korean beginner Go book by Dahye Lee and Jihee Baek.",
        "curator": "Dahye Lee & Jihee Baek",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "premier",
    },
    "shikatsu-myoki": {
        "name": "Shikatsu Myoki (Life and Death Brilliant Stratagems)",
        "description": "Classical collection: 死活妙機 — brilliant life and death stratagems.",
        "curator": "Classical",
        "source": "ogs",
        "type": "technique",
        "ordering": "source",
        "tier": "curated",
    },
    "qi-jing-zhong-miao": {
        "name": "Qi Jing Zhong Miao (Wonders of Go)",
        "description": "Classical Chinese Go collection: 棋經衆妙.",
        "curator": "Classical",
        "source": "ogs",
        "type": "technique",
        "ordering": "source",
        "tier": "premier",
    },
    "book-of-pure-pleasures": {
        "name": "Book of Pure Pleasures and Forgotten Worries",
        "description": "Classical Chinese Go collection: 忘憂清樂集.",
        "curator": "Classical",
        "source": "ogs",
        "type": "technique",
        "ordering": "source",
        "tier": "premier",
    },
    "graded-go-problems-beginners-1": {
        "name": "Graded Go Problems for Beginners Vol 1",
        "description": "Volume 1 of Kano Yoshinori's Graded Go Problems for Beginners.",
        "curator": "Kano Yoshinori",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "premier",
    },
    "basic-dictionary-life-death-1": {
        "name": "A Basic Dictionary of Life and Death Vol 1",
        "description": "Volume 1 of Cho Chikun's basic dictionary of life and death.",
        "curator": "Cho Chikun",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "premier",
    },
    "encyclopedia-life-death-2": {
        "name": "Encyclopedia of Life and Death Part Two",
        "description": "Second volume of the Encyclopedia of Life and Death.",
        "curator": "Community",
        "source": "ogs",
        "type": "technique",
        "ordering": "source",
        "tier": "premier",
    },
    "wang-zhi-tsumegos": {
        "name": "Wang Zhi et al. 1000 Tsumegos",
        "description": "1000 tsumego problems by Wang Zhi and collaborators.",
        "curator": "Wang Zhi",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "premier",
    },
    "fran-go-library": {
        "name": "Fran's Go Library",
        "description": "Personal collection and playground puzzles by Fran.",
        "curator": "Fran",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "premier",
    },
    "fuiter-problems": {
        "name": "Fuiter Go Problems",
        "description": "Go problems by Fuiter.",
        "curator": "Fuiter",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "premier",
    },
    "rin-kaiho-golden-opportunities": {
        "name": "Rin Kaiho: Golden Opportunities",
        "description": "Go problems from Rin Kaiho's Golden Opportunities.",
        "curator": "Rin Kaiho",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "gogameguru-easy": {
        "name": "GoGameGuru Easy Series",
        "description": "Easy problem series from GoGameGuru.",
        "curator": "GoGameGuru",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "premier",
    },
    "golden-chicken": {
        "name": "Golden Chicken Standing on One Leg",
        "description": "Problems on the Golden Chicken Standing on One Leg (金雞獨立) formation.",
        "curator": "Community",
        "source": "ogs",
        "type": "technique",
        "ordering": "source",
        "tier": "premier",
    },
    "l-shape": {
        "name": "The L-Shape",
        "description": "Problems on the L-Shape (7字形) life and death formation.",
        "curator": "Madgo (HKGCA)",
        "source": "ogs",
        "type": "technique",
        "ordering": "source",
        "tier": "curated",
    },
    "nyudan-tesuji-250": {
        "name": "Nyudan Compulsory Tesuji 250",
        "description": "250 compulsory tesuji problems from Nyudan (ISBN 4818202770).",
        "curator": "Nyudan",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "kano-tactical-fights": {
        "name": "Basic Tactical Fights (Kano Books 1 & 2)",
        "description": "Basic tactical fight problems from Kano Yoshinori's books 1 and 2.",
        "curator": "Kano Yoshinori",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "life-and-death-second-line": {
        "name": "Life and Death on the Second Line",
        "description": "Specialized life and death problems occurring on the second line.",
        "curator": "Community",
        "source": "ogs",
        "type": "technique",
        "ordering": "source",
        "tier": "curated",
    },
    "fujisawa-fuseki": {
        "name": "Fujisawa: Fuseki Exercises",
        "description": "Opening exercises from Fujisawa Shuuko.",
        "curator": "Fujisawa Shuuko",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "michael-redmond-9p-youtube-tsumegos": {
        "name": "Michael Redmond 9p YouTube Tsumegos",
        "description": "Tsumego problems from Michael Redmond 9p's YouTube channel.",
        "curator": "Michael Redmond",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "nagahara-strategic-concepts": {
        "name": "Nagahara: Strategic Concepts of Go (1972)",
        "description": "Strategic concepts and problems from Nagahara's 1972 classic.",
        "curator": "Nagahara",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "nagahara-bozulich-handicap-go": {
        "name": "Nagahara & Bozulich: Handicap Go",
        "description": "Handicap Go problems from Nagahara and Bozulich.",
        "curator": "Nagahara & Bozulich",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "sung-ho-baek-haengma": {
        "name": "Sung-Ho Baek: The Master of Haengma",
        "description": "Haengma (stone movement) problems from Korean pro Sung-Ho Baek.",
        "curator": "Sung-Ho Baek",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "kajiwara-direction-of-play": {
        "name": "Takeo Kajiwara: The Direction of Play",
        "description": "Strategic problems from Takeo Kajiwara's The Direction of Play.",
        "curator": "Takeo Kajiwara",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "yilun-yang-fundamental-principles": {
        "name": "Yang Yilun: Fundamental Principles of Go",
        "description": "Problems from Yang Yilun's Fundamental Principles of Go.",
        "curator": "Yang Yilun",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "korean-problem-academy-1": {
        "name": "Korean Problem Academy Vol. 1",
        "description": "Go problems from the Korean Problem Academy series, Volume 1.",
        "curator": "Korean Problem Academy",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "curated",
    },
    "train-like-a-pro-kim-seong-rae": {
        "name": "Train Like a Pro (Kim Seong-rae)",
        "description": "Professional-level training problems by Kim Seong-rae.",
        "curator": "Kim Seong-rae",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "5x5-problems-fukui-masaaki": {
        "name": "5x5 Problems (Fukui Masaaki 8D)",
        "description": "Problems on a 5x5 board by Fukui Masaaki (8 dan).",
        "curator": "Fukui Masaaki",
        "source": "ogs",
        "type": "author",
        "ordering": "source",
        "tier": "curated",
    },
    "go-world-problems": {
        "name": "Go World Problems",
        "description": "Problems from Go World magazine spanning multiple decades.",
        "curator": "Atorrante",
        "source": "ogs",
        "type": "reference",
        "ordering": "source",
        "tier": "premier",
    },
}


def consolidate() -> None:
    """Run the consolidation."""
    dry_run = "--dry-run" in sys.argv

    with open(COLLECTIONS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    old_collections: list[dict] = data["collections"]
    print(f"Input: {len(old_collections)} collections")

    # Phase 1: Build mapping for every slug
    unmapped: list[str] = []
    for c in old_collections:
        slug = c["slug"]
        if slug not in SLUG_MAP:
            unmapped.append(slug)
            SLUG_MAP[slug] = "general-practice"  # catch-all

    if unmapped:
        print(f"\n⚠ {len(unmapped)} slugs fell through to general-practice:")
        for s in sorted(unmapped):
            print(f"  - {s}")

    # Phase 2: Group collections by canonical target
    canonical_groups: dict[str, list[dict]] = {}
    for c in old_collections:
        target = SLUG_MAP[c["slug"]]
        canonical_groups.setdefault(target, []).append(c)

    # Phase 3: Build consolidated collections
    result: list[dict] = []
    total_aliases = 0

    for canonical_slug, group in sorted(canonical_groups.items()):
        # Pick the "primary" collection (prefer editorial tier, then premier)
        tier_order = {"editorial": 0, "premier": 1, "curated": 2}
        group.sort(key=lambda c: tier_order.get(c.get("tier", "curated"), 2))
        primary = group[0]

        # Use NEW_CANONICAL metadata if defined, otherwise inherit from primary
        if canonical_slug in NEW_CANONICAL:
            meta = NEW_CANONICAL[canonical_slug]
            entry = {
                "slug": canonical_slug,
                "name": meta["name"],
                "description": meta["description"],
                "curator": meta["curator"],
                "source": meta["source"],
                "type": meta["type"],
                "ordering": meta["ordering"],
                "tier": meta["tier"],
            }
        else:
            entry = {
                "slug": canonical_slug,
                "name": primary["name"],
                "description": primary.get("description", ""),
                "curator": primary.get("curator", "Community"),
                "source": primary.get("source", "ogs"),
                "type": primary.get("type", "reference"),
                "ordering": primary.get("ordering", "source"),
                "tier": primary.get("tier", "curated"),
            }

        # Collect all aliases from all absorbed collections
        all_aliases: set[str] = set()
        for c in group:
            # Add existing aliases
            for alias in c.get("aliases", []):
                alias = alias.strip()
                if alias:
                    all_aliases.add(alias)
            # Add the collection's own name as alias (if different)
            if c["name"].strip() != entry["name"].strip():
                all_aliases.add(c["name"].strip())

        # Remove the canonical name itself from aliases
        all_aliases.discard(entry["name"])
        all_aliases.discard(entry["name"].strip())

        entry["aliases"] = sorted(all_aliases)
        total_aliases += len(entry["aliases"])
        result.append(entry)

    print(f"\nOutput: {len(result)} canonical collections")
    print(f"Total aliases preserved: {total_aliases}")

    # Sort result: editorial first, then premier, then curated; within tier alphabetically
    tier_sort = {"editorial": 0, "premier": 1, "curated": 2}
    result.sort(key=lambda c: (tier_sort.get(c["tier"], 2), c["slug"]))

    if dry_run:
        print("\n[DRY RUN] Not writing file.")
        print("\nCanonical collections by tier:")
        for tier in ["editorial", "premier", "curated"]:
            tier_items = [c for c in result if c["tier"] == tier]
            print(f"  {tier}: {len(tier_items)}")
            for c in tier_items:
                print(f"    {c['slug']} ({len(c['aliases'])} aliases)")
    else:
        data["collections"] = result
        atomic_write_json(COLLECTIONS_PATH, data, indent=2, ensure_ascii=False)
        print(f"\n✓ Written to {COLLECTIONS_PATH}")


if __name__ == "__main__":
    consolidate()
