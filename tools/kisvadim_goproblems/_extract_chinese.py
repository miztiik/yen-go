#!/usr/bin/env python3
"""Extract all unique Chinese characters and phrases from Shokyuu SGF files."""
import re
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..",
    "external-sources", "kisvadim-goproblems",
    "GO SEIGEN Tsumego Collection 1 - Shokyuu",
)


def is_cjk(c):
    cp = ord(c)
    return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
            or 0xF900 <= cp <= 0xFAFF)


def extract_properties(content):
    """Extract C[] and N[] property values from SGF content."""
    values = []
    j = 0
    while j < len(content):
        if j < len(content) - 1 and content[j] in "CN" and content[j + 1] == "[":
            if j == 0 or not content[j - 1].isupper():
                prop = content[j]
                j += 2
                val_chars = []
                while j < len(content):
                    if content[j] == "\\" and j + 1 < len(content):
                        val_chars.append(content[j : j + 2])
                        j += 2
                    elif content[j] == "]":
                        break
                    else:
                        val_chars.append(content[j])
                        j += 1
                val = "".join(val_chars)
                values.append((prop, val))
                if j < len(content):
                    j += 1
            else:
                j += 1
        else:
            j += 1
    return values


def main():
    all_chars = set()
    all_words = []

    for i in range(143, 241):
        fn = f"{i:04d}.sgf"
        fp = os.path.join(DIR, fn)
        if not os.path.exists(fp):
            continue
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()

        for prop, val in extract_properties(content):
            for c in val:
                if is_cjk(c):
                    all_chars.add(c)
            for seq in re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]+", val):
                all_words.append(seq)

    print(f"Total unique CJK chars: {len(all_chars)}")
    print("".join(sorted(all_chars)))
    print()
    word_counts = Counter(all_words)
    print("=== MOST COMMON CJK SEQUENCES (top 400) ===")
    for word, count in word_counts.most_common(400):
        print(f"{count:3d}  {word}")


if __name__ == "__main__":
    main()
