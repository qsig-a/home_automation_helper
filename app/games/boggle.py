from random import choice, shuffle
from typing import List, Tuple, Dict, Any

# --- Constants ---
# These constants define the character codes for the Vestaboard.
LETTER_PLACEHOLDER = 1  # Indicates where a rolled letter should be placed
BOUNDARY_START = 66     # Initial value for boundary cells in the 'start' grid
BOUNDARY_END = 63       # Value for boundary cells in the 'end' grid
EMPTY_CELL = 0          # Represents an empty cell in the template
ASCII_LOWERCASE_OFFSET = 96 # Offset to convert 'a'..'z' to 1..26 (ord('a') - 1)

# --- Boggle Dice Definitions ---
BOGGLE_DICE_4x4: List[List[str]] = [
    ["A","E","A","N","E","G"], ["A","H","S","P","C","O"], ["A","B","B","J","O","O"],
    ["A","F","F","K","P","S"], ["A","O","O","T","T","W"], ["C","I","M","O","T","U"],
    ["D","E","I","L","R","X"], ["D","E","L","R","V","Y"], ["D","I","S","T","T","Y"],
    ["E","E","G","H","N","W"], ["E","E","I","N","S","U"], ["E","H","R","T","V","W"],
    ["E","I","O","S","S","T"], ["E","L","R","T","T","Y"], ["H","I","M","N","U","T"],
    ["H","L","N","N","R","Z"]
]

BOGGLE_DICE_5x5: List[List[str]] = [
    ["Q","B","Z","J","X","K"], ["H","H","L","R","D","C"], ["T","E","L","P","C","I"],
    ["T","T","O","T","E","M"], ["A","E","A","E","E","E"], ["T","O","U","O","T","C"],
    ["N","H","D","T","H","C"], ["S","S","N","S","E","U"], ["S","C","T","I","E","P"],
    ["Y","I","F","P","S","R"], ["O","V","W","R","G","R"], ["L","H","N","R","O","D"],
    ["R","I","Y","P","R","H"], ["E","A","N","D","N","N"], ["E","E","E","E","M","A"],
    ["A","A","A","F","S","R"], ["A","F","A","I","S","R"], ["D","O","R","D","L","N"],
    ["M","N","N","E","A","G"], ["I","T","I","T","I","E"], ["A","U","M","E","E","G"],
    ["Y","I","F","A","S","R"], ["C","C","W","N","S","T"], ["U","O","T","O","W","N"],
    ["E","T","I","L","I","C"]
]

# --- Vestaboard Grid Templates ---
# These templates define the structure of the Boggle grid on the Vestaboard.
# The numbers are character codes specific to the Vestaboard API.
BEGIN_ROW_4x4: List[int] = [2,0,0,0,0,0,0,0,66,66,66,66,66,66,0,0,0,0,29,48,0,27]
MID_ROWS_TEMPLATE_4x4: List[List[int]] = [
    [15,20,0,0,0,0,0,0,66, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, 66,0,0,0,0,30,48,0,27],
    [7,9,0,0,0,0,0,0,66, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, 66,0,0,0,0,31,48,0,28],
    [7,13,0,0,0,0,0,0,66, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, 66,0,0,0,0,32,48,0,29],
    [12,5,0,0,0,0,0,0,66, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, 66,0,0,0,0,33,48,0,31]
]
END_ROW_4x4: List[int] = [5,0,0,0,0,0,0,0,66,66,66,66,66,66,0,0,0,0,34,48,27,27]

MID_ROWS_TEMPLATE_5x5: List[List[int]] = [
    [2,0,0,0,0,0,0,66, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, 66,0,0,0,0,29,48,0,27],
    [15,20,0,0,0,0,0,66, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, 66,0,0,0,0,30,48,0,27],
    [7,9,0,0,0,0,0,66, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, 66,0,0,0,0,31,48,0,28],
    [7,13,0,0,0,0,0,66, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, 66,0,0,0,0,32,48,0,29],
    [12,5,0,0,0,0,0,66, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, 66,0,0,0,0,33,48,0,31]
]
END_ROW_5x5: List[int] = [5,0,0,0,0,0,0,66,66,66,66,66,66,66,0,0,0,0,34,48,27,27]

# --- Configuration Dictionary ---
BOGGLE_CONFIG: Dict[int, Dict[str, Any]] = {
    4: {
        "dice": BOGGLE_DICE_4x4,
        "dice_int": [[ord(c.lower()) - ASCII_LOWERCASE_OFFSET for c in die] for die in BOGGLE_DICE_4x4],
        "begin_row": BEGIN_ROW_4x4,
        "mid_rows": MID_ROWS_TEMPLATE_4x4,
        "placeholders": [(r, c) for r, row in enumerate(MID_ROWS_TEMPLATE_4x4) for c, cell in enumerate(row) if cell == LETTER_PLACEHOLDER],
        "end_row": END_ROW_4x4
    },
    5: {
        "dice": BOGGLE_DICE_5x5,
        "dice_int": [[ord(c.lower()) - ASCII_LOWERCASE_OFFSET for c in die] for die in BOGGLE_DICE_5x5],
        "begin_row": None, # No separate begin row for 5x5 in original logic
        "mid_rows": MID_ROWS_TEMPLATE_5x5,
        "placeholders": [(r, c) for r, row in enumerate(MID_ROWS_TEMPLATE_5x5) for c, cell in enumerate(row) if cell == LETTER_PLACEHOLDER],
        "end_row": END_ROW_5x5
    }
}

def _roll_dice_and_get_letters(dice_set_int: List[List[int]]) -> List[int]:
    """Rolls the dice and returns a list of letter numbers."""
    return [choice(die) for die in dice_set_int]

def _populate_grid(template: List[List[int]], letters: List[int], placeholders: List[Tuple[int, int]]) -> List[List[int]]:
    """Populates a grid template with letters."""
    # ⚡ Bolt: Using list comprehension instead of deepcopy for performance
    populated_grid = [row[:] for row in template]

    if len(letters) < len(placeholders):
        raise RuntimeError("Not enough letters for placeholders.")
    if len(letters) > len(placeholders):
        raise RuntimeError("More letters than placeholders.")

    # ⚡ Bolt: letters is already a uniquely generated list from _roll_dice_and_get_letters, modify in-place
    shuffle(letters)

    for i, (r, c) in enumerate(placeholders):
        populated_grid[r][c] = letters[i]

    return populated_grid

def _create_end_grid(start_grid: List[List[int]]) -> List[List[int]]:
    """Creates the end grid by modifying boundary markers."""
    # ⚡ Bolt: Using nested list comprehension for C-speed iteration, replacing Python for loops
    return [[BOUNDARY_END if cell == BOUNDARY_START else cell for cell in row] for row in start_grid]

def generate_boggle_grids(size: int) -> Tuple[List[List[int]], List[List[int]]]:
    """
    Generates 'start' and 'end' grid representations for a Boggle game.
    """
    if size not in BOGGLE_CONFIG:
        raise ValueError(f"Unsupported Boggle size: {size}.")

    config = BOGGLE_CONFIG[size]
    # ⚡ Bolt: Use precomputed integer dice and placeholder coordinates for O(1) lookups
    letter_numbers = _roll_dice_and_get_letters(config["dice_int"])
    populated_mid_rows = _populate_grid(config["mid_rows"], letter_numbers, config["placeholders"])

    start_grid: List[List[int]] = []
    # ⚡ Bolt: Using slice [:] instead of deepcopy for performance
    if config["begin_row"]:
        start_grid.append(config["begin_row"][:])

    start_grid.extend(populated_mid_rows)
    start_grid.append(config["end_row"][:])

    end_grid = _create_end_grid(start_grid)

    return start_grid, end_grid