import copy
from random import choice, shuffle
from typing import List, Tuple, Dict, Any, Optional

# --- Constants ---
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

# Templates for 4x4 grid structure
BEGIN_ROW_4x4: List[int] = [2,0,0,0,0,0,0,0,66,66,66,66,66,66,0,0,0,0,29,48,0,27]
MID_ROWS_TEMPLATE_4x4: List[List[int]] = [
    [15,20,0,0,0,0,0,0,66, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, 66,0,0,0,0,30,48,0,27],
    [7,9,0,0,0,0,0,0,66, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, 66,0,0,0,0,31,48,0,28],
    [7,13,0,0,0,0,0,0,66, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, 66,0,0,0,0,32,48,0,29],
    [12,5,0,0,0,0,0,0,66, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, LETTER_PLACEHOLDER, 66,0,0,0,0,33,48,0,31]
]
END_ROW_4x4: List[int] = [5,0,0,0,0,0,0,0,66,66,66,66,66,66,0,0,0,0,34,48,27,27]

# Templates for 5x5 grid structure (Note: No separate 'begin' row was used in original logic for size 5)
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
        "begin_row": BEGIN_ROW_4x4,
        "mid_rows": MID_ROWS_TEMPLATE_4x4,
        "end_row": END_ROW_4x4
    },
    5: {
        "dice": BOGGLE_DICE_5x5,
        "begin_row": None, # No separate begin row for 5x5 in original logic
        "mid_rows": MID_ROWS_TEMPLATE_5x5,
        "end_row": END_ROW_5x5
    }
}

# --- Refactored Function ---
def generate_boggle_grids(size: int) -> Tuple[List[List[int]], List[List[int]]]:
    """
    Generates 'start' and 'end' grid representations for a Boggle game.

    The function selects the appropriate dice set and grid template based on the
    specified size (4 for 4x4, 5 for 5x5). It "rolls" the dice, converts
    letters to numbers (A=1, B=2,...), and populates the grid template.
    Two grids are returned:
    - 'start_grid': Contains the rolled letter numbers and initial boundary markers.
    - 'end_grid': A copy of the start grid where boundary markers are modified.

    Args:
        size: The dimension of the Boggle board (must be 4 or 5).

    Returns:
        A tuple containing two grids (lists of lists of integers):
        (start_grid, end_grid)

    Raises:
        ValueError: If the provided size is not supported (not in BOGGLE_CONFIG).
        RuntimeError: If there aren't enough letters generated to fill placeholders.
    """
    if size not in BOGGLE_CONFIG:
        raise ValueError(f"Unsupported Boggle size: {size}. Supported sizes are {list(BOGGLE_CONFIG.keys())}")

    config = BOGGLE_CONFIG[size]
    dice_set = config["dice"]
    begin_row_template = config["begin_row"]
    mid_rows_template = config["mid_rows"]
    end_row_template = config["end_row"]

    # --- Roll the Dice ---
    # Create a copy to shuffle without modifying the original constant list
    shuffled_dice = dice_set[:]
    shuffle(shuffled_dice)

    # Roll one letter from each die
    letters = [choice(die) for die in shuffled_dice]

    # Convert letters to numbers (A=1, B=2, ..., Z=26)
    letter_numbers = [ord(letter.lower()) - ASCII_LOWERCASE_OFFSET for letter in letters]

    # Create a mutable copy to consume numbers as they are placed
    available_numbers = letter_numbers[:]

    # --- Populate the Mid Rows Template ---
    # Use deepcopy to avoid modifying the original template definition
    populated_mid_rows = copy.deepcopy(mid_rows_template)

    for row_index, row in enumerate(populated_mid_rows):
        for col_index, cell_value in enumerate(row):
            if cell_value == LETTER_PLACEHOLDER:
                if not available_numbers:
                    # Should not happen if template placeholders match dice count
                    raise RuntimeError("Mismatch between dice count and grid placeholders.")
                # Take a random number from the available pool (mimics original 'choice')
                chosen_number = choice(available_numbers)
                populated_mid_rows[row_index][col_index] = chosen_number
                available_numbers.remove(chosen_number) # Remove the used number

    # --- Assemble the Start Grid ---
    start_grid: List[List[int]] = []
    # Add the begin row only if it's defined for this size (i.e., size 4)
    if begin_row_template:
        start_grid.append(copy.deepcopy(begin_row_template)) # Use deepcopy for safety

    start_grid.extend(populated_mid_rows) # Add the populated middle rows
    start_grid.append(copy.deepcopy(end_row_template)) # Add the end row (use deepcopy)

    # --- Create the End Grid ---
    # Start with a deep copy of the start_grid
    end_grid = copy.deepcopy(start_grid)
    # Modify the boundary markers in the end_grid
    for row in end_grid:
        for col_index, cell_value in enumerate(row):
            if cell_value == BOUNDARY_START:
                row[col_index] = BOUNDARY_END

    return start_grid, end_grid