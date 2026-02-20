# Understanding Super Smash Bros. Melee — A Reference for AI Agents

This document explains competitive Super Smash Bros. Melee at a level of detail
sufficient to reason about replay data, answer gameplay questions, and translate
between natural language and frame-level analysis. It is written for an AI agent
that may have no prior knowledge of the game.

---

## 1. What Is Melee?

Super Smash Bros. Melee (2001, Nintendo GameCube) is a platform fighting game.
Unlike traditional fighters with health bars, Melee uses a **damage percentage**
system: as a character takes hits, their % rises, and higher % means they fly
farther when hit. The goal is to knock opponents past the **blastzones** — the
invisible boundaries surrounding the stage — to take their **stocks** (lives).

A standard competitive match is **4 stocks, 8 minutes, 1v1** on a set of legal
stages. The game runs at **60 frames per second** with no input buffer, meaning
every action must be timed precisely at the frame level.

### Why Melee Matters for Analysis

Melee's depth comes from emergent mechanics — techniques the developers never
intended that arise from the physics engine. The competitive community has spent
20+ years developing an intricate meta-game around these mechanics, creating a
rich vocabulary of techniques, strategies, and character-specific knowledge that
players discuss in natural language but that ultimately maps to frame-level data.

---

## 2. Core Mechanics

### 2.1 Damage and Knockback

Every attack has **damage** (how much % it adds) and **knockback** (how far it
sends the opponent). Knockback has two components:

- **Base knockback**: a fixed amount that applies regardless of the victim's %
- **Knockback scaling**: additional knockback proportional to the victim's %

This means the same attack sends opponents farther at higher %. A move like
Fox's up-smash might barely budge an opponent at 0% but kill them at 90%.

**Weight** affects how far a character flies. Heavier characters (Bowser) resist
knockback; lighter characters (Jigglypuff, Fox) fly farther from the same hit.

### 2.2 Hitstun

After being hit, a character enters **hitstun** — a state where they cannot
perform any action. The duration of hitstun is proportional to knockback. This
is the fundamental mechanic that enables combos: if the attacker can reach the
opponent and land another hit before hitstun ends, the opponent cannot escape.

In frame data, hitstun corresponds to the `damage` action state category
(states 75-91 + 357). A character is "in hitstun" when they are in one of these
states.

### 2.3 Hitlag (Freeze Frames)

When an attack connects, BOTH the attacker and defender freeze for a few frames.
This is **hitlag** (also called "freeze frames"). The duration depends on the
attack's damage. During hitlag, the game pauses the action briefly — this is
when DI and SDI inputs are read (see below).

### 2.4 Directional Influence (DI)

**DI** allows the player being hit to influence their knockback trajectory by
holding a direction on the control stick. DI does not reduce knockback — it
rotates the angle. Optimal DI choices depend on the situation:

- **Survival DI**: Hold perpendicular to the knockback direction to maximize
  the distance before reaching a blastzone. Against a move that sends you
  straight up, hold left or right.
- **Combo DI**: Hold a direction that makes the opponent's follow-up harder.
  Against a move that leads into a specific combo, DI away from the attacker.

DI is invisible in replay data as a direct field, but its effects are visible in
the victim's trajectory (position changes after hitstun). The `joystick_x` and
`joystick_y` fields during hitstun capture what DI the player chose.

### 2.5 Smash DI (SDI) and ASDI

**SDI** (Smash Directional Influence) allows micro-adjustments to position
during hitlag. By tapping the stick during the freeze frames, a player can shift
their position slightly — useful for escaping multi-hit moves or repositioning
before knockback begins.

**ASDI** (Automatic Smash DI) is a smaller version that happens automatically
based on whatever direction the stick is held during the last frame of hitlag.

### 2.6 Crouch Cancel (CC)

Holding down (crouching) when hit reduces knockback to **0.67x** of its normal
value. This lets a player absorb an attack and immediately counterattack. CC
is extremely powerful at low % but becomes ineffective at higher % when the
reduced knockback still sends the player into tumble. The % threshold where CC
stops working depends on the attack's knockback values.

In frame data, CC is detectable by checking if the player was in a crouching
state (states 39-41) when hit.

---

## 3. Movement

Movement in Melee is exceptionally fast and precise. Understanding the movement
states is essential for analyzing replays.

### 3.1 Ground Movement

- **Dash** (state 20): Initial burst of speed when the player taps the stick.
  During the dash animation, the player can reverse direction (enabling
  dashdancing) or transition into a run.
- **Run** (state 21): After the dash animation completes, the character enters
  a full run. Running has fewer options — the player cannot immediately reverse
  direction without a turnaround animation.
- **Walk** (states 16-19): Slow but allows any action to be performed instantly.
  Rarely used in competitive play except for precise spacing.
- **Crouch** (states 39-41): Holding down. Enables crouch cancel and allows
  certain actions like down-tilt.

### 3.2 Aerial Movement

- **Jumpsquat** (state 24): The brief crouch before becoming airborne. Duration
  varies by character (3 frames for Fox, 5 for Falcon, 6 for Marth).
- **Fall** (states 30-35): Aerial states. Characters have a **fast-fall** option
  (pressing down while falling) that increases fall speed significantly. Fast
  fall speed and normal fall speed vary by character and are critical properties.
- **Double jump**: Every character has one double jump (some have more). Using
  it provides height but removes the option until landing.

### 3.3 Advanced Movement Techniques

**Wavedash**: Performed by jumping and immediately air-dodging into the ground at
a diagonal angle. The character slides along the ground while retaining all
grounded options (grab, smash attack, tilt, shield). In frame data, this appears
as: jumpsquat (state 24) → airdodge (state 236) → landing (state 23) with
horizontal movement. Wavedash distance depends on the character's traction —
Luigi has the longest, Peach the shortest.

**Dashdance**: Rapidly alternating dash directions. In frame data, this appears
as state 20 (DASH) repeatedly with alternating facing directions. It is the
primary spacing tool in competitive Melee — players use it to threaten approach
while maintaining the ability to retreat.

**Wavelanding**: Air-dodging diagonally into a platform from above. The same
mechanic as wavedashing but used to land on platforms with momentum. Enables
fast platform movement.

**Foxtrot**: Repeatedly initiating dashes at the edge of the dash window to
cover ground with the initial burst of speed without committing to a run.

**Moonwalk**: A technique where the character moves backward while facing
forward, achieved through precise stick inputs during a dash. Primarily
associated with Captain Falcon. In frame data, look for backward velocity
during a forward-facing dash animation.

---

## 4. Attacks and Combat

### 4.1 Ground Attacks

- **Jab** (move ID 2): Fast, close-range attack. Some characters have jab
  combos (jab 1 → jab 2 → jab 3) or rapid jabs.
- **Tilts**: Medium-speed attacks performed by tilting the stick + A.
  - Forward tilt / ftilt (move ID 7)
  - Up tilt / utilt (move ID 8)
  - Down tilt / dtilt (move ID 9)
- **Smash attacks**: Powerful attacks performed by smashing the stick + A.
  Can be charged by holding A.
  - Forward smash / fsmash (move ID 10)
  - Up smash / usmash (move ID 11)
  - Down smash / dsmash (move ID 12)
- **Dash attack** (move ID 6): Attack out of a dash/run.

### 4.2 Aerial Attacks

Performed in the air. Each has landing lag (frames of vulnerability when landing
during the move) that can be halved with L-canceling.

- **Neutral air / nair** (move ID 13)
- **Forward air / fair** (move ID 14)
- **Back air / bair** (move ID 15)
- **Up air / uair** (move ID 16)
- **Down air / dair** (move ID 17)

**SHFFL** (Short Hop Fast Fall L-cancel) is the standard way to deliver aerials
quickly: short hop → aerial → fast fall → L-cancel on landing. This is the
bread and butter of aggressive play and one of the first techniques competitive
players learn.

### 4.3 Special Moves

Move IDs 18-21 correspond to Neutral B, Side B, Up B, and Down B respectively.
The actual move differs completely per character. Some signature specials:

- **Fox/Falco Reflector ("Shine")**: Down B. Frame 1 hitbox, jump-cancellable.
  One of the strongest moves in the game — used in combos, shield pressure,
  edgeguards, and as a reversal. Fox's sends opponents on a low trajectory
  (semi-spike); Falco's pops opponents upward.
- **Sheik Needles**: Neutral B. A chargeable projectile (up to 6 needles
  stored). One of the best projectiles in the game.
- **Jigglypuff Rest**: Down B. Falls asleep for ~4 seconds but has an
  incredibly powerful frame-1 hitbox that KOs at extremely low %. Rest setups
  (guaranteed ways to land Rest off a combo) are a defining aspect of Puff play.
- **Falcon Punch**: Neutral B. Iconic but slow (52 frame startup). Rarely
  used competitively except as a disrespect/style choice.

### 4.4 Grabs and Throws

Grabs bypass shields. After grabbing, the player can **pummel** (hit the
opponent for small damage) and then **throw** in one of four directions:

- Forward throw / fthrow (move ID 53)
- Back throw / bthrow (move ID 54)
- Up throw / uthrow (move ID 55)
- Down throw / dthrow (move ID 56)

Throws are critical in competitive Melee because many characters have guaranteed
follow-ups (combos) from specific throws at specific % ranges. Examples:
- Fox's up-throw → up-air is a staple combo at mid-%.
- Sheik's down-throw leads to tech chases on fast-fallers or chain grabs.
- Marth's forward-throw and up-throw lead to chain grabs on spacies (Fox/Falco)
  on flat stages.

### 4.5 L-Canceling

Pressing a shield button within **7 frames** of landing during an aerial attack
halves the landing lag. This is binary — either you L-cancel (lag halved) or you
don't (full lag). In replay data, the `l_cancel` field records: 1 = success,
2 = miss. L-cancel rate is a key skill metric; top players achieve 95%+.

### 4.6 Shield and Out-of-Shield Options

Shielding blocks all attacks but the shield shrinks with each hit and over time.
When an attack hits a shield, the defender experiences **shield stun** (can't
act) and the attacker experiences landing lag. The difference between these
determines who acts first — this is called **frame advantage**.

**Out-of-shield (OOS) options** are what a player can do directly from shield
without first dropping shield:
- **Grab** (fastest for most characters)
- **Up-smash** (via jump-cancel up-smash)
- **Up-B** (some characters)
- **Wavedash** (jump → airdodge, for repositioning)
- **Nair/uair** (jump → aerial, for punishing)
- **Roll** (forward or backward, invincible but slow and predictable)
- **Spot dodge** (invincible in place, briefly)

The speed of a character's OOS options determines how "safe" an attacker's
moves are on shield. Fox's shine is frame 1 OOS; most grabs are frame 7.

### 4.7 Powershield

If a player presses shield at the exact moment an attack connects (within a
2-frame window), they **powershield** — the attack is reflected or the defender
can act immediately without shield stun. In frame data, this is state 182.

---

## 5. Game Phases

Competitive Melee play is commonly divided into these phases. Understanding
which phase the players are in is essential for interpreting gameplay questions.

### 5.1 Neutral Game

The phase where **neither player has a clear advantage**. Both players are
spacing, positioning, and looking for an opening. Neutral is a mental game of
reads, conditioning, and risk management.

Common neutral tools:
- **Dashdancing** to maintain positioning while threatening approach
- **Aerials** (SHFFL'd nair, fair, etc.) as approach options
- **Projectiles** (Fox/Falco laser, Sheik needles) to force reactions
- **Empty movement** (empty hops, wavedash back) to bait and punish

A key neutral concept is the **risk-reward tradeoff**: safe options (retreating
aerial, laser) have low reward; committal options (dash-in grab, raw smash
attack) have high reward but are punishable if read.

Neutral ends when one player lands a significant hit or grab.

### 5.2 Punish Game (Advantage State)

After winning neutral (landing a hit or grab), the attacker enters the **punish
phase** — converting the opening into maximum damage or a kill. This is where
combos, tech chases, and chain grabs happen.

**True combo**: A sequence of hits where the opponent is in hitstun the entire
time and literally cannot escape. Requires knowledge of knockback, DI, and
follow-up timing. Example: Fox's up-throw → up-air at mid-% on most characters.

**String**: A sequence of hits where there are small gaps the opponent could
theoretically escape, but the attacker correctly reads or reacts to their
option. Most "combos" in practice are strings — they depend on reading DI.

**Conversion**: The full sequence from the initial opening to either resetting
to neutral or taking a stock. "Conversion rate" and "damage per opening" are
key metrics of punish quality.

**Tech chase**: After a knockdown (from a throw or an attack that sends the
opponent into the ground), the opponent must choose a **tech option**: tech in
place, tech roll forward, tech roll back, or no tech (missed tech → get-up from
ground). The attacker reads or reacts to this choice and punishes. Tech chasing
is critical for characters like Sheik, Captain Falcon, and Marth. In frame data,
this is a sequence: throw/knockdown → tech state (199-204) or missed tech
(183-198) → follow-up attack.

**Chain grab**: A throw that leaves the opponent in enough hitstun/lag to be
re-grabbed. The attacker throws, dashes to the landing spot, and grabs again.
Repeatable until the % gets too high. Examples:
- Marth chain grabs Fox/Falco with fthrow/dthrow on flat stages (0-~60%)
- Sheik chain grabs most characters with dthrow at low-mid %

### 5.3 Edgeguarding

When an opponent is knocked offstage, the attacking player attempts to prevent
their recovery — this is **edgeguarding**. Melee has very aggressive
edgeguarding compared to other platform fighters because recoveries are limited
and there is no ledge magnet/trump mechanic.

Common edgeguard techniques:
- **Edgehogging**: Grabbing the ledge so the recovering player cannot. Only one
  player can hold the ledge at a time. In frame data, the edgeguarder enters
  ledge states (253, 362, 363) while the opponent is offstage.
- **Offstage attacks**: Jumping offstage to hit the opponent during their
  recovery. Risky but devastating. Common examples: Marth's fair, Fox's bair/
  dair, Falcon's knee/stomp.
- **Ledge trapping**: Positioning to cover the opponent's ledge options (ledge
  getup, ledge attack, ledge roll, ledge jump, or ledge drop).

A **gimp** is a kill at low % caused by the opponent's inability to recover,
not by raw knockback. Example: hitting Fox out of his up-B startup before it
launches, leaving him helpless below the stage.

### 5.4 Recovery

The complement of edgeguarding — getting back to the stage after being knocked
off. Each character has different recovery tools:
- **Up-B**: The primary recovery move for most characters. Quality varies
  enormously (Fox's Fire Fox covers great distance; Falcon's Falcon Dive is
  slow and short).
- **Side-B**: Some characters use this for horizontal recovery (Fox Illusion,
  Falco Phantasm).
- **Double jump**: Essential for recovery positioning.
- **Air dodge**: Can be used to reach the ledge but leaves the character
  helpless.

Recovery quality is a major factor in tier placement. Characters with poor
recovery (Falcon, Falco) are much more vulnerable to edgeguarding.

### 5.5 Ledge Situation

When a player is on the ledge, they have limited options:
- **Ledge getup** (states 254-255): Stand up on stage. Slow, vulnerable.
- **Ledge attack** (states 256-257): Attack from ledge. Has invincibility but
  is slow and punishable.
- **Ledge roll** (states 258-259): Roll onto stage. Invincible during roll but
  has end lag.
- **Ledge jump** (states 260-263): Jump from ledge. Fast but predictable height.
- **Ledge drop → action**: Drop from ledge and immediately double jump, aerial,
  or air dodge. The most versatile option.

**Ledgedash**: An advanced technique where the player drops from ledge, jumps,
and wavedashes onto stage while retaining intangibility frames from the ledge.
Requires frame-perfect execution.

---

## 6. Advanced Techniques

These are the techniques that define high-level Melee play. Each one has a
specific signature in frame data.

| Technique | Input | Frame Data Signature | Purpose |
|-----------|-------|---------------------|---------|
| **Wavedash** | Jump → airdodge into ground | Jumpsquat (24) → ESCAPE_AIR (236) → landing with horizontal slide | Grounded repositioning while retaining all options |
| **L-cancel** | Shield button within 7 frames of landing | `l_cancel == 1` | Halves aerial landing lag |
| **Dashdance** | Rapidly alternate dash direction | State 20 (DASH) alternating | Spacing, threatening approach, baiting |
| **SHFFL** | Short hop → aerial → fast fall → L-cancel | Short jump → aerial state → fast fall → L-canceled landing | Fast, safe aerial delivery |
| **Wavedash OOS** | From shield: jump → airdodge into ground | Shield state → jumpsquat (24) → ESCAPE_AIR (236) | Escape shield pressure, reposition |
| **Jump-cancel grab** | During dash: jump → grab in jumpsquat | Dash (20) → jumpsquat (24) → grab (212) | Grab during a dash without dash grab's lag |
| **Waveland** | Airdodge into platform | ESCAPE_AIR (236) near platform → platform landing | Fast platform landing with momentum |
| **Shield drop** | Specific stick inputs while on platform shield | Shield → fall-through platform | Fast platform escape from shield |
| **Moonwalk** | Precise stick inputs during dash | Backward velocity during forward-facing dash | Backward movement while facing forward |
| **Waveshine** | Shine → jump cancel → wavedash | Reflector state → jumpsquat → ESCAPE_AIR | Extended shine combos (Fox/Falco) |
| **Multishine** | Rapid shine → jump → shine | Repeating: reflector → jumpsquat → reflector | Shield pressure (Fox/Falco) |
| **Pillar** | Shine → dair → shine → dair... | Alternating reflector and aerial states | Falco combo pattern |

---

## 7. Character Archetypes and the Top Tier

Melee has 26 characters but competitive play focuses on roughly 8-14. The top
tier characters have distinct playstyles:

### 7.1 Fox (Tier: 1st)

The fastest and most technically demanding character. Fox has the best
combination of speed, combo ability, and kill power.

- **Neutral**: Laser camping, SHFFL nair/drill approaches, dashdance spacing
- **Punish**: Up-throw → up-air chains, waveshine combos, up-smash kills
- **Edgeguard**: Shine spikes (frame 1 semi-spike offstage), bair, dair
- **Weaknesses**: Light weight (easy to kill), fast fall speed (easy to combo),
  technically demanding
- **Key moves**: Shine (down-B), up-smash, up-air, nair, drill (dair)
- **Signature stats to look for**: Shine usage, waveshine combo length, up-throw
  follow-up rate, L-cancel rate (Fox requires frequent L-canceling)

### 7.2 Falco (Tier: 3rd-4th)

Similar to Fox but trades speed for stronger combo game and a better laser.

- **Neutral**: Short hop laser is arguably the best projectile in the game.
  Controls space and forces approaches.
- **Punish**: The "pillar combo" — shine pops opponent up → dair spikes them
  down → shine again → repeat. Devastating against fast-fallers.
- **Edgeguard**: Dair meteor, laser at ledge, bair
- **Weaknesses**: Poor recovery (Fire Bird is short and slow), light weight,
  below-average ground speed
- **Key moves**: Laser (neutral-B), shine, dair, bair
- **Signature stats**: Laser frequency, pillar combo execution, dair usage

### 7.3 Marth (Tier: 2nd-3rd)

A swordsman with huge disjointed range and a devastating grab game.

- **Neutral**: Dtilt and fair spacing. Dashdance is exceptionally good due to
  Marth's long dash. Threatens grab at all times.
- **Punish**: Chain grabs on spacies (fthrow/dthrow at low %), tipper fsmash
  kills, fair/dair edgeguards. "Tipper" — the tip of Marth's sword does more
  damage and knockback than the base.
- **Edgeguard**: One of the best edgeguarders — fair covers enormous space
  offstage with low risk due to his double jump height.
- **Weaknesses**: Struggles to kill floaty characters, recovery is predictable
  (Dolphin Slash is linear)
- **Key moves**: Fair, dtilt, grab, fsmash (tipper), dair (spike)
- **Signature stats**: Kill % by move (tipper vs non-tipper), chain grab length

### 7.4 Sheik (Tier: 4th-5th)

A grab-based character with one of the best punish games at low-mid %.

- **Neutral**: Needles for zoning, ftilt and fair for spacing, dashdance grab.
  Struggles in neutral at low % due to crouch cancel vulnerability.
- **Punish**: Down-throw is one of the best combo starters in the game. Leads
  to: tech chases on fast-fallers (can be zero-to-death), chain grabs, or
  fair follow-ups. Fair is the primary kill move — it semi-spikes and is very
  difficult to recover from.
- **Edgeguard**: Fair covers most recovery angles, needles harass offstage
- **Weaknesses**: Poor air speed, high short hop (slow SHFFL), struggles to
  approach, poor recovery (Vanish is short, no hitbox on reappear)
- **Key moves**: Fair, dthrow, needles, ftilt, dash attack
- **Signature stats**: Dthrow follow-up rate, tech chase success, fair kill %

### 7.5 Captain Falcon (Tier: 6th)

The fastest ground speed in the game with explosive combo and kill potential.

- **Neutral**: Dashdance (best in the game due to speed), nair spacing,
  overshoot aerials, empty hop → grab mixups
- **Punish**: Tech chase-based. Dthrow → react to tech option → knee/stomp/
  regrab. "Knee" (fair) sweetspot kills at ~60%, one of the strongest kill
  moves. The "Gentleman" (frame-perfect jab 1-2-3) is used in pressure and
  combo starters.
- **Edgeguard**: Knee, stomp (dair meteor), bair
- **Weaknesses**: Terrible recovery (Falcon Dive is slow and short), no
  projectile, predictable approach options, limited range
- **Key moves**: Knee (fair), stomp (dair), nair, up-air, grab → dthrow
- **Unique terminology**: "Knee" = sweetspot fair, "stomp" = dair, "gentleman"
  = 3-hit jab, "nipple spike" = specific uair hitbox that spikes, "the Knee
  of Justice" = stylish sweetspot knee kill
- **Signature stats**: Tech chase conversion rate, knee sweetspot rate (strong
  vs weak fair hitbox)

### 7.6 Jigglypuff (Tier: 3rd-5th, volatile)

A floaty character with the best air game and a devastating kill move.

- **Neutral**: Back-air spacing is Puff's bread and butter — short range but
  fast, strong, and safe. Pound (side-B) for shield pressure. Aerial drift
  (best air speed in the game) to weave in and out of range.
- **Punish**: Up-throw → Rest on fast-fallers at kill %, up-air chains → Rest,
  "Wall of Pain" — a sequence of bairs offstage that carries the opponent to
  the blastzone. Edge-cancel and teeter-cancel techniques extend combo
  potential.
- **Edgeguard**: Arguably the best edgeguarder. Five jumps + best air speed
  means Puff can chase deep offstage. Bair and fair are strong offstage.
- **Weaknesses**: Lightest character (dies very early to strong hits), slow
  ground speed, poor wavedash, no projectile, vulnerable to camping/lasers
- **Key moves**: Bair, Rest (down-B), up-air, Pound (side-B), fair
- **Unique terminology**: "Wall of Pain" = repeated bairs offstage, "RTC" =
  Rest Tech Chase (a Rest setup off a tech chase), "Rest punish" = the ~4
  second window where Puff sleeps and can be punished
- **Signature stats**: Rest hit rate, bair frequency, kill % distribution

### 7.7 Peach (Tier: 5th-7th)

A floaty character with unique float and turnip mechanics.

- **Neutral**: Float-canceled aerials (Peach can hover and attack with reduced
  lag), turnip pull and throw for projectile control, dsmash for CC punish
- **Punish**: Dsmash is a multi-hit move that can do 30-50%+ on a CC'd opponent.
  Float cancel aerials chain into each other at low %.
- **Weaknesses**: Slow ground movement, predictable recovery, struggles vs
  characters who outrange her
- **Key moves**: Fair, dsmash, turnip (down-B), float-cancel nair/bair

### 7.8 Ice Climbers (Tier: 7th-8th)

Two characters controlled simultaneously. Nana (the AI partner) follows Popo's
inputs with a slight delay.

- **Key mechanic**: "Wobbling" — an infinite combo where Popo grabs while Nana
  pummels, creating an inescapable loop. Some tournaments ban this. "Handoffs"
  are grab transfers between the two climbers for chain grabs.
- **Weaknesses**: When separated (Nana is hit away), the Ice Climbers are
  drastically weaker. Killing Nana first is a common strategy.

---

## 8. Matchup Dynamics

Matchup knowledge is central to competitive Melee. Each pairing has specific
interactions, percent thresholds, and strategic considerations.

### 8.1 Key Matchup Concepts

- **Fast-faller vs floaty**: Fast-fallers (Fox, Falco, Falcon) fall quickly,
  making them susceptible to extended combos and chain grabs. Floaty characters
  (Puff, Peach) are hard to combo but also hard to kill at low %.
- **Projectile vs no projectile**: Characters with good projectiles (Falco
  laser, Sheik needles) can force opponents to approach, controlling the pace
  of neutral.
- **Range advantage**: Marth's sword outranges most characters, forcing them to
  find ways around his wall of hitboxes.
- **Recovery vs edgeguarding**: Matchups where one character has strong
  edgeguards against another's weak recovery are often lopsided offstage.

### 8.2 Common Matchup Patterns

**Fox vs Marth**: Marth can chain grab Fox on flat stages (particularly Final
Destination), making stage choice critical. Fox relies on up-throw → up-air
combos and fast movement to compensate.

**Fox vs Sheik**: Fox is generally favored. Sheik wants grabs for dthrow tech
chases; Fox avoids grabs through movement and crouch cancel at low %. Fox's
speed and combo weight make Sheik's neutral difficult.

**Fox vs Jigglypuff**: Fox uses lasers to accumulate damage safely, then
up-throw → up-air at kill %. Puff threatens Rest and bair walls. Fox must avoid
Rest setups (particularly up-throw Rest at certain %).

**Fox vs Falco**: Laser control defines this matchup. Falco's lasers disrupt
Fox's movement; Fox's speed lets him punish Falco's commitments hard.

**Falcon vs Sheik**: Sheik's dthrow tech chases are devastating against Falcon
(heavy, fast faller = long tech chase windows). Falcon needs to avoid grabs and
win through raw speed and aerial advantage.

**Marth vs Sheik**: Marth outranges Sheik in neutral but Sheik's dthrow can
lead to extended punishes. Marth struggles to kill Sheik at high % without a
tipper setup.

**Puff vs Marth**: Puff struggles against Marth's disjoint and tipper threat,
but Puff's edgeguarding against Marth is among the best in the game.

---

## 9. Stages

Competitive Melee uses a limited stage list. Stage choice affects matchups
significantly.

### 9.1 Legal Stages

| Stage | Key Properties | Notable For |
|-------|---------------|-------------|
| **Battlefield** | 3 platforms, medium size | Platform play, aerial characters benefit |
| **Final Destination** | Flat, no platforms | Chain grabs are inescapable, favors characters with strong ground game |
| **Dreamland N64** | 3 high platforms, large blastzones | Survival stage — characters live longer, hard to kill off top |
| **Yoshi's Story** | Small, low platforms, close blastzones | Early kills, aggressive play rewarded |
| **Fountain of Dreams** | 3 platforms that move up/down | Disrupts platform-dependent combos, unique interactions |
| **Pokemon Stadium** | Flat with 2 platforms, transforms | Transformations create temporary layout changes |

### 9.2 Stage Selection Strategy

- Characters with chain grabs prefer Final Destination (Marth vs spacies)
- Light characters prefer large stages (Dreamland) for survival
- Characters with strong edgeguards prefer small stages (Yoshi's Story)
- Platform-heavy characters prefer Battlefield (Peach, Fox)

---

## 10. Key Terminology Quick Reference

This section provides a compact glossary of terms that appear frequently in
competitive Melee discussion.

### Moves and Actions
- **Nair/fair/bair/uair/dair**: Neutral/forward/back/up/down aerial
- **Ftilt/utilt/dtilt**: Forward/up/down tilt
- **Fsmash/usmash/dsmash**: Forward/up/down smash
- **Fthrow/bthrow/uthrow/dthrow**: Forward/back/up/down throw
- **Shine**: Fox or Falco's down-B (Reflector)
- **Knee**: Captain Falcon's forward aerial (sweetspot is "the knee")
- **Stomp**: Captain Falcon's down aerial
- **Gentleman**: Falcon's three-hit jab (requires frame-perfect timing to avoid rapid jab)
- **Tipper**: The tip of Marth's sword (does more damage/knockback)
- **Rest**: Jigglypuff's down-B (frame 1 instant KO move, 4 second sleep on miss/hit)
- **Wall of Pain**: Puff chaining bairs offstage to carry opponents to blastzone
- **Pillar**: Falco's shine → dair → shine → dair combo pattern
- **Waveshine**: Shine → jump cancel → wavedash (extends shine combos)

### Techniques
- **SH**: Short hop
- **FH**: Full hop
- **FF**: Fast fall
- **WD**: Wavedash
- **SHFFL**: Short hop fast fall L-cancel (standard aerial delivery)
- **JC**: Jump cancel (used for JC grab, JC up-smash)
- **CC**: Crouch cancel
- **AC**: Auto-cancel (landing during frames where aerial has no landing lag)
- **OOS**: Out of shield (options available from shield without dropping it)
- **IDJ**: Instant double jump (double jump on first airborne frame)
- **DI**: Directional influence
- **SDI**: Smash directional influence
- **ASDI**: Automatic smash DI

### Game Concepts
- **Neutral**: Phase where neither player has advantage
- **Punish**: Converting a hit into damage/stocks
- **Conversion**: The complete punish sequence from opening to reset/kill
- **Tech chase**: Reacting to an opponent's tech option after knockdown
- **Chain grab**: Repeated grab-throw-regrab sequence
- **Edgeguard**: Preventing an offstage opponent from recovering
- **Gimp**: Killing an opponent at low % by exploiting recovery weakness
- **Edgehog**: Holding the ledge to deny it to the recovering player
- **Read**: Predicting the opponent's action and preemptively countering it
- **Mixup**: Varying between multiple options to stay unpredictable
- **Conditioning**: Establishing patterns to manipulate future opponent choices
- **Frame trap**: Leaving a small gap in pressure that baits the opponent into
  acting, then punishing the action
- **Whiff punish**: Punishing an opponent's missed attack during its end lag
- **Spacing**: Controlling the distance between characters to maximize safety
  and punish potential
- **Stage control**: Occupying center stage, pushing the opponent toward edges
  and platforms where they have fewer options

### Character Classes
- **Spacies**: Fox and Falco (from "space animals")
- **Fast-fallers**: Characters with high fall speed (Fox, Falco, Falcon). Easy
  to combo vertically; benefit from strong vertical survival.
- **Floaties**: Characters with low fall speed (Puff, Peach, Samus). Hard to
  combo but die to horizontal kills earlier.
- **Swordie/swordsman**: Marth (and to a lesser extent Roy). Disjointed
  hitboxes that extend past their hurtbox.

### Numerical Terminology
- **Frame**: 1/60th of a second. All timing in Melee is measured in frames.
- **Startup**: The number of frames before a move's hitbox becomes active.
- **Active frames**: Frames during which the hitbox can hit.
- **End lag / IASA**: Frames of recovery after the active frames where the
  character is vulnerable. IASA = Interruptible As Soon As (the first frame
  the character can act again).
- **Landing lag**: Vulnerability frames when landing during an aerial attack.
  Halved by L-canceling.
- **Shield stun**: Frames the defender cannot act after their shield is hit.
- **Hitlag**: Freeze frames both characters experience on hit.

---

## 11. Connecting Concepts to Replay Data

When analyzing .slp replay data, the concepts above map to specific data fields:

| Concept | Data Field / Detection Method |
|---------|------------------------------|
| What move was used | `action_state` for the attacker's animation state |
| What move hit the victim | `last_attack_landed` (move ID) on the victim's frame |
| Who hit whom | `last_hit_by` (port number) on the victim's frame |
| Damage dealt | Change in `percent` between frames |
| In hitstun | `action_state` in damage category (75-91, 357) |
| Performing a tech | `action_state` in tech states (199-204) |
| Missed tech | `action_state` in missed tech states (183-198) |
| On ledge | `action_state` in ledge_hang category (253, 362, 363) |
| Wavedash | Jumpsquat (24) → airdodge (236) → ground state with x-velocity |
| L-cancel success | `l_cancel == 1` |
| Kill / death | `stocks` decreases between consecutive frames |
| Blastzone | Death state (0-10) after stock loss |
| Stage position | `position_x`, `position_y` per frame |
| Shield | `action_state` in shield category (178-180, 349) |

### What Replay Data Cannot Tell You

- **Player intent**: You can see WHAT happened but not WHY. Was that airdodge
  an intentional wavedash or a panic option? Context (game state, positioning,
  opponent's action) is needed to infer intent.
- **Mental game**: Reads, conditioning, and adaptation are invisible in frame
  data. You can only observe their effects.
- **DI quality**: You can see the result (trajectory) but must infer whether
  the DI was optimal given the situation.
- **Missed inputs**: The data shows what happened, not what the player tried
  to do. A missed L-cancel shows up as `l_cancel == 2`, but other missed
  inputs (missed wavedash, wrong aerial) are harder to detect.
