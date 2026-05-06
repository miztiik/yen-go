# yengo_dashboard color palette

> Single source of truth for cockpit semantic colors. Any new UI element MUST
> reuse one of these tokens — do not pick fresh hexes for "this one button".
> CI grep guards reference this file when checking for stray colors.

---

## Why a fixed palette

The cockpit shows a small number of operationally meaningful states:
*healthy*, *active*, *just-completed*, *steady-ok*, *warned*, *failed*. Each
has **exactly one** color and **exactly one** glyph. Operators learn the
mapping in the first session and never have to relearn it.

When a state's meaning is genuinely new (not a synonym for an existing
state), add a row to this file in the same commit as the UI change. Do
not introduce ad-hoc shades.

---

## Semantic tokens (2026-05 refresh)

| State / role           | Tailwind text       | Tailwind bg          | Tailwind ring          | Glyph | Used for                                                   |
| ---------------------- | ------------------- | -------------------- | ---------------------- | ----- | ---------------------------------------------------------- |
| **neutral / chrome**   | `text-slate-300`    | `bg-slate-900`       | `ring-slate-800`       | —     | Frames, surfaces, body chrome                              |
| **secondary text**     | `text-slate-400`    | —                    | —                      | —     | Secondary copy (labels, captions, hints)                   |
| **info**               | `text-sky-300`      | `bg-sky-500/10`      | `ring-sky-500/30`      | `▲`   | Static notices, links, informational badges                |
| **running**            | `text-teal-300`     | `bg-teal-500/15`     | `ring-teal-400/40`     | `▶`   | In-flight subprocess; **must** carry `data-pulse="true"`   |
| **success-fresh**      | `text-lime-300`     | `bg-lime-500/10`     | `ring-lime-500/30`     | `✓`   | Just-completed runs, "look here" success in History/toasts |
| **success-steady**     | `text-emerald-300`  | `bg-emerald-500/10`  | `ring-emerald-500/30`  | `✓`   | Steady-state ok (`System · healthy`, healthy adapter rows) |
| **warning**            | `text-orange-300`   | `bg-orange-500/10`   | `ring-orange-500/30`   | `!`   | Lock held, dry-run notice, throttle hints                  |
| **failure**            | `text-rose-300`     | `bg-rose-500/10`     | `ring-rose-500/30`     | `✕`   | Failed run, ok=false CLI exits, 4xx/5xx                    |
| **destructive**        | `text-rose-300`     | `bg-rose-500/10`     | `ring-rose-500/30`     | `✕`   | Reserved for buttons that mutate or delete                 |
| **stale**              | `text-slate-500`    | `bg-slate-900/60`    | `ring-slate-700`       | `~`   | Failed health check, overdue poll, dependent data          |
| **muted / disabled**   | `text-slate-500`    | `bg-slate-800/50`    | `ring-slate-800`       | `○`   | Disabled adapter, idle controls                            |
| **stdout (log)**       | `text-slate-200`    | `bg-slate-950`       | —                      | —     | Log line stdout body                                       |
| **stderr (log)**       | `text-rose-300`     | `bg-slate-950`       | —                      | —     | Log line stderr body                                       |

### What changed in this refresh (2026-05-05 → 2026-05)

1. **`running` swapped from sky → teal.** Sky reads as "info / link" in every
   modern dashboard idiom. Teal is the `htop`/`btop`/process-monitor signal
   for "live activity," and it doesn't compete with `info` chips. AA on
   `slate-900` confirmed (text-teal-300 ≈ 7.1:1).
2. **Two-tier success: `success-fresh` (lime) and `success-steady` (emerald).**
   Lime says *"this just completed — look at me."* Emerald says *"steady
   state, all good, no action needed."* The History tab uses lime for the
   most recent successful run row; the System pill stays emerald because
   "healthy" is a steady condition, not an event. This adds hierarchy to
   what was previously a single calm-success treatment.
3. **`warning` swapped from amber → orange.** Amber-300 sits ~50° from
   lime-300 in HSV; deutan/protan operators (~5% of men) report confusion.
   Orange-300 shifts the hue another ~30° toward red and reads more
   urgent without entering rose territory.
4. **Body copy promoted slate-400 → slate-300.** The previous slate-400
   on slate-950 panels measured ~3.8:1 (fails AA for body). slate-300 on
   slate-950 ≈ 9.4:1. **Secondary** copy is the new slate-400 role;
   labels remain slate-500.
5. **Glyph set extended** with `▶` (running, replaces `▲`). The triangle-
   right reads "play / in flight" universally. `▲` is now reserved for
   `info` only.

### Intensity gradient (deliberate)

Read top-to-bottom:

```
neutral  <  info  <  running  <  success-steady  <  success-fresh  <  warning  <  failure / destructive
   (ambient)        (calm)        (steady ok)       (event ok)       (attention)      (alarm)
```

The cockpit deliberately keeps **steady success calm**. If "ok" is as loud as
"failure," the eye learns to ignore the alarm states by association. Use
`bg-{hue}-500/10 ring-{hue}-500/30` for everything except `running`
(slightly louder via `/15` + `ring-{hue}-400/40 + data-pulse`).

Hex equivalents (Tailwind v3 defaults — do not use these directly in code,
they're listed here for designer reference):

- `slate-300` `#cbd5e1` · `slate-400` `#94a3b8` · `slate-500` `#64748b` ·
  `slate-700` `#334155` · `slate-800` `#1e293b` · `slate-900` `#0f172a` ·
  `slate-950` `#020617`
- `sky-300` `#7dd3fc` · `sky-500` `#0ea5e9`
- `teal-300` `#5eead4` · `teal-400` `#2dd4bf` · `teal-500` `#14b8a6`
- `lime-300` `#bef264` · `lime-500` `#84cc16`
- `emerald-300` `#6ee7b7` · `emerald-500` `#10b981`
- `orange-300` `#fdba74` · `orange-500` `#f97316`
- `rose-300` `#fda4af` · `rose-500` `#f43f5e`

---

## Why color + glyph (always together)

Every status is encoded **both** by color and by a Unicode glyph. This is
not decorative — it's so the cockpit remains usable for:

- Operators with red/green color vision deficiency (deuteranopia /
  protanopia ≈ 8% of men).
- Screenshots in light terminals where dark-on-dark loses contrast.
- High-contrast OS themes that override CSS colors.

Glyph set: `○ ✓ ✕ ▲ ▶ ! ~` — picked because they remain visually distinct
in sub-pixel monospace rendering. Do not substitute emojis (they break
copy-paste, screen readers, and the "no emojis in production UI" rule
from `CLAUDE.md`). This rule applies to **CLI stdout** that the cockpit
streams too — the `🔍` emoji that landed in `cmd_clean` caused a real
`UnicodeEncodeError` on Windows console code page `cp1252` and crashed
the dry-run. The runner now wraps subprocess output with `errors="replace"`
as a belt-and-braces guard, but CLI authors must not introduce emojis in
the first place.

---

## Surface hierarchy (dark mode)

The cockpit ships in dark mode by default — terminal-adjacent operators
are usually in dark IDEs. Three surface tiers compose the layout:

| Tier        | Class                                            | Purpose                              |
| ----------- | ------------------------------------------------ | ------------------------------------ |
| **App bg**  | `bg-slate-950`                                   | Page background; never used for text |
| **Panel**   | `bg-slate-900 border border-slate-800`           | Cards, tabs, tables, modals          |
| **Inset**   | `bg-slate-950 border border-slate-800`           | Log panel, code blocks, JSON viewers |

Body copy is `text-slate-300`; secondary copy is `text-slate-400`; labels
are `text-slate-500 uppercase tracking-wider text-xs`. Headers are white
(H1) or `text-slate-200` (H2/H3) — one tonal step from body keeps the
hierarchy tight.

---

## What NOT to use

- **No `red-*`, `green-*`, `blue-*`, `yellow-*`** — use the semantic
  rose/emerald/lime/sky/teal/orange tokens above so a future palette
  swap touches one file.
- **No `amber-*`** — replaced by `orange-*` in the 2026-05 refresh
  (colorblind separation from lime). Existing amber references in
  `styles.css` / `app.js` were swept in the same commit; do not
  reintroduce.
- **No raw hex codes** in `app.js`, `index.html`, or `styles.css`. The
  only exceptions are the log-panel rules in `styles.css` that need
  values Tailwind utilities can't express (those are listed in
  the Surface table above and must match these tokens).
- **No emojis as status icons** (`✅ ❌ ⚠️ 🔴`) — see "Why color + glyph".
- **No light-mode-only colors** without a dark-mode counterpart. The
  cockpit is a single-theme app today; if a future "light mode for
  daytime ops" lands, every token here gets a light counterpart in
  one PR.

---

## Adding a new status

1. Confirm the new state is genuinely distinct from the seven above.
   "Loading" is not new — it's `info / running`. "Partially succeeded"
   is not new — pick one of `success-fresh` (with a count) or `warning`
   (with a partial-failure count) and stay consistent.
2. Pick a Tailwind 300/500 pair from the same hue family as the closest
   existing token (so the palette stays harmonious).
3. Pick a glyph that's visually distinct from `○ ✓ ✕ ▲ ▶ ! ~` at 12 px
   monospace.
4. Add a row to the Semantic tokens table above and reference the token
   from the UI change in the same commit.
5. Update the CI grep guard if the guard explicitly enumerates allowed
   colors (search `tools/yengo_dashboard/` for any pattern that pins the list).
