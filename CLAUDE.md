# melee-tools

Python library for analyzing Super Smash Bros. Melee `.slp` replay files using `peppi-py`.

Always work inside the project venv. Before running any Python or pytest commands in Bash, activate it:

```bash
source .venv/bin/activate
```

---

## Documentation

Read these docs before writing analysis code — they contain critical mappings between
Melee terminology and the library's data model:

- **`docs/melee_guide.md`** — Comprehensive Melee primer for AI agents. Covers game mechanics,
  competitive concepts, character archetypes, techniques, and how natural language maps to frame data.
- **`docs/glossary.md`** — Maps Melee gameplay terms to technical IDs (action states, move IDs,
  character IDs). Essential for translating questions like "how often do I grab" into correct field lookups.
- **`docs/cookbook.md`** — Worked examples translating natural language questions into melee-tools code.
  Shows common import patterns and analysis workflows.
- **`docs/example_queries.md`** — 10+ research questions with full code and sample findings. Good
  reference for what the library can answer and how to structure analysis.
- **`docs/clip_query_guide.md`** — Reference for the clip finder API (`find_move_sequences`,
  `find_confirmed_events`, `find_edgeguards`, etc.) and Dolphin export workflow.

## Analysis Scripts

Example analysis scripts live in `analysis/`. These demonstrate real-world usage patterns:

- `analysis/common.py` — Shared constants (ROOT, TAG) and imports
- `analysis/ten_questions.py` — 10-question self-assessment using library functions
- `analysis/insights.py` — Multi-character population-level analysis
- `analysis/tech_chases.py` — Custom tech option scanner (workaround for `find_tech_chases()` bug)
- `analysis/ledgedash_analysis.py` — Ledgedash detection and analysis
- `analysis/fox_training.py` — Fox-specific training analysis
- `analysis/positions.py` — Stage position heatmaps
- `analysis/annotate_slides.py` — Google Slides annotation with analysis results

---

## Default Datasource

**Use `replays/training_data/` by default for all analysis.**

- 95,000+ community `.slp` files — broad sample across skill levels and matchups
- Sample 1000 games randomly (seed=42) unless the user requests otherwise
- `replays/sample/` — 100-game subset of training_data (checked into git) for tests and quick iteration
- Only use `replays/Replays Onion-Desktop/` (EG#0 personal replays, ~65 games) when the user explicitly
  asks for player-specific data (e.g. "my games", "EG#0", "my Sheik", etc.)

## Red Flags — Stop and Verify Before Reporting

If any of these appear in analysis results, assume a processing bug before reporting findings:

- A very common in-game action shows **0 occurrences** (e.g. 0 successful techs, 0 grabs, 0 aerials)
- A stat is 100% or 0% for something with natural variance
- Character names look wrong relative to the filename
- Sample size is much smaller than expected given the dataset

Always validate with a quick sanity check on a few files before presenting results.

## Training Data — peppi_py Compatibility

`extract_frames()` **fails on training_data files** (older Slippi format, AttributeError on null_count).
For training_data scans, read peppi_py directly:

```python
from peppi_py import read_slippi
game = read_slippi(str(fpath))  # catch with BaseException, not just Exception
```

- Use `character_name(int(player.character))` for `game.start.players[i]` — these are **internal** IDs
- **Never** use `character_name_external()` with start metadata; that's for post-frame character column
- Extract fields with `_safe_np(arr)` helper that handles None arrays (missing in older formats)
- Catch parse errors with `except BaseException` — Rust panics don't always surface as `Exception`

## Known Library Bugs (Fixed)

- ~~`_iter_1v1_games()` character filter was case-sensitive~~ — **Fixed 2026-02-25.** Now uses `.lower()`
  comparison. Pass any case (`"sheik"`, `"Sheik"`, `"SHEIK"`) and it will match.
- ~~`ledge_options()` classified all ledgedashes as `drop_jump`~~ — **Fixed 2026-02-25.** Was checking for
  JUMPSQUAT(24) instead of JUMP_AERIAL(27/28). Added regrab detection (DJ → fall → ledge grab).

## Known Library Bugs (Open)

- `find_tech_chases()` in `clips.py` only detects **missed tech bounces** (states 183/191). It completely
  misses successful techs (states 199/200/201), which enter without a prior bounce state. Do NOT use
  `find_tech_chases()` for full tech option distribution — write a custom scanner instead (see
  `analysis/tech_chases.py` for the correct pattern covering both paths).
