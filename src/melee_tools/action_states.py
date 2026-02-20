"""
Melee Action State IDs — complete mapping from numeric ID to name.

Sources:
- py-slippi (hohav/py-slippi): ActionState IntEnum from slippi/id.py
- 20XX Hack Pack (Achilles1515): SSBM Facts.txt canonical game names
- libmelee (altf4/libmelee): melee/enums.py Action enum

These are the "common" action states (0-382) shared by all characters.
Character-specific action states start at 341+ but overlap with some
shared states; the character-specific ones (e.g., Fox shine, Marth counter)
use IDs >= 0x127 (295+) that vary per character.

Usage:
    from melee_tools.action_states import ACTION_STATES, ACTION_STATE_CATEGORIES
    name = ACTION_STATES[14]  # "WAIT"
"""

# =============================================================================
# Full action state ID -> name mapping (0-382)
# Names use py-slippi conventions (UPPER_SNAKE_CASE).
# The comment after each entry shows the canonical game internal name
# from 20XX/the Melee debug menu where it differs.
# =============================================================================

ACTION_STATES: dict[int, str] = {
    # --- Death / KO states (0-10) ---
    0: "DEAD_DOWN",                       # DeadDown
    1: "DEAD_LEFT",                       # DeadLeft
    2: "DEAD_RIGHT",                      # DeadRight
    3: "DEAD_UP",                         # DeadUp
    4: "DEAD_UP_STAR",                    # DeadUpStar
    5: "DEAD_UP_STAR_ICE",               # DeadUpStarIce
    6: "DEAD_UP_FALL",                    # DeadUpFall
    7: "DEAD_UP_FALL_HIT_CAMERA",        # DeadUpFallHitCamera
    8: "DEAD_UP_FALL_HIT_CAMERA_FLAT",   # DeadUpFallHitCameraFlat
    9: "DEAD_UP_FALL_ICE",               # DeadUpFallIce
    10: "DEAD_UP_FALL_HIT_CAMERA_ICE",   # DeadUpFallHitCameraIce

    # --- Respawn / Sleep (11-13) ---
    11: "SLEEP",                          # Sleep (also: nothing state before spawn)
    12: "REBIRTH",                        # Rebirth (on halo descent)
    13: "REBIRTH_WAIT",                   # RebirthWait (on halo wait)

    # --- Idle / Movement (14-23) ---
    14: "WAIT",                           # Wait (idle/standing)
    15: "WALK_SLOW",                      # WalkSlow
    16: "WALK_MIDDLE",                    # WalkMiddle
    17: "WALK_FAST",                      # WalkFast
    18: "TURN",                           # Turn
    19: "TURN_RUN",                       # TurnRun
    20: "DASH",                           # Dash (initial dash)
    21: "RUN",                            # Run
    22: "RUN_DIRECT",                     # RunDirect
    23: "RUN_BRAKE",                      # RunBrake

    # --- Jump / Squat (24-28) ---
    24: "KNEE_BEND",                      # KneeBend (jumpsquat)
    25: "JUMP_F",                         # JumpF (first jump forward)
    26: "JUMP_B",                         # JumpB (first jump backward)
    27: "JUMP_AERIAL_F",                  # JumpAerialF (double jump forward)
    28: "JUMP_AERIAL_B",                  # JumpAerialB (double jump backward)

    # --- Falling (29-38) ---
    29: "FALL",                           # Fall
    30: "FALL_F",                         # FallF
    31: "FALL_B",                         # FallB
    32: "FALL_AERIAL",                    # FallAerial (fall after double jump)
    33: "FALL_AERIAL_F",                  # FallAerialF
    34: "FALL_AERIAL_B",                  # FallAerialB
    35: "FALL_SPECIAL",                   # FallSpecial (helpless fall)
    36: "FALL_SPECIAL_F",                 # FallSpecialF
    37: "FALL_SPECIAL_B",                 # FallSpecialB
    38: "DAMAGE_FALL",                    # DamageFall (tumble)

    # --- Crouch (39-41) ---
    39: "SQUAT",                          # Squat (crouch start)
    40: "SQUAT_WAIT",                     # SquatWait (crouching)
    41: "SQUAT_RV",                       # SquatRv (crouch end / stand up from crouch)

    # --- Landing (42-43) ---
    42: "LANDING",                        # Landing (normal landing)
    43: "LANDING_FALL_SPECIAL",           # LandingFallSpecial (special fall landing lag)

    # --- Jab / Neutral A (44-49) ---
    44: "ATTACK_11",                      # Attack11 (jab 1)
    45: "ATTACK_12",                      # Attack12 (jab 2)
    46: "ATTACK_13",                      # Attack13 (jab 3)
    47: "ATTACK_100_START",              # Attack100Start (rapid jab start)
    48: "ATTACK_100_LOOP",              # Attack100Loop (rapid jab loop)
    49: "ATTACK_100_END",               # Attack100End (rapid jab end)

    # --- Dash Attack (50) ---
    50: "ATTACK_DASH",                    # AttackDash

    # --- Forward Tilt (51-55) ---
    51: "ATTACK_S_3_HI",                 # AttackS3Hi (f-tilt angled up)
    52: "ATTACK_S_3_HI_S",              # AttackS3HiS (f-tilt angled slightly up)
    53: "ATTACK_S_3_S",                  # AttackS3S (f-tilt straight)
    54: "ATTACK_S_3_LW_S",              # AttackS3LwS (f-tilt angled slightly down)
    55: "ATTACK_S_3_LW",                # AttackS3Lw (f-tilt angled down)

    # --- Up Tilt / Down Tilt (56-57) ---
    56: "ATTACK_HI_3",                   # AttackHi3 (up tilt)
    57: "ATTACK_LW_3",                   # AttackLw3 (down tilt)

    # --- Forward Smash (58-62) ---
    58: "ATTACK_S_4_HI",                 # AttackS4Hi (f-smash angled up)
    59: "ATTACK_S_4_HI_S",              # AttackS4HiS
    60: "ATTACK_S_4_S",                  # AttackS4S (f-smash straight)
    61: "ATTACK_S_4_LW_S",              # AttackS4LwS
    62: "ATTACK_S_4_LW",                # AttackS4Lw (f-smash angled down)

    # --- Up Smash / Down Smash (63-64) ---
    63: "ATTACK_HI_4",                   # AttackHi4 (up smash)
    64: "ATTACK_LW_4",                   # AttackLw4 (down smash)

    # --- Aerials (65-69) ---
    65: "ATTACK_AIR_N",                  # AttackAirN (nair)
    66: "ATTACK_AIR_F",                  # AttackAirF (fair)
    67: "ATTACK_AIR_B",                  # AttackAirB (bair)
    68: "ATTACK_AIR_HI",                # AttackAirHi (uair)
    69: "ATTACK_AIR_LW",                # AttackAirLw (dair)

    # --- Aerial Landing Lag (70-74) ---
    70: "LANDING_AIR_N",                 # LandingAirN (nair landing)
    71: "LANDING_AIR_F",                 # LandingAirF (fair landing)
    72: "LANDING_AIR_B",                 # LandingAirB (bair landing)
    73: "LANDING_AIR_HI",               # LandingAirHi (uair landing)
    74: "LANDING_AIR_LW",               # LandingAirLw (dair landing)

    # --- Damage / Hitstun (75-91) ---
    75: "DAMAGE_HI_1",                   # DamageHi1
    76: "DAMAGE_HI_2",                   # DamageHi2
    77: "DAMAGE_HI_3",                   # DamageHi3
    78: "DAMAGE_N_1",                    # DamageN1
    79: "DAMAGE_N_2",                    # DamageN2
    80: "DAMAGE_N_3",                    # DamageN3
    81: "DAMAGE_LW_1",                   # DamageLw1
    82: "DAMAGE_LW_2",                   # DamageLw2
    83: "DAMAGE_LW_3",                   # DamageLw3
    84: "DAMAGE_AIR_1",                  # DamageAir1
    85: "DAMAGE_AIR_2",                  # DamageAir2
    86: "DAMAGE_AIR_3",                  # DamageAir3
    87: "DAMAGE_FLY_HI",                # DamageFlyHi (knockback high)
    88: "DAMAGE_FLY_N",                  # DamageFlyN (knockback neutral)
    89: "DAMAGE_FLY_LW",                # DamageFlyLw (knockback low)
    90: "DAMAGE_FLY_TOP",               # DamageFlyTop (knockback straight up)
    91: "DAMAGE_FLY_ROLL",              # DamageFlyRoll (knockback tumble)

    # --- Item Pickup (92-93) ---
    92: "LIGHT_GET",                     # LightGet (pick up light item)
    93: "HEAVY_GET",                     # HeavyGet (pick up heavy item)

    # --- Item Throw - Light (94-103) ---
    94: "LIGHT_THROW_F",                 # LightThrowF
    95: "LIGHT_THROW_B",                 # LightThrowB
    96: "LIGHT_THROW_HI",               # LightThrowHi
    97: "LIGHT_THROW_LW",               # LightThrowLw
    98: "LIGHT_THROW_DASH",             # LightThrowDash
    99: "LIGHT_THROW_DROP",             # LightThrowDrop
    100: "LIGHT_THROW_AIR_F",           # LightThrowAirF
    101: "LIGHT_THROW_AIR_B",           # LightThrowAirB
    102: "LIGHT_THROW_AIR_HI",          # LightThrowAirHi
    103: "LIGHT_THROW_AIR_LW",          # LightThrowAirLw

    # --- Item Throw - Heavy (104-107) ---
    104: "HEAVY_THROW_F",               # HeavyThrowF
    105: "HEAVY_THROW_B",               # HeavyThrowB
    106: "HEAVY_THROW_HI",              # HeavyThrowHi
    107: "HEAVY_THROW_LW",              # HeavyThrowLw

    # --- Item Throw - Smash (108-119) ---
    108: "LIGHT_THROW_F_4",             # LightThrowF4 (smash throw forward)
    109: "LIGHT_THROW_B_4",             # LightThrowB4
    110: "LIGHT_THROW_HI_4",            # LightThrowHi4
    111: "LIGHT_THROW_LW_4",            # LightThrowLw4
    112: "LIGHT_THROW_AIR_F_4",         # LightThrowAirF4
    113: "LIGHT_THROW_AIR_B_4",         # LightThrowAirB4
    114: "LIGHT_THROW_AIR_HI_4",        # LightThrowAirHi4
    115: "LIGHT_THROW_AIR_LW_4",        # LightThrowAirLw4
    116: "HEAVY_THROW_F_4",             # HeavyThrowF4
    117: "HEAVY_THROW_B_4",             # HeavyThrowB4
    118: "HEAVY_THROW_HI_4",            # HeavyThrowHi4
    119: "HEAVY_THROW_LW_4",            # HeavyThrowLw4

    # --- Weapon Swings: Beam Sword (120-123) ---
    120: "SWORD_SWING_1",               # SwordSwing1
    121: "SWORD_SWING_3",               # SwordSwing3
    122: "SWORD_SWING_4",               # SwordSwing4
    123: "SWORD_SWING_DASH",            # SwordSwingDash

    # --- Weapon Swings: Bat (124-127) ---
    124: "BAT_SWING_1",                 # BatSwing1
    125: "BAT_SWING_3",                 # BatSwing3
    126: "BAT_SWING_4",                 # BatSwing4
    127: "BAT_SWING_DASH",              # BatSwingDash

    # --- Weapon Swings: Parasol (128-131) ---
    128: "PARASOL_SWING_1",             # ParasolSwing1
    129: "PARASOL_SWING_3",             # ParasolSwing3
    130: "PARASOL_SWING_4",             # ParasolSwing4
    131: "PARASOL_SWING_DASH",          # ParasolSwingDash

    # --- Weapon Swings: Fan / Harisen (132-135) ---
    132: "HARISEN_SWING_1",             # HarisenSwing1
    133: "HARISEN_SWING_3",             # HarisenSwing3
    134: "HARISEN_SWING_4",             # HarisenSwing4
    135: "HARISEN_SWING_DASH",          # HarisenSwingDash

    # --- Weapon Swings: Star Rod (136-139) ---
    136: "STAR_ROD_SWING_1",            # StarRodSwing1
    137: "STAR_ROD_SWING_3",            # StarRodSwing3
    138: "STAR_ROD_SWING_4",            # StarRodSwing4
    139: "STAR_ROD_SWING_DASH",         # StarRodSwingDash

    # --- Weapon Swings: Lip's Stick (140-143) ---
    140: "LIP_STICK_SWING_1",           # LipStickSwing1
    141: "LIP_STICK_SWING_3",           # LipStickSwing3
    142: "LIP_STICK_SWING_4",           # LipStickSwing4
    143: "LIP_STICK_SWING_DASH",        # LipStickSwingDash

    # --- Parasol Item (144-147) ---
    144: "ITEM_PARASOL_OPEN",           # ItemParasolOpen
    145: "ITEM_PARASOL_FALL",           # ItemParasolFall
    146: "ITEM_PARASOL_FALL_SPECIAL",   # ItemParasolFallSpecial
    147: "ITEM_PARASOL_DAMAGE_FALL",    # ItemParasolDamageFall

    # --- Ray Gun (148-151) ---
    148: "L_GUN_SHOOT",                 # LGunShoot
    149: "L_GUN_SHOOT_AIR",             # LGunShootAir
    150: "L_GUN_SHOOT_EMPTY",           # LGunShootEmpty
    151: "L_GUN_SHOOT_AIR_EMPTY",       # LGunShootAirEmpty

    # --- Fire Flower (152-153) ---
    152: "FIRE_FLOWER_SHOOT",           # FireFlowerShoot
    153: "FIRE_FLOWER_SHOOT_AIR",       # FireFlowerShootAir

    # --- Screw Attack Item (154-157) ---
    154: "ITEM_SCREW",                  # ItemScrew
    155: "ITEM_SCREW_AIR",              # ItemScrewAir
    156: "DAMAGE_SCREW",                # DamageScrew
    157: "DAMAGE_SCREW_AIR",            # DamageScrewAir

    # --- Super Scope (158-173) ---
    158: "ITEM_SCOPE_START",            # ItemScopeStart
    159: "ITEM_SCOPE_RAPID",            # ItemScopeRapid
    160: "ITEM_SCOPE_FIRE",             # ItemScopeFire
    161: "ITEM_SCOPE_END",              # ItemScopeEnd
    162: "ITEM_SCOPE_AIR_START",        # ItemScopeAirStart
    163: "ITEM_SCOPE_AIR_RAPID",        # ItemScopeAirRapid
    164: "ITEM_SCOPE_AIR_FIRE",         # ItemScopeAirFire
    165: "ITEM_SCOPE_AIR_END",          # ItemScopeAirEnd
    166: "ITEM_SCOPE_START_EMPTY",      # ItemScopeStartEmpty
    167: "ITEM_SCOPE_RAPID_EMPTY",      # ItemScopeRapidEmpty
    168: "ITEM_SCOPE_FIRE_EMPTY",       # ItemScopeFireEmpty
    169: "ITEM_SCOPE_END_EMPTY",        # ItemScopeEndEmpty
    170: "ITEM_SCOPE_AIR_START_EMPTY",  # ItemScopeAirStartEmpty
    171: "ITEM_SCOPE_AIR_RAPID_EMPTY",  # ItemScopeAirRapidEmpty
    172: "ITEM_SCOPE_AIR_FIRE_EMPTY",   # ItemScopeAirFireEmpty
    173: "ITEM_SCOPE_AIR_END_EMPTY",    # ItemScopeAirEndEmpty

    # --- Lift / Carry (174-177) ---
    174: "LIFT_WAIT",                   # LiftWait
    175: "LIFT_WALK_1",                 # LiftWalk1
    176: "LIFT_WALK_2",                 # LiftWalk2
    177: "LIFT_TURN",                   # LiftTurn

    # --- Shield (178-182) ---
    178: "GUARD_ON",                    # GuardOn (shield startup)
    179: "GUARD",                       # Guard (shielding)
    180: "GUARD_OFF",                   # GuardOff (shield release)
    181: "GUARD_SET_OFF",               # GuardSetOff (shield stun / pushback)
    182: "GUARD_REFLECT",               # GuardReflect (powershield)

    # --- Downed / Knockdown - Face Up (183-190) ---
    183: "DOWN_BOUND_U",                # DownBoundU (missed tech face up)
    184: "DOWN_WAIT_U",                 # DownWaitU (lying on ground face up)
    185: "DOWN_DAMAGE_U",               # DownDamageU (hit while lying face up)
    186: "DOWN_STAND_U",                # DownStandU (getup from ground face up)
    187: "DOWN_ATTACK_U",               # DownAttackU (getup attack face up)
    188: "DOWN_FOWARD_U",               # DownFowardU (roll forward face up)
    189: "DOWN_BACK_U",                 # DownBackU (roll backward face up)
    190: "DOWN_SPOT_U",                 # DownSpotU (getup in place face up)

    # --- Downed / Knockdown - Face Down (191-198) ---
    191: "DOWN_BOUND_D",                # DownBoundD (missed tech face down)
    192: "DOWN_WAIT_D",                 # DownWaitD (lying on ground face down)
    193: "DOWN_DAMAGE_D",               # DownDamageD (hit while lying face down)
    194: "DOWN_STAND_D",                # DownStandD (getup from ground face down)
    195: "DOWN_ATTACK_D",               # DownAttackD (getup attack face down)
    196: "DOWN_FOWARD_D",               # DownFowardD (roll forward face down)
    197: "DOWN_BACK_D",                 # DownBackD (roll backward face down)
    198: "DOWN_SPOT_D",                 # DownSpotD (getup in place face down)

    # --- Tech / Passive (199-204) ---
    199: "PASSIVE",                     # Passive (tech in place / neutral tech)
    200: "PASSIVE_STAND_F",             # PassiveStandF (tech roll forward)
    201: "PASSIVE_STAND_B",             # PassiveStandB (tech roll backward)
    202: "PASSIVE_WALL",                # PassiveWall (wall tech)
    203: "PASSIVE_WALL_JUMP",           # PassiveWallJump (wall tech jump)
    204: "PASSIVE_CEIL",                # PassiveCeil (ceiling tech)

    # --- Shield Break (205-211) ---
    205: "SHIELD_BREAK_FLY",            # ShieldBreakFly
    206: "SHIELD_BREAK_FALL",           # ShieldBreakFall
    207: "SHIELD_BREAK_DOWN_U",         # ShieldBreakDownU
    208: "SHIELD_BREAK_DOWN_D",         # ShieldBreakDownD
    209: "SHIELD_BREAK_STAND_U",        # ShieldBreakStandU
    210: "SHIELD_BREAK_STAND_D",        # ShieldBreakStandD
    211: "FURA_FURA",                   # FuraFura (dazed / shield broken stun)

    # --- Grab (212-218) ---
    212: "CATCH",                       # Catch (grab)
    213: "CATCH_PULL",                  # CatchPull (grab pulling opponent)
    214: "CATCH_DASH",                  # CatchDash (dash grab)
    215: "CATCH_DASH_PULL",             # CatchDashPull
    216: "CATCH_WAIT",                  # CatchWait (holding opponent)
    217: "CATCH_ATTACK",                # CatchAttack (grab pummel)
    218: "CATCH_CUT",                   # CatchCut (grab release / grab break)

    # --- Throws (219-222) ---
    219: "THROW_F",                     # ThrowF (forward throw)
    220: "THROW_B",                     # ThrowB (back throw)
    221: "THROW_HI",                    # ThrowHi (up throw)
    222: "THROW_LW",                    # ThrowLw (down throw)

    # --- Being Grabbed (223-232) ---
    223: "CAPTURE_PULLED_HI",           # CapturePulledHi
    224: "CAPTURE_WAIT_HI",             # CaptureWaitHi (grabbed, held high)
    225: "CAPTURE_DAMAGE_HI",           # CaptureDamageHi (pummeled high)
    226: "CAPTURE_PULLED_LW",           # CapturePulledLw
    227: "CAPTURE_WAIT_LW",             # CaptureWaitLw (grabbed, held low)
    228: "CAPTURE_DAMAGE_LW",           # CaptureDamageLw (pummeled low)
    229: "CAPTURE_CUT",                 # CaptureCut (grab escape / mash out)
    230: "CAPTURE_JUMP",                # CaptureJump (grab jump)
    231: "CAPTURE_NECK",                # CaptureNeck
    232: "CAPTURE_FOOT",                # CaptureFoot

    # --- Dodge / Roll (233-236) ---
    233: "ESCAPE_F",                    # EscapeF (roll forward)
    234: "ESCAPE_B",                    # EscapeB (roll backward)
    235: "ESCAPE",                      # Escape (spot dodge)
    236: "ESCAPE_AIR",                  # EscapeAir (air dodge)

    # --- Rebound / Clank (237-238) ---
    237: "REBOUND_STOP",                # ReboundStop
    238: "REBOUND",                     # Rebound

    # --- Being Thrown (239-243) ---
    239: "THROWN_F",                     # ThrownF (being forward thrown)
    240: "THROWN_B",                     # ThrownB (being back thrown)
    241: "THROWN_HI",                    # ThrownHi (being up thrown)
    242: "THROWN_LW",                    # ThrownLw (being down thrown)
    243: "THROWN_LW_WOMEN",             # ThrownLwWomen

    # --- Platform / Edge Teeter (244-251) ---
    244: "PASS",                        # Pass (platform drop-through)
    245: "OTTOTTO",                     # Ottotto (teetering on edge start)
    246: "OTTOTTO_WAIT",                # OttottoWait (teetering on edge)
    247: "FLY_REFLECT_WALL",            # FlyReflectWall (bounce off wall)
    248: "FLY_REFLECT_CEIL",            # FlyReflectCeil (bounce off ceiling)
    249: "STOP_WALL",                   # StopWall (bump wall)
    250: "STOP_CEIL",                   # StopCeil (bump ceiling)
    251: "MISS_FOOT",                   # MissFoot (sliding off edge)

    # --- Ledge / Cliff (252-263) ---
    252: "CLIFF_CATCH",                 # CliffCatch (ledge grab)
    253: "CLIFF_WAIT",                  # CliffWait (hanging on ledge)
    254: "CLIFF_CLIMB_SLOW",            # CliffClimbSlow (ledge getup >100%)
    255: "CLIFF_CLIMB_QUICK",           # CliffClimbQuick (ledge getup <100%)
    256: "CLIFF_ATTACK_SLOW",           # CliffAttackSlow (ledge attack >100%)
    257: "CLIFF_ATTACK_QUICK",          # CliffAttackQuick (ledge attack <100%)
    258: "CLIFF_ESCAPE_SLOW",           # CliffEscapeSlow (ledge roll >100%)
    259: "CLIFF_ESCAPE_QUICK",          # CliffEscapeQuick (ledge roll <100%)
    260: "CLIFF_JUMP_SLOW_1",           # CliffJumpSlow1 (ledge jump >100%)
    261: "CLIFF_JUMP_SLOW_2",           # CliffJumpSlow2
    262: "CLIFF_JUMP_QUICK_1",          # CliffJumpQuick1 (ledge jump <100%)
    263: "CLIFF_JUMP_QUICK_2",          # CliffJumpQuick2

    # --- Taunt (264-265) ---
    264: "APPEAL_R",                    # AppealR (taunt right)
    265: "APPEAL_L",                    # AppealL (taunt left)

    # --- DK Cargo / Shouldered (266-270) ---
    266: "SHOULDERED_WAIT",             # ShoulderedWait (DK cargo hold)
    267: "SHOULDERED_WALK_SLOW",        # ShoulderedWalkSlow
    268: "SHOULDERED_WALK_MIDDLE",      # ShoulderedWalkMiddle
    269: "SHOULDERED_WALK_FAST",        # ShoulderedWalkFast
    270: "SHOULDERED_TURN",             # ShoulderedTurn

    # --- Being Thrown (extended) (271-274) ---
    271: "THROWN_F_F",                  # ThrownFF
    272: "THROWN_F_B",                  # ThrownFB
    273: "THROWN_F_HI",                 # ThrownFHi
    274: "THROWN_F_LW",                 # ThrownFLw

    # --- Character-Specific Capture States (275-292) ---
    275: "CAPTURE_CAPTAIN",             # CaptureCaptain (Falcon grab)
    276: "CAPTURE_YOSHI",               # CaptureYoshi (Yoshi neutral-B tongue)
    277: "YOSHI_EGG",                   # YoshiEgg (in Yoshi's egg)
    278: "CAPTURE_KOOPA",               # CaptureKoopa (Bowser side-B ground)
    279: "CAPTURE_DAMAGE_KOOPA",        # CaptureDamageKoopa
    280: "CAPTURE_WAIT_KOOPA",          # CaptureWaitKoopa
    281: "THROWN_KOOPA_F",              # ThrownKoopaF
    282: "THROWN_KOOPA_B",              # ThrownKoopaB
    283: "CAPTURE_KOOPA_AIR",           # CaptureKoopaAir (Bowser side-B air)
    284: "CAPTURE_DAMAGE_KOOPA_AIR",    # CaptureDamageKoopaAir
    285: "CAPTURE_WAIT_KOOPA_AIR",      # CaptureWaitKoopaAir
    286: "THROWN_KOOPA_AIR_F",          # ThrownKoopaAirF
    287: "THROWN_KOOPA_AIR_B",          # ThrownKoopaAirB
    288: "CAPTURE_KIRBY",               # CaptureKirby (Kirby neutral-B inhale)
    289: "CAPTURE_WAIT_KIRBY",          # CaptureWaitKirby
    290: "THROWN_KIRBY_STAR",           # ThrownKirbyStar
    291: "THROWN_COPY_STAR",            # ThrownCopyStar
    292: "THROWN_KIRBY",                # ThrownKirby

    # --- Barrel / Bury / Status (293-300) ---
    293: "BARREL_WAIT",                 # BarrelWait
    294: "BURY",                        # Bury (buried in ground, e.g., DK side-B)
    295: "BURY_WAIT",                   # BuryWait
    296: "BURY_JUMP",                   # BuryJump
    297: "DAMAGE_SONG",                 # DamageSong (Jigglypuff sing)
    298: "DAMAGE_SONG_WAIT",            # DamageSongWait
    299: "DAMAGE_SONG_RV",              # DamageSongRv
    300: "DAMAGE_BIND",                 # DamageBind (Mewtwo disable)

    # --- Mewtwo Capture (301-304) ---
    301: "CAPTURE_MEWTWO",              # CaptureMewtwo
    302: "CAPTURE_MEWTWO_AIR",          # CaptureMewtwoAir
    303: "THROWN_MEWTWO",               # ThrownMewtwo
    304: "THROWN_MEWTWO_AIR",           # ThrownMewtwoAir

    # --- Warp Star (305-306) ---
    305: "WARP_STAR_JUMP",              # WarpStarJump
    306: "WARP_STAR_FALL",              # WarpStarFall

    # --- Hammer Item (307-313) ---
    307: "HAMMER_WAIT",                 # HammerWait
    308: "HAMMER_WALK",                 # HammerWalk
    309: "HAMMER_TURN",                 # HammerTurn
    310: "HAMMER_KNEE_BEND",            # HammerKneeBend
    311: "HAMMER_FALL",                 # HammerFall
    312: "HAMMER_JUMP",                 # HammerJump
    313: "HAMMER_LANDING",              # HammerLanding

    # --- Mushroom / Size Change (314-321) ---
    314: "KINOKO_GIANT_START",          # KinokoGiantStart (super mushroom start)
    315: "KINOKO_GIANT_START_AIR",      # KinokoGiantStartAir
    316: "KINOKO_GIANT_END",            # KinokoGiantEnd
    317: "KINOKO_GIANT_END_AIR",        # KinokoGiantEndAir
    318: "KINOKO_SMALL_START",          # KinokoSmallStart (poison mushroom start)
    319: "KINOKO_SMALL_START_AIR",      # KinokoSmallStartAir
    320: "KINOKO_SMALL_END",            # KinokoSmallEnd
    321: "KINOKO_SMALL_END_AIR",        # KinokoSmallEndAir

    # --- Entry / Spawn (322-324) ---
    322: "ENTRY",                       # Entry
    323: "ENTRY_START",                 # EntryStart
    324: "ENTRY_END",                   # EntryEnd

    # --- Ice Damage (325-326) ---
    325: "DAMAGE_ICE",                  # DamageIce (frozen)
    326: "DAMAGE_ICE_JUMP",             # DamageIceJump (break out of freeze)

    # --- Master Hand / Crazy Hand Capture (327-339) ---
    327: "CAPTURE_MASTER_HAND",         # CaptureMasterhand
    328: "CAPTURE_DAMAGE_MASTER_HAND",  # CapturedamageMasterhand
    329: "CAPTURE_WAIT_MASTER_HAND",    # CapturewaitMasterhand
    330: "THROWN_MASTER_HAND",          # ThrownMasterhand
    331: "CAPTURE_KIRBY_YOSHI",         # CaptureKirbyYoshi
    332: "KIRBY_YOSHI_EGG",             # KirbyYoshiEgg
    333: "CAPTURE_REDEAD",              # CaptureLeadead (ReDead grab in adventure)
    334: "CAPTURE_LIKE_LIKE",           # CaptureLikelike (Like Like grab in adventure)
    335: "DOWN_REFLECT",                # DownReflect
    336: "CAPTURE_CRAZY_HAND",          # CaptureCrazyhand
    337: "CAPTURE_DAMAGE_CRAZY_HAND",   # CapturedamageCrazyhand
    338: "CAPTURE_WAIT_CRAZY_HAND",     # CapturewaitCrazyhand
    339: "THROWN_CRAZY_HAND",           # ThrownCrazyhand

    # --- Barrel Cannon (340) ---
    340: "BARREL_CANNON_WAIT",          # BarrelCannonWait

    # --- Idle Variations (341-344) ---
    341: "WAIT_1",                      # Wait1 (idle animation variation 1)
    342: "WAIT_2",                      # Wait2 (idle animation variation 2)
    343: "WAIT_3",                      # Wait3 (idle animation variation 3)
    344: "WAIT_4",                      # Wait4 (idle animation variation 4)

    # --- Wait with Item / Crouch Wait Variations (345-348) ---
    345: "WAIT_ITEM",                   # WaitItem
    346: "SQUAT_WAIT_1",                # SquatWait1 (crouch wait variation 1)
    347: "SQUAT_WAIT_2",                # SquatWait2 (crouch wait variation 2)
    348: "SQUAT_WAIT_ITEM",             # SquatWaitItem

    # --- Shield Damage / Spot Dodge Variant (349-350) ---
    349: "GUARD_DAMAGE",                # GuardDamage (shield hit)
    350: "ESCAPE_N",                    # EscapeN (spot dodge variant)

    # --- Smash Hold / Heavy Walk (351-353) ---
    351: "ATTACK_S_4_HOLD",             # AttackS4Hold (f-smash charge hold)
    352: "HEAVY_WALK_1",                # HeavyWalk1
    353: "HEAVY_WALK_2",                # HeavyWalk2

    # --- Item Hammer / Blind (354-356) ---
    354: "ITEM_HAMMER_WAIT",            # ItemHammerWait
    355: "ITEM_HAMMER_MOVE",            # ItemHammerMove
    356: "ITEM_BLIND",                  # ItemBlind

    # --- Electric Damage / Sleep (357-360) ---
    357: "DAMAGE_ELEC",                 # DamageElec (electric shock)
    358: "FURA_SLEEP_START",            # FuraSleepStart (sleep start from Sing/Rest)
    359: "FURA_SLEEP_LOOP",             # FuraSleepLoop (sleeping)
    360: "FURA_SLEEP_END",              # FuraSleepEnd (wake up)

    # --- Wall Damage / Cliff Wait Variations (361-363) ---
    361: "WALL_DAMAGE",                 # WallDamage
    362: "CLIFF_WAIT_1",                # CliffWait1 (ledge hang variation)
    363: "CLIFF_WAIT_2",                # CliffWait2 (ledge hang variation)

    # --- Slip / Banana (364-372) ---
    364: "SLIP_DOWN",                   # SlipDown (slip / trip)
    365: "SLIP",                        # Slip
    366: "SLIP_TURN",                   # SlipTurn
    367: "SLIP_DASH",                   # SlipDash
    368: "SLIP_WAIT",                   # SlipWait
    369: "SLIP_STAND",                  # SlipStand
    370: "SLIP_ATTACK",                 # SlipAttack
    371: "SLIP_ESCAPE_F",               # SlipEscapeF
    372: "SLIP_ESCAPE_B",               # SlipEscapeB

    # --- Side Taunt / Misc (373-382) ---
    373: "APPEAL_S",                    # AppealS (side taunt)
    374: "ZITABATA",                    # Zitabata (struggling)
    375: "CAPTURE_KOOPA_HIT",           # CaptureKoopaHit
    376: "THROWN_KOOPA_END_F",          # ThrownKoopaEndF
    377: "THROWN_KOOPA_END_B",          # ThrownKoopaEndB
    378: "CAPTURE_KOOPA_AIR_HIT",       # CaptureKoopaAirHit
    379: "THROWN_KOOPA_AIR_END_F",      # ThrownKoopaAirEndF
    380: "THROWN_KOOPA_AIR_END_B",      # ThrownKoopaAirEndB
    381: "THROWN_KIRBY_DRINK_S_SHOT",   # ThrownKirbyDrinkSShot
    382: "THROWN_KIRBY_SPIT_S_SHOT",    # ThrownKirbySpitSShot
}


# =============================================================================
# Reverse lookup: name -> ID
# =============================================================================

ACTION_STATE_BY_NAME: dict[str, int] = {v: k for k, v in ACTION_STATES.items()}


# =============================================================================
# Categorized subsets for analysis convenience
# =============================================================================

ACTION_STATE_CATEGORIES: dict[str, set[int]] = {
    "dead": set(range(0, 11)),
    "spawn": {11, 12, 13, 322, 323, 324},
    "idle": {14, 341, 342, 343, 344, 345},
    "walk": {15, 16, 17},
    "dash_run": {20, 21, 22, 23},
    "turn": {18, 19},
    "jumpsquat": {24},
    "jump": {25, 26, 27, 28},
    "fall": {29, 30, 31, 32, 33, 34},
    "fall_special": {35, 36, 37},  # helpless
    "tumble": {38},
    "crouch": {39, 40, 41, 346, 347, 348},
    "landing": {42, 43},
    "jab": {44, 45, 46, 47, 48, 49},
    "dash_attack": {50},
    "ftilt": {51, 52, 53, 54, 55},
    "utilt": {56},
    "dtilt": {57},
    "fsmash": {58, 59, 60, 61, 62, 351},  # includes hold
    "usmash": {63},
    "dsmash": {64},
    "nair": {65},
    "fair": {66},
    "bair": {67},
    "uair": {68},
    "dair": {69},
    "aerial": {65, 66, 67, 68, 69},
    "aerial_landing": {70, 71, 72, 73, 74},
    "ground_attack": {44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57,
                      58, 59, 60, 61, 62, 63, 64},
    "damage_ground": {75, 76, 77, 78, 79, 80, 81, 82, 83},  # grounded hitstun
    "damage_air": {84, 85, 86},  # aerial hitstun
    "damage_fly": {87, 88, 89, 90, 91},  # knockback
    "damage": set(range(75, 92)) | {357},  # all hitstun + electric
    "shield": {178, 179, 180, 349},
    "shield_stun": {181},
    "powershield": {182},
    "shield_break": {205, 206, 207, 208, 209, 210, 211},
    "roll": {233, 234},
    "spotdodge": {235, 350},
    "airdodge": {236},
    "dodge": {233, 234, 235, 236, 350},
    "grab": {212, 213, 214, 215},
    "grab_hold": {216, 217, 218},
    "throw": {219, 220, 221, 222},
    "grabbed": {223, 224, 225, 226, 227, 228, 229, 230, 231, 232},
    "being_thrown": {239, 240, 241, 242, 243},
    "tech": {199, 200, 201},
    "wall_tech": {202, 203},
    "ceiling_tech": {204},
    "missed_tech_up": {183, 184, 185, 186, 187, 188, 189, 190},
    "missed_tech_down": {191, 192, 193, 194, 195, 196, 197, 198},
    "getup_attack": {187, 195},
    "ledge": {252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 362, 363},
    "ledge_grab": {252},
    "ledge_hang": {253, 362, 363},
    "ledge_getup": {254, 255},
    "ledge_attack": {256, 257},
    "ledge_roll": {258, 259},
    "ledge_jump": {260, 261, 262, 263},
    "teeter": {245, 246},
    "taunt": {264, 265, 373},
    "platform_drop": {244},
    "edge_slip": {251},
    "frozen": {325, 326},
    "sleep": {297, 298, 299, 358, 359, 360},
    "buried": {294, 295, 296},
    "actionable": {14, 40, 179, 253, 341, 342, 343, 344},  # states where player can act
}


# =============================================================================
# Friendly name mapping for common gameplay analysis
# =============================================================================

FRIENDLY_NAMES: dict[int, str] = {
    14: "Idle",
    15: "Walk (slow)", 16: "Walk (mid)", 17: "Walk (fast)",
    18: "Turn", 19: "Run turn",
    20: "Dash", 21: "Run", 23: "Run brake",
    24: "Jumpsquat",
    25: "Jump (forward)", 26: "Jump (backward)",
    27: "Double jump (forward)", 28: "Double jump (backward)",
    29: "Fall", 35: "Helpless fall", 38: "Tumble",
    39: "Crouch start", 40: "Crouching", 41: "Crouch end",
    42: "Landing", 43: "Special landing lag",
    44: "Jab 1", 45: "Jab 2", 46: "Jab 3",
    47: "Rapid jab start", 48: "Rapid jab loop", 49: "Rapid jab end",
    50: "Dash attack",
    53: "F-tilt", 56: "Up tilt", 57: "Down tilt",
    60: "F-smash", 63: "Up smash", 64: "Down smash", 351: "F-smash (charge)",
    65: "Nair", 66: "Fair", 67: "Bair", 68: "Up air", 69: "Down air",
    70: "Nair landing", 71: "Fair landing", 72: "Bair landing",
    73: "Up air landing", 74: "Down air landing",
    178: "Shield startup", 179: "Shielding", 180: "Shield drop",
    181: "Shield stun", 182: "Powershield", 349: "Shield hit",
    199: "Tech in place", 200: "Tech roll forward", 201: "Tech roll backward",
    202: "Wall tech", 203: "Wall tech jump", 204: "Ceiling tech",
    183: "Missed tech (face up)", 191: "Missed tech (face down)",
    186: "Getup (face up)", 194: "Getup (face down)",
    187: "Getup attack (face up)", 195: "Getup attack (face down)",
    211: "Shield broken (dazed)",
    212: "Grab", 214: "Dash grab", 216: "Grab hold", 217: "Pummel",
    219: "Forward throw", 220: "Back throw", 221: "Up throw", 222: "Down throw",
    229: "Grab escape",
    233: "Roll forward", 234: "Roll backward", 235: "Spot dodge", 236: "Air dodge",
    244: "Platform drop", 245: "Teetering",
    252: "Ledge grab", 253: "Ledge hang",
    254: "Ledge getup (slow)", 255: "Ledge getup (fast)",
    256: "Ledge attack (slow)", 257: "Ledge attack (fast)",
    258: "Ledge roll (slow)", 259: "Ledge roll (fast)",
    260: "Ledge jump (slow)", 262: "Ledge jump (fast)",
    264: "Taunt",
    325: "Frozen", 358: "Asleep",
}


if __name__ == "__main__":
    print(f"Total action states: {len(ACTION_STATES)}")
    print(f"Categories: {len(ACTION_STATE_CATEGORIES)}")
    print()
    for state_id in sorted(ACTION_STATES.keys()):
        friendly = FRIENDLY_NAMES.get(state_id, "")
        suffix = f"  ({friendly})" if friendly else ""
        print(f"  {state_id:>3d} (0x{state_id:03X})  {ACTION_STATES[state_id]}{suffix}")
