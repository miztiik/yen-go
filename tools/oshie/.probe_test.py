"""Thorough probe: 5 tests (V1 vs V2 comparison + 3 new techniques)."""
import json, time, http.client, sys

def run_test(name, system_msg, user_msg, max_tokens=8192):
    conn = http.client.HTTPConnection("127.0.0.1", 8080, timeout=600)
    payload = json.dumps({
        "model": "gemma-4-26B-A4B-it-Q8_0.gguf",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.5,
        "stream": True
    })
    conn.request("POST", "/v1/chat/completions", body=payload, headers={"Content-Type": "application/json"})
    response = conn.getresponse()
    if response.status != 200:
        err = response.read().decode("utf-8", errors="replace")
        print(f"  ERROR: HTTP {response.status}: {err[:300]}")
        return None

    r_tok = 0; c_tok = 0; r_text = []; c_text = []
    start = time.time(); last_rpt = start; buf = ""; fr = None

    for chunk in response:
        buf += chunk.decode("utf-8", errors="replace")
        while "\n\n" in buf:
            ev, buf = buf.split("\n\n", 1)
            for ln in ev.strip().split("\n"):
                if not ln.startswith("data: "): continue
                ds = ln[6:]
                if ds.strip() == "[DONE]": fr = "done"; continue
                try: d = json.loads(ds)
                except: continue
                ch = d.get("choices", [{}])[0]
                delta = ch.get("delta", {})
                if ch.get("finish_reason"): fr = ch["finish_reason"]
                if delta.get("reasoning_content"):
                    r_tok += 1; r_text.append(delta["reasoning_content"])
                if delta.get("content"):
                    c_tok += 1; c_text.append(delta["content"])
                now = time.time()
                if now - last_rpt > 15:
                    el = now - start
                    ph = "THINK" if c_tok == 0 else "OUT"
                    print(f"  [{el:5.1f}s] {ph} | t:{r_tok} c:{c_tok} | {(r_tok+c_tok)/el:.0f} t/s", flush=True)
                    last_rpt = now
    conn.close()
    el = time.time() - start
    content = "".join(c_text)
    # Strip markdown fences
    if "```json" in content:
        content = content.split("```json")[-1].split("```")[0].strip()
    elif "```" in content:
        parts = content.split("```")
        if len(parts) >= 3:
            content = parts[1].strip()
    return {"name": name, "elapsed": el, "r_tok": r_tok, "c_tok": c_tok,
            "finish": fr, "content": content, "reasoning_tail": "".join(r_text)[-300:]}


SYS_V1 = (
    "You are a professional Go (Baduk/Weiqi) teacher generating teaching comments for tsumego. "
    "Respond with a JSON object:\n"
    '{"teaching_comments": {"correct_comment": "...", "wrong_comments": {"<sgf_coord>": "..."}, '
    '"summary": "..."}, "hints": ["tier1: technique name only", "tier2: reasoning without answer", '
    '"tier3: coordinate with {!xy}"]}\n\n'
    "Voice rules:\n"
    "1. Board speaks first -- describe consequence, not student error.\n"
    "2. Action then consequence with double-dash.\n"
    "3. Verb-forward -- drop leading articles.\n"
    "4. 15-word cap for wrong-move explanation.\n"
    "5. Warmth only for near-misses."
)

SYS_V2 = (
    "You are a professional Go (Baduk/Weiqi) teacher generating teaching comments for tsumego. "
    "Respond with a JSON object:\n"
    '{"teaching_comments": {"correct_comment": "...", "wrong_comments": {"<sgf_coord>": "..."}, '
    '"summary": "..."}, "hints": ["tier1: technique name only", "tier2: reasoning without answer", '
    '"tier3: coordinate with {!xy}"]}\n\n'
    "Voice rules:\n"
    "1. Board speaks first -- describe consequence, not student error.\n"
    "2. Action then consequence with double-dash.\n"
    "3. Verb-forward -- drop leading articles.\n"
    "4. 15-word cap for wrong-move explanation.\n"
    "5. Warmth only for near-misses.\n\n"
    "Teaching depth rules:\n"
    "6. For each wrong move, state the concrete board consequence in one move sequence "
    '(e.g. "after F5, White G4 escapes in sente").\n'
    "7. For the correct move, name the resulting dead shape, capture, or position outcome.\n"
    "8. For beginners, explain physical board mechanics step by step. "
    "For advanced players, name the principle concisely."
)

SNAP_PROMPT = (
    "Board: 9x9, Black to play\n"
    "Difficulty: Beginner\n"
    "Technique: Snapback\n\n"
    "Black stones: E5, F5, F4, G4\n"
    "White stones: E4, F3, G3, G5\n"
    "White has just captured at G4. Black can recapture via snapback.\n\n"
    "Correct move: G4 (SGF: gd) -- recaptures two White stones via snapback\n"
    "Wrong move 1: H4 (SGF: hd) -- does not recapture, White keeps the stones\n"
    "Wrong move 2: F6 (SGF: ff) -- defensive, misses the snapback opportunity\n\n"
    "Explain why G4 works as a snapback and why H4/F6 fail. Provide 3-tier hints."
)

CONNECT_DIE_PROMPT = (
    "Board: 19x19, Black to play\n"
    "Difficulty: Intermediate\n"
    "Technique: Connect-and-die (uttegaeshi)\n\n"
    "Black stones: C2, D2, E2, C1, E1\n"
    "White stones: D1, D3, C3, E3\n"
    "White stone at D1 looks alive between Black stones. But if White connects, the whole group dies.\n\n"
    "Correct move: D1 area -- force White to connect, creating connect-and-die\n"
    "Wrong move 1: F1 (SGF: fa) -- outside the shape, White lives easily\n"
    "Wrong move 2: B1 (SGF: ba) -- wrong side, White escapes via E side\n\n"
    "The key is that White connecting creates a dead shape. Explain this technique. Provide 3-tier hints."
)

DOUBLE_ATARI_PROMPT = (
    "Board: 19x19, Black to play\n"
    "Difficulty: Beginner\n"
    "Technique: Double atari\n\n"
    "Black stones: D4, F4, E3\n"
    "White stones: E4, E5\n"
    "Black can play a double atari -- one move that puts two White groups in atari simultaneously.\n\n"
    "Correct move: E6 (SGF: ef) -- double atari on E5 and creates threat on E4 group\n"
    "Wrong move 1: D5 (SGF: de) -- only ataris one stone, White saves the other\n"
    "Wrong move 2: F5 (SGF: fe) -- only ataris one stone from wrong direction\n\n"
    "Explain the double atari concept. Why E6 catches both while D5/F5 only threaten one. Provide 3-tier hints."
)

THROWIN_PROMPT = (
    "Board: 19x19, Black to play\n"
    "Difficulty: Dan (1d-3d)\n"
    "Technique: Throw-in (horikomi), shortage of liberties (damezumari)\n\n"
    "Black stones: R17, S17, R16, S15, R14\n"
    "White stones: Q17, Q16, Q15, R15, S16\n"
    "White group looks connected but has a liberty shortage. A throw-in creates damezumari.\n\n"
    "Correct move: S18 (SGF: sr) -- throw-in sacrifices one stone, White recaptures but ends in damezumari\n"
    "Wrong move 1: T16 (SGF: tp) -- crude push, White connects safely with one extra liberty\n"
    "Wrong move 2: Q18 (SGF: qr) -- wrong direction, White captures and lives\n\n"
    "Explain the throw-in mechanism and why it creates damezumari. Provide 3-tier hints."
)

PUZZLES = [
    {"name": "T1-V1: Snapback beginner (original)", "sys": SYS_V1, "prompt": SNAP_PROMPT},
    {"name": "T1-V2: Snapback beginner (improved)", "sys": SYS_V2, "prompt": SNAP_PROMPT},
    {"name": "T2-V2: Connect-and-die intermediate", "sys": SYS_V2, "prompt": CONNECT_DIE_PROMPT},
    {"name": "T3-V2: Double atari beginner", "sys": SYS_V2, "prompt": DOUBLE_ATARI_PROMPT},
    {"name": "T4-V2: Throw-in dan level", "sys": SYS_V2, "prompt": THROWIN_PROMPT},
]

print("=" * 70)
print("THOROUGH PROBE: 5 tests (V1 vs V2 comparison + 3 new techniques)")
print("=" * 70)

results = []
for i, p in enumerate(PUZZLES):
    print(f"\n--- {i+1}/5: {p['name']} ---")
    r = run_test(p["name"], p["sys"], p["prompt"])
    if r:
        results.append(r)
        print(f"  DONE: {r['elapsed']:.0f}s | think:{r['r_tok']} out:{r['c_tok']} | finish:{r['finish']}")
        print(f"  --- OUTPUT ---")
        print(r["content"][:800])
        if len(r["content"]) > 800: print("  ...")
        print(f"  --- END ---")
    else:
        results.append({"name": p["name"], "error": True})
        print(f"  FAILED")

print(f"\n{'='*70}")
print("SUMMARY TABLE")
print(f"{'='*70}")
print(f"{'Test':<45} {'Time':>5} {'Think':>6} {'Out':>5} {'Status'}")
print("-" * 70)
for r in results:
    if r.get("error"):
        print(f"{r['name']:<45} {'FAIL':>5}")
    else:
        status = "EMPTY" if r["c_tok"] == 0 else "OK"
        print(f"{r['name']:<45} {r['elapsed']:>4.0f}s {r['r_tok']:>6} {r['c_tok']:>5} {status}")

with open("c:/Users/kumarsnaveen/Downloads/NawiN/personal/gitrepos/yen-go/tools/oshie/.test_results_v2.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to tools/oshie/.test_results_v2.json")
