# Melee Gameplay Glossary for Frame Data Analysis

This document maps Melee gameplay terminology to the technical IDs and data
fields in Slippi replay frame data. Use it to translate natural language
questions into frame data queries.

For a comprehensive explanation of Melee mechanics and concepts, see
`melee_guide.md` in this directory.

---

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

---

## Attacks → Frame Data

### Standard Attacks

| Common Name(s) | Move ID | Action States | Notes |
|----------------|---------|---------------|-------|
| Jab / jab 1 | 2 | 44, 45, 46 | First hit of jab combo |
| Dash attack | 6 | 50, 51 | Attack out of dash/run |
| Forward tilt / ftilt | 7 | 52, 53, 54 | Directional variants (high/mid/low) |
| Up tilt / utilt | 8 | 55, 56, 57 | |
| Down tilt / dtilt | 9 | 48, 49 | |
| Forward smash / fsmash | 10 | 58, 59, 60, 61, 62, 351 | Includes charge hold states |
| Up smash / usmash | 11 | 63, 64, 65, 352 | |
| Down smash / dsmash | 12 | 55, 56, 57, 353 | |
| Nair / neutral air | 13 | 65 | |
| Fair / forward air | 14 | 66 | |
| Bair / back air | 15 | 67 | |
| Uair / up air | 16 | 68 | |
| Dair / down air | 17 | 69 | Can be a meteor/spike |
| Grab (standing) | — | 212 | move ID not applicable |
| Grab (dash) | — | 213 | |
| Grab (pivot) | — | 214 | |
| Forward throw / fthrow | 53 | 219 | |
| Back throw / bthrow | 54 | 220 | |
| Up throw / uthrow | 55 | 221 | |
| Down throw / dthrow | 56 | 222 | |

### Special Moves (Character-Dependent)

Specials are move IDs 18-21. The actual attack differs per character:

| Move ID | Fox | Falco | Marth | Sheik | C. Falcon | Jigglypuff | Peach |
|---------|-----|-------|-------|-------|-----------|------------|-------|
| 18 (Neutral B) | Blaster | Blaster | Shield Breaker | Needles | Falcon Punch | Rollout | Toad |
| 19 (Side B) | Fox Illusion | Phantasm | Dancing Blade | Chain | Raptor Boost | Pound | Peach Bomber |
| 20 (Up B) | Fire Fox | Fire Bird | Dolphin Slash | Vanish | Falcon Dive | Sing | Parasol |
| 21 (Down B) | Reflector (Shine) | Reflector | Counter | Transform | Falcon Kick | Rest | Turnip |

### Character-Specific Move Names

These nicknames appear constantly in community discussion:

| Nickname | Character | Actual Move | Move ID / States |
|----------|-----------|-------------|-----------------|
| **Shine** | Fox, Falco | Down-B (Reflector) | move ID 21 |
| **Knee** / **Knee of Justice** | Falcon | Forward air (sweetspot) | move ID 14 |
| **Weak knee** | Falcon | Forward air (sourspot) | move ID 14, weaker hitbox |
| **Stomp** | Falcon | Down air | move ID 17 |
| **Gentleman** | Falcon | Jab 1-2-3 (not rapid jab) | move ID 2, states 44-46 |
| **Nipple spike** | Falcon | Up air (specific hitbox) | move ID 16, spikes |
| **Tipper** | Marth | Any sword move hitting with tip | Same move IDs, more KB |
| **Rest** | Jigglypuff | Down-B | move ID 21 |
| **Wall of Pain** | Jigglypuff | Repeated bairs offstage | move ID 15, repeated |
| **Pillar** | Falco | Shine → dair → shine → dair chain | move IDs 21, 17 alternating |
| **Drill** | Fox | Down air (multi-hit) | move ID 17 |

---

## Game States → Frame Data

### Hitstun / Getting Hit

| Concept | Frame Data | Notes |
|---------|-----------|-------|
| In hitstun | `ACTION_STATE_CATEGORIES['damage']` (states 75-91, 357) | Cannot act |
| Knockback flying | States 87-91 (DAMAGE_FLY variants) | Sent flying from strong hit |
| Tumble | State 38 | Spinning in air after hitstun, can act |
| Hitlag / freeze frames | Occurs on hit, not directly a state | Both players freeze briefly |

### Tech Options (After Knockdown)

| Option | State(s) | Community Name |
|--------|----------|---------------|
| Tech in place | 199 | "tech in place", "neutral tech" |
| Tech roll forward | 200 | "tech roll", "tech forward" |
| Tech roll backward | 201 | "tech roll back", "tech behind" |
| Missed tech (face up) | 183-190 | "no tech", "missed tech" |
| Missed tech (face down) | 191-198 | "no tech", "missed tech" |
| Getup attack (face up) | 187 | "getup attack" |
| Getup attack (face down) | 195 | "getup attack" |
| Wall tech | 202 | "wall tech" |
| Wall tech jump | 203 | "wall tech jump" |
| Ceiling tech | 204 | "ceiling tech" |
| Amsah tech | — | Survival DI + tech → slide to ledge. Look for tech near edge + ledge grab |

Category lookups:
- All tech: `ACTION_STATE_CATEGORIES['tech']`
- Missed tech face up: `ACTION_STATE_CATEGORIES['missed_tech_up']`
- Missed tech face down: `ACTION_STATE_CATEGORIES['missed_tech_down']`

### Shield and Defensive Options

| Option | State(s) | Notes |
|--------|----------|-------|
| Shield | 178-180, 349 | `ACTION_STATE_CATEGORIES['shield']` |
| Powershield | 182 | Perfect shield timing (2 frame window) |
| Roll forward | 233 | `ACTION_STATE_CATEGORIES['roll']` |
| Roll backward | 234 | |
| Spot dodge | 235, 350 | `ACTION_STATE_CATEGORIES['spotdodge']` |
| Air dodge | 236 | ESCAPE_AIR — also used for wavedash |

### Movement States

| Action | State(s) | Notes |
|--------|----------|-------|
| Idle / standing | 14 (WAIT) | Neutral stance |
| Walk | 16-19 | Slow, full action availability |
| Dash | 20 | Initial burst; can reverse (dashdance) |
| Run | 21 | Full speed; limited reversal options |
| Jumpsquat | 24 | Pre-jump crouch (3-6 frames by character) |
| Fall | 30-35 | Airborne, including fast-fall variants |
| Crouch | 39-41 | Enables CC, dtilt, crawl |
| Landing | 23 | Normal landing, 4 frames |
| Platform drop | 244 | Drop through platform |
| Wavedash | 24 → 236 → 23 with x-velocity | Jumpsquat → airdodge → slide |
| Dashdance | Repeated state 20 | Alternating dash direction |

### Ledge States

| Action | State(s) | Notes |
|--------|----------|-------|
| Ledge hang | 253, 362, 363 | `ACTION_STATE_CATEGORIES['ledge_hang']` |
| Ledge getup | 254, 255 | Slow, standard |
| Ledge getup (>100%) | 255 | Slower version at high % |
| Ledge attack | 256, 257 | Has invincibility, punishable end lag |
| Ledge roll | 258, 259 | Invincible during roll |
| Ledge jump | 260-263 | Fastest but predictable |
| Ledgedash | 253 → release → jump → 236 → land | Advanced: retains ledge invincibility |

### Death and Kill Detection

A **kill** is detected by `stocks` decreasing between consecutive frames.
- Frame BEFORE stock drop: `last_attack_landed` = killing move, `last_hit_by` = attacker port
- Frame AFTER stock drop: `state` in DEAD_* states (0-10) = blastzone direction

| Death State | Blastzone |
|-------------|-----------|
| DEAD_DOWN (0) | Bottom (spiked, fell) |
| DEAD_LEFT (1) | Left |
| DEAD_RIGHT (2) | Right |
| DEAD_UP through DEAD_UP_FALL* (3-10) | Top |

### Respawn

| State | Meaning |
|-------|---------|
| 12 (REBIRTH) | Descending on revival platform |
| 13 (REBIRTH_WAIT) | Waiting on revival platform (invincible) |

Use `ACTION_STATE_CATEGORIES['spawn']` to detect respawn.

### Game Outcome

| Field | Value | Meaning |
|-------|-------|---------|
| `placement` | 0 | Winner |
| `end_method` | 'GAME' | Standard 1v1/FFA ending |
| `end_method` | 'RESOLVED' | Teams game ending |
| `end_method` | 'NO_CONTEST' | Someone quit (LRAS) |

---

## Technique Detection Signatures

How to identify advanced techniques in frame data:

| Technique | Detection Pattern |
|-----------|------------------|
| **Wavedash** | Jumpsquat (24) → ESCAPE_AIR (236) → grounded state with horizontal velocity |
| **Waveland** | ESCAPE_AIR (236) → platform landing, coming from above |
| **L-cancel** | `l_cancel == 1` during aerial landing |
| **Dashdance** | Repeated DASH (20) entries with alternating facing direction |
| **SHFFL** | Short jump frames → aerial state → fast fall → L-canceled landing |
| **Waveshine** | Reflector state → jumpsquat (24) → ESCAPE_AIR (236) |
| **Pillar (Falco)** | Alternating reflector state and dair state |
| **Tech chase** | Throw (219-222) → opponent in tech/missed-tech states → follow-up attack |
| **Chain grab** | Throw → opponent landing → regrab (212-214) within ~20 frames |
| **Edgehog** | Player in ledge states (253+) while opponent is offstage (y < 0 or past stage edge) |
| **Crouch cancel** | Player in crouch state (39-41) → hit → reduced knockback (stays grounded) |
| **Shield pressure** | Attacker aerial landing → defender in shield stun → attacker acts before defender |

---

## Abbreviation Reference

| Abbrev | Meaning |
|--------|---------|
| SH | Short hop |
| FH | Full hop |
| FF | Fast fall |
| WD | Wavedash |
| WL | Waveland |
| SHFFL | Short hop fast fall L-cancel |
| JC | Jump cancel |
| CC | Crouch cancel |
| AC | Auto-cancel |
| OOS | Out of shield |
| IDJ | Instant double jump |
| DI | Directional influence |
| SDI | Smash directional influence |
| ASDI | Automatic smash DI |
| CQC | Close quarters combat |
| IASA | Interruptible as soon as (first actionable frame) |
| RTC | Rest tech chase (Puff-specific) |
| FD | Final Destination (stage) |
| BF | Battlefield (stage) |
| DL | Dreamland N64 (stage) |
| YS | Yoshi's Story (stage) |
| FoD | Fountain of Dreams (stage) |
| PS | Pokemon Stadium (stage) |
| LRAS | L+R+A+Start (quit/forfeit) |

---

## Common Data Gotchas

### Port Mapping
`last_hit_by` uses **actual port numbers** (0-3), not sequential player indices.
In a 1v1 on ports 1 and 3, `last_hit_by` will be 1 or 3, not 0 or 1.
Use the port-to-player-index mapping from `game.start.players`.

### Null Frames
After a player loses their last stock, their frame data fills with `None`/`NaN`.
Always filter for non-null values when computing stats.

### Internal vs External Character IDs
`start.players[i].character` uses internal IDs. `post.character` in frame data
uses external IDs. These are different numbering systems. Use `CHARACTER_NAMES`
for start data and `CHARACTER_NAMES_EXTERNAL` for frame data.

### Move ID vs Action State Ambiguity
The same "move" can appear as different action states (e.g., fsmash has charge,
swing, and follow-through states) but always has the same move ID (10) in
`last_attack_landed`. When counting "how many times did X use fsmash," use
action state entries (for attempts) or `last_attack_landed` on victims (for
hits that connected).

### Sweetspot vs Sourspot
Many moves have multiple hitboxes with different properties (e.g., Falcon's knee
sweetspot vs sourspot, Marth's tipper vs non-tipper). The replay data does not
directly distinguish which hitbox connected — you must infer from knockback
trajectory or damage dealt.
