# Melee Gameplay Glossary for Frame Data Analysis

This document maps Melee gameplay terminology to the technical IDs and data
fields in Slippi replay frame data. Use it to translate natural language
questions into frame data queries.

## ID Systems

There are THREE separate numeric ID systems in .slp data:

| System | Where Used | Lookup |
|--------|-----------|--------|
| **Internal character ID** | `game.start.players[i].character` | `melee_tools.enums.CHARACTER_NAMES` |
| **External character ID** | `post.character` (per-frame) | `melee_tools.enums.CHARACTER_NAMES_EXTERNAL` |
| **Action state ID** | `post.state` (per-frame) | `melee_tools.action_states.ACTION_STATES` |
| **Move ID** | `post.last_attack_landed` | `melee_tools.moves.MOVE_NAMES` |

Action state IDs and move IDs are DIFFERENT numbering systems.
- Action state = what animation/state a character is in (383 shared states)
- Move ID = which attack was used (used in `last_attack_landed` and `last_hit_by` context)

## Gameplay Concepts → Frame Data

### Attacks

"Forward smash" / "fsmash" → move ID 10, action states {58, 59, 60, 61, 62, 351}
"Forward air" / "fair" → move ID 14, action states {66}
"Back air" / "bair" → move ID 15, action states {67}
"Down air" / "dair" / "spike" → move ID 17, action states {69}
"Grab" → move ID not applicable (it's a state), action states {212, 213, 214, 215}
"Forward throw" / "fthrow" → move ID 53, action states {219}
"Back throw" / "bthrow" → move ID 54, action states {220}
"Up throw" / "uthrow" → move ID 55, action states {221}
"Down throw" / "dthrow" → move ID 56, action states {222}

For a full list, see `melee_tools.moves.MOVE_NAMES` and
`melee_tools.action_states.ACTION_STATE_CATEGORIES`.

### Character-Specific Specials

Specials are move IDs 18-21 (Neutral B, Side B, Up B, Down B) but the actual
move differs per character:

| Move ID | Fox | Falco | Marth | Sheik | C. Falcon | Jigglypuff | Peach |
|---------|-----|-------|-------|-------|-----------|------------|-------|
| 18 (Neutral B) | Blaster | Blaster | Shield Breaker | Needles | Falcon Punch | Rollout | Toad |
| 19 (Side B) | Fox Illusion | Phantasm | Dancing Blade | Chain | Raptor Boost | Pound | Peach Bomber |
| 20 (Up B) | Fire Fox | Fire Bird | Dolphin Slash | Vanish | Falcon Dive | Sing | Parasol |
| 21 (Down B) | Reflector (Shine) | Reflector | Counter | Transform | Falcon Kick | Rest | Turnip |

### Hitstun / Getting Hit

"Got hit" / "in hitstun" → `ACTION_STATE_CATEGORIES['damage']` (states 75-91 + 357)
"Knockback" → states 87-91 (DAMAGE_FLY variants)
"Tumble" → state 38

### Tech Options (after knockdown)

When a player is knocked down, they can:
- "Tech in place" → state 199
- "Tech roll forward" → state 200
- "Tech roll backward" → state 201
- "Missed tech" / "no tech" → states 183-198 (face up: 183-190, face down: 191-198)
- "Getup attack" → states 187 (face up) or 195 (face down)
- "Wall tech" → state 202
- "Wall tech jump" → state 203
- "Ceiling tech" → state 204

All tech states: `ACTION_STATE_CATEGORIES['tech']`
All missed tech: `ACTION_STATE_CATEGORIES['missed_tech_up']` | `ACTION_STATE_CATEGORIES['missed_tech_down']`

### Defensive Options

- "Shield" / "shielding" → `ACTION_STATE_CATEGORIES['shield']` (178-180, 349)
- "Roll" → `ACTION_STATE_CATEGORIES['roll']` (233=forward, 234=backward)
- "Spot dodge" → `ACTION_STATE_CATEGORIES['spotdodge']` (235, 350)
- "Air dodge" / "wavedash" → state 236 (ESCAPE_AIR)
- "Powershield" → state 182

### Movement

- "Dash" → state 20
- "Run" → state 21
- "Wavedash" → jumpsquat (24) → airdodge (236) → landing slide. The airdodge
  into ground is the key indicator.
- "Dashdance" → rapid alternation of state 20 (DASH) with direction changes
- "Platform drop" → state 244

### Ledge / Edge

- "On ledge" / "ledge hang" → `ACTION_STATE_CATEGORIES['ledge_hang']` (253, 362, 363)
- "Ledge getup" → states 254, 255
- "Ledge attack" → states 256, 257
- "Ledge roll" → states 258, 259
- "Ledge jump" → states 260-263

### Death / Kill

A **kill** is detected by `stocks` decreasing between consecutive frames.
- The frame BEFORE the stock drop has: `last_attack_landed` (move ID of the
  killing attack) and `last_hit_by` (port of the attacker).
- The frame AFTER the stock drop has: `state` in DEAD_* states (0-10) which
  encodes the **blastzone direction**.

Blastzone mapping:
- `DEAD_DOWN` (0) → bottom blastzone (spiked, fell too far)
- `DEAD_LEFT` (1) → left blastzone
- `DEAD_RIGHT` (2) → right blastzone
- `DEAD_UP` / `DEAD_UP_STAR` / `DEAD_UP_FALL*` (3-10) → top blastzone

### Respawn

After dying, a player enters:
- state 12 (REBIRTH) — descending on revival platform
- state 13 (REBIRTH_WAIT) — waiting on revival platform

Use `ACTION_STATE_CATEGORIES['spawn']` to detect respawn.

### Game Outcome

- `placement == 0` → winner (or winning team member)
- `end_method == 'RESOLVED'` → teams game ended
- `end_method == 'GAME'` → 1v1 or FFA ended
- `end_method == 'NO_CONTEST'` → someone quit (LRAS)

## Port Mapping Gotcha

`last_hit_by` uses **actual port numbers** (0-3), not sequential player indices.
In a 1v1 on ports 1 and 3, `last_hit_by` will be 1 or 3, not 0 or 1.
Use the port-to-player-index mapping from `game.start.players`.

## Null Frames

After a player loses their last stock, their frame data fills with `None`/`NaN`.
Always filter for non-null values when computing stats.
