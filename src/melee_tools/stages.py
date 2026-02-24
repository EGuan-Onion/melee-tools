"""Stage geometry data for competitive Melee stages.

Provides ledge X positions used for offstage detection.
A player is offstage when abs(position_x) > edge_x or position_y < -10.
"""

STAGE_GEOMETRY = {
    2:  {"name": "Fountain of Dreams", "edge_x": 63.35},
    3:  {"name": "Pokemon Stadium",    "edge_x": 87.75},
    8:  {"name": "Yoshi's Story",      "edge_x": 56.0},
    28: {"name": "Dream Land N64",     "edge_x": 77.27},
    31: {"name": "Battlefield",        "edge_x": 68.4},
    32: {"name": "Final Destination",  "edge_x": 85.57},
}
