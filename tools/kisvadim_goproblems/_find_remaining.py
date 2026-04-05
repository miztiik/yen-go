#!/usr/bin/env python3
"""Extract bigrams/trigrams containing remaining characters."""
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

REMAINING = set("分力加戏比但地实常执做利担瞄时局必动均如包括破佳发可打第应撇路定材亦另成真作欲两步共紧自么因握智东西起为住保往由知进目筋事妄单弯理劫呼易显干式忆性方假双含屈服条直超及联沿以丢吴差任带别待乍")


def is_cjk(c):
    cp = ord(c)
    return 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0xF900 <= cp <= 0xFAFF


def extract_values(content):
    vals = []
    j = 0
    while j < len(content):
        if j < len(content) - 1 and content[j] in "CN" and content[j + 1] == "[":
            if j == 0 or not content[j - 1].isupper():
                j += 2
                vc = []
                while j < len(content):
                    if content[j] == "\\" and j + 1 < len(content):
                        j += 2
                    elif content[j] == "]":
                        break
                    else:
                        vc.append(content[j])
                        j += 1
                vals.append("".join(vc))
                if j < len(content):
                    j += 1
            else:
                j += 1
        else:
            j += 1
    return vals


def main():
    bigrams = Counter()
    trigrams = Counter()
    fourgrams = Counter()

    for i in range(143, 241):
        fn = f"{i:04d}.sgf"
        fp = os.path.join(DIR, fn)
        if not os.path.exists(fp):
            continue
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()
        for val in extract_values(content):
            for k in range(len(val) - 1):
                if is_cjk(val[k]) and is_cjk(val[k + 1]):
                    bigrams[val[k : k + 2]] += 1
            for k in range(len(val) - 2):
                if all(is_cjk(val[k + m]) for m in range(3)):
                    trigrams[val[k : k + 3]] += 1
            for k in range(len(val) - 3):
                if all(is_cjk(val[k + m]) for m in range(4)):
                    fourgrams[val[k : k + 4]] += 1

    print("=== BIGRAMS with remaining chars (top 100) ===")
    count = 0
    for bg, cnt in bigrams.most_common(500):
        if any(c in REMAINING for c in bg):
            print(f"{cnt:3d}  {bg}")
            count += 1
            if count >= 100:
                break

    print("\n=== TRIGRAMS with remaining chars (top 60) ===")
    count = 0
    for tg, cnt in trigrams.most_common(500):
        if any(c in REMAINING for c in tg):
            print(f"{cnt:3d}  {tg}")
            count += 1
            if count >= 60:
                break


if __name__ == "__main__":
    main()
