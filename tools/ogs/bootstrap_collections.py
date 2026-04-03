"""
Bootstrap new collection entries from OGS sorted collections JSONL.

Reads the sorted JSONL (from sort_collections.py), identifies OGS
collections that don't match any existing YenGo collection slug, and
generates new config/collections.json entries for premier/curated tiers.

The output is a proposed collections.json for human review before merging.

Usage:
    python -m tools.ogs.bootstrap_collections --input <sorted-jsonl>
    python -m tools.ogs.bootstrap_collections -i <file> --dry-run
    python -m tools.ogs.bootstrap_collections -i <file> -o <output-file>
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

from tools.core.paths import rel_path
from tools.core.text_cleaner import (
    NON_LATIN_RE as _NON_LATIN_RE,
)
from tools.core.text_cleaner import (
    clean_name as _core_clean_name,
)
from tools.core.text_cleaner import (
    extract_english_portion as _extract_english_portion,
)
from tools.core.text_cleaner import (
    generate_slug,
    infer_curator,
    infer_type,
)
from tools.ogs.collections import CollectionMatcher
from tools.ogs.config import get_project_root
from tools.ogs.sort_collections import read_collections

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================================
# OGS-Specific Name Cleanup
# ============================================================================

# Map from OGS quality_tier to collections schema tier values
_OGS_TIER_MAP: dict[str, str] = {
    "premier": "premier",
    "curated": "curated",
    "community": "community",
    "unvetted": "community",  # fallback if unvetted slips through
}

# ============================================================================
# Manual Overrides for High-Value Non-Latin Collections
# ============================================================================
# Curated by Go domain expertise: slugs use standard English Go terminology,
# no author names, no language/cultural markers, no usernames.

_SLUG_OVERRIDES: dict[int, str] = {
    # Russian
    9389: "basic-shape-recognition",          # базовые формы 1
    951: "capturing-fundamentals",            # Задачи на взятие камней.1
    4004: "capturing-tactics",                # Задачи на взятие камней. 2
    4034: "advanced-capturing",               # Задачи на взятие камней. 3
    2384: "tesuji-strength",                  # Стань сильным в тэсудзи
    2020: "golden-opportunities",             # Рин Кайхо - Золотые возможности
    9621: "shape-play",                       # игра по форме, 10кю+
    7619: "tesuji-semeai",                    # Тэсудзи 3 Сэмэай
    8689: "bozulich-fuseki-problems",         # Бозулич_501 задача на фусеки
    7352: "puzzles-20-15kyu",                 # 20-15кю
    7365: "puzzles-20-15kyu-vol3",            # 20-15кю 3
    7358: "puzzles-20-16kyu-vol2",            # 20-16кю 2
    3276: "interactive-go-intro",             # Интерактивное введение в Го
    9392: "basic-shape-recognition-2",        # базовые формы 2
    9781: "problem-collection-2",             # Задачник №2.
    # Thai
    5442: "geta-technique",                   # ปิดประตู (door closing = geta)
    8714: "endgame-essentials",               # [camp] ท้ายเกม - ปัญหาช่วงท้ายเกม
    8705: "opening-shapes",                   # [camp] เปิดเกม - เชพหมาก
    9924: "eye-shape-fundamentals",           # ห้องจริง ห้องปลอม และ การจับกิน
    6572: "go-puzzles-25-20kyu",              # โจทย์หมากล้อม 25-20คิว
    6056: "krun-capturing-basics",            # จับกินเบื้องต้น By Krun
    # Chinese
    5625: "precise-endgame",                  # 權甲龍精妙收官
    10247: "fourth-line-endgame",             # 四路官子譜
    5783: "tesuji-capturing",                 # 基本手筋事典 吃子 capturing
    10382: "intermediate-lectures",           # 佑林中級D講義
    10757: "life-death-training-10k-5k",      # 死活專項訓練 (10級到5級)
    5680: "hong-dojo-problems-c",             # 洪道場秘傳問題集 class C
    6830: "brilliant-moves-1",                # 鬼手魔手 1 Satan's move 1
    6855: "brilliant-moves-2",                # 鬼手魔手 2 Satan's move 2
    7438: "fuiter-go-problems",               # Fuiter Go-荒漠版本更新
    # Korean
    4895: "tesuji-dictionary",                # 수근대사전
    # Japanese
    5744: "yamada-practical-tesuji",           # Yamada Kimio -- 直感力を鍛える 囲碁・実戦手筋
    7769: "life-death-auto-response",          # Amigo no igo - 詰碁 - Life and Death
    7895: "two-choice-tsumego-9-19kyu",       # 【2択】詰碁解けたら寝ろシリーズ【9-19級】
    # Vietnamese (Latin script but not English)
    10819: "van-vuong-introduction",           # Van Vuong - Bai tap nhap mon
    8312: "homework-session-1-extra",          # BTVN buoi 1 extra
    10483: "fixed-patterns-pda",               # Dinh thuc PDA
    10563: "beautiful-shapes",                 # Hinh dep
    8328: "homework-session-2",                # BTVN buoi 2
    8345: "homework-session-3",                # BTVN buoi 3
    8373: "homework-session-4",                # BTVN buoi 4
    # Vietnamese "tren lop" (classroom drills) cluster
    8368: "eye-making-drills",                 # Tạo mắt trên lớp
    8370: "eye-destroying-drills",             # Phá mắt trên lớp
    8326: "capture-drills-vn",                 # Cướp trên lớp
    8318: "connection-drills",                 # Nối quân trên lớp
    8333: "geta-capture-drills",               # Bắt tại cửa trên lớp
    8336: "snapback-drills",                   # Vồ ngược trên lớp
    8369: "real-false-eyes-drills",            # Mắt thật mắt giả trên lớp
    8334: "shape-correction-drills",           # Chỉnh quân trên lớp
    8371: "seki-drills",                       # Sống chung trên lớp
    8323: "capture-race-drills",               # Bắt đối trên lớp
    8335: "net-technique-drills",              # Khóa trên lớp
    8320: "capture-direction-drills",          # Hướng bắt quân trên lớp
    8367: "semeai-drills",                     # Đối sát trên lớp
    8337: "empty-triangle-drills",             # Nối không về trên lớp
    # Vietnamese misc
    10524: "attack-pattern-drills",            # Các hình thức công sát
    10542: "attacking-drills",                 # Tấn công
    10876: "hue-university-go-basics-1",       # Đội Cờ vây Trường Đại Học Y dược Huế #1
    # French
    160: "go-basics-french",                   # Apprendre les bases du go (en Francais)
    543: "rennes-go-school-30kyu",             # Ecole de Go de Rennes - 30k
    622: "rennes-go-school-25kyu",             # Ecole de Go de Rennes - 25k
    975: "rennes-go-school-15kyu",             # Ecole de Go de Rennes - 15k
    985: "rennes-go-school-10kyu",             # Ecole de Go de Rennes - 10k
    1195: "rennes-go-school-shapes",           # Ecole de Go de Rennes - Les formes
    1252: "rennes-go-school-life-death",        # Ecole de Go de Rennes - Vie et Mort
    3311: "rennes-go-school-joseki-20kyu",      # Ecole de Go de Rennes - Josekis 20k
    3461: "rennes-go-school-20kyu",            # Ecole de Go de Rennes - 20k
    3886: "go-school-problems",                # Ecole de Go
    9046: "rennes-go-school-joseki-25kyu",      # Ecole de Go de Rennes - Josekis 25k
    10155: "capture-life-death-easy",          # Capture, vie et mort facile
    10302: "beginner-problems-french",         # problème pour débutant
    10778: "life-death-problems-french",       # Problème de vie ou de mort
    1549: "go-basics-2",                       # Les bases du go
    # Spanish
    1795: "elementary-life-death-spanish",      # vida y muerte elemental
    1199: "line-of-death",                     # Línea de la Muerte
    1801: "connect-and-cut-1",                 # conexión y corte 1
    1802: "connect-and-cut-2",                 # conexión y corte II
    1807: "connect-and-cut-3",                 # conexión y corte III
    1806: "bamboo-joint",                      # Nudo de bambú
    3658: "go-exercises-ddk",                  # Ejercicios de Go para DDK
    5136: "life-death-course-1",               # CURSO NIVEL 1: VIDA Y MUERTE I
    7920: "life-death-capture-problems",       # Problemas de vida, muerte y capturas
    2695: "jp-problems",                       # JP problemas
    435: "tutorial-collection-spanish",         # Coleccion Tutorial en espanol
    # German
    261: "go-fundamentals-german",             # Go-Grundlagen (German)
    3423: "corner-life-death-german",          # Leben und Tod in der Ecke
    # Club/acronym overrides
    9872: "lu-practice-problems",              # LU!01 (club code, 172 puzzles)
    9871: "graded-problems-beginners-1",       # GGPB1 (acronym, 239 puzzles)
    7512: "student-practice-box-1",            # Student Box Vol.1
    4020: "train-like-kyu-week-1",             # Kyu Gibi Çalış - Hafta 1 (Turkish)
    8472: "joseki-problems-iscimenozgur",      # İscimenOzgur's Joseki Problems (Turkish)
    # More Spanish
    2668: "beginners-spanish",                # Principiantes
    1787: "capture-spanish",                  # Captura
    1799: "edges",                            # Bordes
    4009: "review-problems",                  # REPASO
    1844: "assessment-problems",              # Evaluacion
    8601: "ladder-review",                    # Escaleras repaso
    1814: "elementary-double-atari",          # Doble atari elemental
    1813: "continuous-atari",                 # atari continuo
    1810: "first-line-atari",                 # atari en primera linea
    1811: "atari-toward-friendly-stones",     # atari hacia piedras aliadas
    1791: "mutual-atari",                     # Atari mutuo
    1822: "false-eyes-spanish",              # ojos falsos
    4092: "eyes-and-false-eyes",             # OJOS-OJOS FALSOS
    8134: "reducing-liberties-2",             # reduciendo libertades 2
    1805: "double-tigers-mouth",             # doble boca de tigre
    10798: "monday-tsumego",                  # Lunes de Tsumegos
    3344: "basic-rules-aago",                # REGLAS BASICAS AAGO
    1818: "snapback-technique",              # tecnica de snapback
    3934: "capture-exercises-1",             # Ejercicios capturas I
    # More French
    7119: "go-problems-french",               # problème go
    10181: "go-tutorial-french",              # Tuto GO FR
    133: "small-joseki-collection",           # petit joseki collection
    3885: "atari-30k-25k-french",             # 30K-25K Atari (FR)
    # More German
    7216: "beginner-brain-teasers-30kyu",     # Kopfnüsse für Neueinsteiger DGoZ
    6019: "fujisawa-fuseki-exercises",        # K. Lehwald & H. Fujisawa: Fuseki Übungen
    # More Spanish
    2334: "cho-chikun-problems-spanish",      # Problema de Cho Chikun
    # Misspelling fix
    9302: "noguchi-90-fundamental-tsumego",   # Motoki Noguchi I : 90 Fondamentals Tsumego
    # Dutch
    1991: "basic-puzzles-dutch",              # Basis puzzels
    1990: "go-presentation-dutch",            # Laurens en Lucca presentatie
    1998: "go-presentation-farel",            # Eindpresentatie farel GO 1/2
    # Turkish
    7575: "liberties-problems",               # Nefes - Liberties
    # Serbian
    3160: "introduction-to-go-serbian",       # Uvod u Go
    # Thai/Chinese with existing English terms
    5615: "krun-capturing",                   # ท่าจับกิน Krun (Krun series: capturing moves)
    6544: "carpenter-square",                 # 金柜角 Carpenter's Square (standard Go term)
}

_NAME_OVERRIDES: dict[int, str] = {
    # Russian
    9389: "Basic Shape Recognition",
    951: "Capturing Fundamentals",
    4004: "Capturing Tactics",
    4034: "Advanced Capturing",
    2384: "Tesuji Strength Training",
    2020: "Golden Opportunities",
    9621: "Shape Play",
    7619: "Tesuji: Semeai",
    8689: "501 Fuseki Problems",
    7352: "Puzzles 20-15 Kyu",
    7365: "Puzzles 20-15 Kyu Vol 3",
    7358: "Puzzles 20-16 Kyu Vol 2",
    3276: "Interactive Go Introduction",
    9392: "Basic Shape Recognition 2",
    9781: "Problem Collection 2",
    # Thai
    5442: "Geta Technique",
    8714: "Endgame Essentials",
    8705: "Opening Shapes",
    9924: "Eye Shape Fundamentals",
    6572: "Go Puzzles 25-20 Kyu",
    6056: "Capturing Basics by Krun",
    # Chinese
    5625: "Precise Endgame",
    10247: "Fourth Line Endgame",
    5783: "Tesuji: Capturing",
    10382: "Intermediate Lectures",
    10757: "Life and Death Training 10-5 Kyu",
    5680: "Hong Dojo Problem Collection C",
    6830: "Brilliant Moves 1",
    6855: "Brilliant Moves 2",
    7438: "Fuiter Go Problems",
    # Korean
    4895: "Tesuji Dictionary",
    # Japanese
    5744: "Yamada Practical Tesuji",
    7769: "Life and Death: Auto Response",
    7895: "Two-Choice Tsumego 9-19 Kyu",
    # Vietnamese
    10819: "Van Vuong Introduction",
    8312: "Homework Session 1 Extra",
    10483: "Fixed Patterns PDA",
    10563: "Beautiful Shapes",
    8328: "Homework Session 2",
    8345: "Homework Session 3",
    8373: "Homework Session 4",
    # Vietnamese "tren lop" (classroom drills) cluster
    8368: "Eye Making Drills",
    8370: "Eye Destroying Drills",
    8326: "Capture Drills (Vietnamese)",
    8318: "Connection Drills",
    8333: "Geta Capture Drills",
    8336: "Snapback Drills",
    8369: "Real and False Eyes Drills",
    8334: "Shape Correction Drills",
    8371: "Seki Drills",
    8323: "Capture Race Drills",
    8335: "Net Technique Drills",
    8320: "Capture Direction Drills",
    8367: "Semeai Drills",
    8337: "Empty Triangle Drills",
    # Vietnamese misc
    10524: "Attack Pattern Drills",
    10542: "Attacking Drills",
    10876: "Hue University Go Basics 1",
    # French
    160: "Go Basics (French)",
    543: "Rennes Go School 30 Kyu",
    622: "Rennes Go School 25 Kyu",
    975: "Rennes Go School 15 Kyu",
    985: "Rennes Go School 10 Kyu",
    1195: "Rennes Go School: Shapes",
    1252: "Rennes Go School: Life and Death",
    3311: "Rennes Go School: Joseki 20 Kyu",
    3461: "Rennes Go School 20 Kyu",
    3886: "Go School Problems",
    9046: "Rennes Go School: Joseki 25 Kyu",
    10155: "Capture, Life and Death (Easy)",
    10302: "Beginner Problems (French)",
    10778: "Life and Death Problems (French)",
    1549: "Go Basics 2",
    # Spanish
    1795: "Elementary Life and Death (Spanish)",
    1199: "Line of Death",
    1801: "Connect and Cut 1",
    1802: "Connect and Cut 2",
    1807: "Connect and Cut 3",
    1806: "Bamboo Joint",
    3658: "Go Exercises DDK",
    5136: "Life and Death Course 1",
    7920: "Life, Death and Capture Problems",
    2695: "JP Problems",
    435: "Tutorial Collection (Spanish)",
    # German
    261: "Go Fundamentals (German)",
    3423: "Corner Life and Death (German)",
    # Club/acronym overrides
    9872: "LU Practice Problems",
    9871: "Graded Problems for Beginners 1",
    7512: "Student Practice Box 1",
    4020: "Train Like a Kyu Week 1",
    8472: "Joseki Problems by IscimenOzgur",
    # More Spanish
    2668: "Beginners (Spanish)",
    1787: "Capture (Spanish)",
    1799: "Edges",
    4009: "Review Problems",
    1844: "Assessment Problems",
    8601: "Ladder Review",
    1814: "Elementary Double Atari",
    1813: "Continuous Atari",
    1810: "First Line Atari",
    1811: "Atari Toward Friendly Stones",
    1791: "Mutual Atari",
    1822: "False Eyes (Spanish)",
    4092: "Eyes and False Eyes",
    8134: "Reducing Liberties 2",
    1805: "Double Tiger's Mouth",
    10798: "Monday Tsumego",
    3344: "Basic Rules AAGO",
    1818: "Snapback Technique",
    3934: "Capture Exercises 1",
    # More French
    7119: "Go Problems (French)",
    10181: "Go Tutorial (French)",
    133: "Small Joseki Collection",
    3885: "Atari 30-25 Kyu (French)",
    # More German
    7216: "Beginner Brain Teasers 30 Kyu",
    6019: "Fujisawa Fuseki Exercises",
    # More Spanish
    2334: "Cho Chikun Problems (Spanish)",
    # Misspelling fix
    9302: "Noguchi 90 Fundamental Tsumego",
    # Dutch
    1991: "Basic Puzzles (Dutch)",
    1990: "Go Presentation (Dutch)",
    1998: "Go Presentation Farel",
    # Turkish
    7575: "Liberties Problems",
    # Serbian
    3160: "Introduction to Go (Serbian)",
    # Thai/Chinese with existing English terms
    5615: "Krun Capturing",
    6544: "Carpenter's Square",
}

# Skip these OGS IDs (username-only, no identifiable Go topic, test data)
_SKIP_IDS: frozenset[int] = frozenset({
    8479,   # ภีมคุง (Bhimkhung — username)
    10325,  # โจทย์คนหน้าตาดี (username)
    7604,   # กะเพราไข่ดาว Puzzle (nickname, not Go topic)
    3003,   # 092920 (date code)
    3121,   # 102720 (date code)
    3144,   # 1010vs (username)
    2951,   # 091520 (date code)
    10689,  # 1233214321 (test data)
    2571,   # 2021vs (username)
    2984,   # test1357890 (test data)
    9133,   # easy 12312312312 (test data)
    9190,   # Don't click this (joke entry)
    60,     # Xua Xua (username)
    335,    # OldLanD (username)
    7000,   # Ozigo (username)
    8430,   # Giang (username)
    9575,   # water12345 (username)
    8465,   # wayu999 (username)
    6098,   # easydobs (username)
    10312,  # BK Puzzle: (opaque acronym)
    5248,   # darwinsais puzzles (username)
    3968,   # C2B2 Salvese quien pueda! (club code + Spanish idiom)
    8147,   # denizy (username)
    7846,   # Pattt.15 (username)
    857,    # zion153 (username)
    9905,   # BPTBG1 (unknown acronym)
    # Gomoku (not Go)
    10058,  # Gomoku Surewin Opening (different game)
    # Personal/opaque collections
    984,    # my picture (personal)
    2238,   # learn go(!@"U"@!) (garbled name)
    4755,   # Random stuff (no identifiable topic)
    86,     # AYD flakeman2 (username)
    6778,   # Basic1 Test (test data)
    1288,   # LevelUp.7.test1. (test data)
    9904,   # MyPractice (personal practice)
    8130,   # Jc puzzle (personal, click my profile)
    # Username-based collections
    9613,   # water12345 - shoujin - 1 (username)
    9592,   # water12345 - shoujin - 2 (username)
    9625,   # water12345 - jingong (username)
    # Opaque day-numbered collections
    5025,   # day 1 (opaque schedule)
    5055,   # day 2
    5061,   # day 3
    5074,   # day 4
    5079,   # day 5
    5084,   # day 6
    5088,   # day 7
    5110,   # day 8
    5812,   # day 9
    # Non-standard board / misc skip
    7883,   # chuẩn bị chơi bàn 23x23 (non-standard board, Vietnamese)
})

# Website prefixes to strip from OGS collection names (OGS-specific)
_WEBSITE_PREFIX_RE = re.compile(
    r'^(?:'
    r'101Weiqi\s*[:.]\s*|'
    r'101Weiqi\.com\s+|'
    r'Madgo\(HKGCA\)[_\s]+|'
    r"gogameguru['\u2019]?s?\s+|"
    r'Blogcovay\s+|'
    r'1200igo\s+'
    r')',
    re.IGNORECASE,
)


def clean_name(ogs_name: str) -> str:
    """Clean up an OGS collection name for display.

    Wraps tools.core.text.clean_name with OGS-specific website prefix stripping.

    Args:
        ogs_name: Raw OGS collection name.

    Returns:
        Cleaned display name.
    """
    return _core_clean_name(ogs_name, extra_strip_patterns=[_WEBSITE_PREFIX_RE])


def generate_collection_entry(record: dict[str, Any]) -> dict[str, Any]:
    """Generate a new collection entry from an OGS collection record.

    Fits into the existing collection schema (no new fields).
    Applies manual overrides, bilingual extraction, and website prefix
    stripping for high-quality English-only names.

    Args:
        record: OGS collection record from sorted JSONL.

    Returns:
        Collection entry dict conforming to schema.
    """
    ogs_id = record.get("id", 0)
    ogs_name = record["name"]

    # Priority 1: Manual overrides for curated collections
    if ogs_id in _NAME_OVERRIDES:
        display_name = _NAME_OVERRIDES[ogs_id]
    # Priority 2: Bilingual extraction for CJK/Thai/Cyrillic names
    elif _NON_LATIN_RE.search(ogs_name):
        english = _extract_english_portion(ogs_name)
        if english:
            display_name = clean_name(english)
        else:
            display_name = clean_name(ogs_name)
    # Priority 3: Standard cleanup for Latin-script names
    else:
        display_name = clean_name(ogs_name)

    if ogs_id in _SLUG_OVERRIDES:
        slug = _SLUG_OVERRIDES[ogs_id]
    else:
        slug = generate_slug(display_name)

    curator = infer_curator(ogs_name)
    coll_type = infer_type(ogs_name, curator)

    puzzle_count = record.get("stats", {}).get("puzzle_count", 0)
    tier = record.get("quality_tier", "unvetted")
    schema_tier = _OGS_TIER_MAP.get(tier, "community")

    return {
        "slug": slug,
        "name": display_name,
        "description": (
            f"OGS community collection ({tier} tier, {puzzle_count} puzzles). "
            f"Imported from online-go.com."
        ),
        "curator": curator,
        "source": "ogs",
        "type": coll_type,
        "ordering": "source",
        "tier": schema_tier,
        "aliases": [ogs_name],
    }


# ============================================================================
# Bootstrap Logic
# ============================================================================

def bootstrap_collections(
    sorted_jsonl_path: Path,
    collections_json_path: Path,
    tiers: frozenset[str] = frozenset({"premier", "curated"}),
) -> tuple[list[dict[str, Any]], list[tuple[int, str, str]], list[tuple[int, str, str, str]]]:
    """Identify OGS collections needing new YenGo entries.

    Args:
        sorted_jsonl_path: Path to sorted JSONL.
        collections_json_path: Path to config/collections.json.
        tiers: Quality tiers to bootstrap (default: premier + curated).

    Returns:
        Tuple of:
        - new_entries: List of generated collection entry dicts
        - matched: List of (ogs_id, ogs_name, yengo_slug) for already-matched
        - skipped: List of (ogs_id, ogs_name, tier, reason) for skipped
    """
    # Load existing config
    with open(collections_json_path, encoding="utf-8") as f:
        existing_config = json.load(f)
    existing_collections = existing_config.get("collections", [])
    existing_slugs = {c["slug"] for c in existing_collections}

    # Collect all existing aliases for uniqueness check
    existing_aliases: set[str] = set()
    for coll in existing_collections:
        existing_aliases.add(coll["slug"])
        if coll.get("name"):
            existing_aliases.add(coll["name"])
        for alias in coll.get("aliases", []):
            existing_aliases.add(alias)

    # Load sorted JSONL
    _, ogs_collections = read_collections(sorted_jsonl_path)

    # Initialize matcher from existing collections
    matcher = CollectionMatcher(collections_json_path)

    matched: list[tuple[int, str, str]] = []
    new_entries: list[dict[str, Any]] = []
    skipped: list[tuple[int, str, str, str]] = []

    for record in ogs_collections:
        ogs_name = record["name"]
        ogs_id = record["id"]
        tier = record.get("quality_tier", "unvetted")

        # Skip username-only collections (no identifiable Go topic)
        if ogs_id in _SKIP_IDS:
            skipped.append((ogs_id, ogs_name, tier, "manual_skip"))
            continue

        # Try to match against existing YenGo slug
        slug = matcher.match(ogs_name)

        if slug:
            matched.append((ogs_id, ogs_name, slug))
            continue

        # Only bootstrap specified tiers
        if tier not in tiers:
            skipped.append((ogs_id, ogs_name, tier, "tier_too_low"))
            continue

        # Generate new collection entry
        entry = generate_collection_entry(record)

        # Validate: reject entries whose name still has non-Latin characters
        # (original was non-Latin but no override or extraction succeeded)
        if _NON_LATIN_RE.search(entry["name"]):
            skipped.append((ogs_id, ogs_name, tier, "non_english"))
            continue

        # Validate slug uniqueness
        if entry["slug"] in existing_slugs:
            skipped.append((ogs_id, ogs_name, tier, "slug_collision"))
            continue

        # Validate alias uniqueness
        if ogs_name in existing_aliases:
            skipped.append((ogs_id, ogs_name, tier, "alias_collision"))
            continue

        existing_slugs.add(entry["slug"])
        existing_aliases.add(ogs_name)
        new_entries.append(entry)

    return new_entries, matched, skipped


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Bootstrap new collection entries from OGS sorted JSONL",
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="Input sorted JSONL file (from sort_collections.py)",
    )
    parser.add_argument(
        "--collections", "-c",
        type=Path,
        default=None,
        help="Path to config/collections.json (default: auto-detect)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output collections JSON file (default: config/collections-proposed.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview proposed entries without writing",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Resolve paths
    project_root = get_project_root()

    input_path: Path = args.input
    if not input_path.is_absolute():
        input_path = project_root / input_path

    collections_path: Path = args.collections or (project_root / "config" / "collections.json")
    if not collections_path.is_absolute():
        collections_path = project_root / collections_path

    output_path: Path | None = args.output
    if output_path is None:
        output_path = project_root / "config" / "collections-proposed.json"
    elif not output_path.is_absolute():
        output_path = project_root / output_path

    logger.info("OGS Collections Bootstrap")
    logger.info("=" * 40)
    logger.info(f"Input:       {rel_path(input_path)}")
    logger.info(f"Collections: {rel_path(collections_path)}")
    logger.info(f"Output:      {rel_path(output_path)}")
    logger.info(f"Dry run:     {args.dry_run}")
    logger.info("")

    # Run bootstrap
    new_entries, matched, skipped = bootstrap_collections(
        sorted_jsonl_path=input_path,
        collections_json_path=collections_path,
    )

    # Log summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("BOOTSTRAP SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Already matched: {len(matched)}")
    logger.info(f"New entries:     {len(new_entries)}")
    logger.info(f"Skipped:         {len(skipped)}")
    logger.info("")

    if matched:
        logger.info("Matched collections:")
        for ogs_id, ogs_name, slug in matched[:10]:
            logger.info(f"  OGS #{ogs_id:<6} -> {slug:<40} ({ogs_name[:50]})")
        if len(matched) > 10:
            logger.info(f"  ... and {len(matched) - 10} more")
        logger.info("")

    if new_entries:
        logger.info("Proposed new entries:")
        for entry in new_entries:
            logger.info(
                f"  {entry['slug']:<40} type={entry['type']:<10} "
                f"curator={entry['curator']:<15} alias={entry['aliases'][0][:40]}"
            )
        logger.info("")

    if skipped:
        # Count by reason
        reason_counts: dict[str, int] = {}
        for _, _, _, reason in skipped:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        logger.info("Skipped breakdown:")
        for reason, count in sorted(reason_counts.items()):
            logger.info(f"  {reason}: {count}")
        logger.info("")

    if args.dry_run:
        logger.info("[DRY RUN] No output file written.")
        return 0

    if not new_entries:
        logger.info("No new entries to add. Output not written.")
        return 0

    # Write merged output
    with open(collections_path, encoding="utf-8") as f:
        existing_config = json.load(f)

    merged_collections = existing_config.get("collections", []) + new_entries
    output_config = {
        "_reference": existing_config.get("_reference", "docs/concepts/collections.md"),
        "version": "3.0",
        "collections": merged_collections,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_config, f, ensure_ascii=False, indent=2)
        f.write("\n")

    logger.info(f"Wrote {len(merged_collections)} collections to {rel_path(output_path)}")
    logger.info("Review and merge into config/collections.json when ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
