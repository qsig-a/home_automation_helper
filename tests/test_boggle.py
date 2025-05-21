import pytest
from app.games.boggle import generate_boggle_grids, BOGGLE_CONFIG, LETTER_PLACEHOLDER

# Simplified helper function to check basic grid properties
def _check_grid_structure(grid):
    assert isinstance(grid, list), "Grid should be a list."
    assert len(grid) == 6, "Grid should always have 6 rows for Vestaboard display."

    for i, row in enumerate(grid):
        assert isinstance(row, list), f"Row {i} in the grid should be a list."
        assert len(row) == 22, f"Row {i} should have 22 columns for Vestaboard display."
        for j, item in enumerate(row):
            assert isinstance(item, int), f"Grid item at ({i},{j}) should be an integer."

# Helper to extract only the Boggle letters from a 4x4 grid based on template
def _extract_letters_from_grid_4x4(grid):
    letters = []
    # For 4x4, letters are in rows defined by MID_ROWS_TEMPLATE_4x4
    # These correspond to grid rows 1, 2, 3, 4 (after the BEGIN_ROW_4x4)
    mid_row_templates = BOGGLE_CONFIG[4]["mid_rows"]
    grid_row_offset = 1 if BOGGLE_CONFIG[4]["begin_row"] else 0

    for template_r_idx, row_template in enumerate(mid_row_templates):
        actual_grid_row_idx = grid_row_offset + template_r_idx
        if actual_grid_row_idx < len(grid): # Ensure we don't go out of bounds
            grid_row = grid[actual_grid_row_idx]
            for template_c_idx, cell_template_value in enumerate(row_template):
                if cell_template_value == LETTER_PLACEHOLDER:
                    if template_c_idx < len(grid_row): # Ensure col index is valid
                        letters.append(grid_row[template_c_idx])
    return letters

# Helper to extract only the Boggle letters from a 5x5 grid based on template
def _extract_letters_from_grid_5x5(grid):
    letters = []
    # For 5x5, letters are in rows defined by MID_ROWS_TEMPLATE_5x5
    # These correspond to grid rows 0, 1, 2, 3, 4
    mid_row_templates = BOGGLE_CONFIG[5]["mid_rows"]
    grid_row_offset = 0 # No begin_row for 5x5

    for template_r_idx, row_template in enumerate(mid_row_templates):
        actual_grid_row_idx = grid_row_offset + template_r_idx
        if actual_grid_row_idx < len(grid):
            grid_row = grid[actual_grid_row_idx]
            for template_c_idx, cell_template_value in enumerate(row_template):
                if cell_template_value == LETTER_PLACEHOLDER:
                    if template_c_idx < len(grid_row):
                        letters.append(grid_row[template_c_idx])
    return letters


def test_generate_boggle_grids_size_4():
    """
    Tests generate_boggle_grids with size=4.
    - Verifies grid structure, dimensions, and that letters are valid.
    - Verifies that start_grid and end_grid are different due to boundary markers.
    """
    start_grid, end_grid = generate_boggle_grids(size=4)

    _check_grid_structure(start_grid)
    _check_grid_structure(end_grid)

    start_letters = _extract_letters_from_grid_4x4(start_grid)
    end_letters = _extract_letters_from_grid_4x4(end_grid)

    assert len(start_letters) == 16, "Should be 16 letters in a 4x4 Boggle grid."
    for letter_val in start_letters:
        assert 1 <= letter_val <= 26, f"Invalid letter value {letter_val} found in 4x4 start grid letters."
    
    assert start_letters == end_letters, "Boggle letters in start and end grids should be identical for size 4."
    
    # Verify that start_grid and end_grid are different (due to boundary markers)
    start_boundary_char = 66 # BOGGLE_CONFIG[4]["begin_row"][8] or similar fixed value from template
    end_boundary_char = 63   # As defined in generate_boggle_grids for end_grid modification

    start_grid_boundary_count = sum(row.count(start_boundary_char) for row in start_grid)
    end_grid_boundary_count = sum(row.count(end_boundary_char) for row in end_grid)
    
    # Ensure that the start grid has the start boundaries and not the end ones (for those positions)
    # And vice-versa for the end grid
    assert start_grid_boundary_count > 0, "Start grid should contain start boundary characters (66)."
    assert sum(row.count(end_boundary_char) for row in start_grid) == 0, "Start grid should not contain end boundary characters (63)."
    
    assert end_grid_boundary_count > 0, "End grid should contain end boundary characters (63)."
    assert sum(row.count(start_boundary_char) for row in end_grid) == 0, "End grid should not contain start boundary characters (66)."
    
    assert start_grid_boundary_count == end_grid_boundary_count, "Number of boundary markers should be consistent between start and end grids."


def test_generate_boggle_grids_size_5():
    """
    Tests generate_boggle_grids with size=5.
    - Verifies grid structure, dimensions, and that letters are valid.
    - Verifies that start_grid and end_grid are different due to boundary markers.
    """
    start_grid, end_grid = generate_boggle_grids(size=5)

    _check_grid_structure(start_grid)
    _check_grid_structure(end_grid)

    start_letters = _extract_letters_from_grid_5x5(start_grid)
    end_letters = _extract_letters_from_grid_5x5(end_grid)

    assert len(start_letters) == 25, "Should be 25 letters in a 5x5 Boggle grid."
    for letter_val in start_letters:
        assert 1 <= letter_val <= 26, f"Invalid letter value {letter_val} found in 5x5 start grid letters."

    assert start_letters == end_letters, "Boggle letters in start and end grids should be identical for size 5."

    # Verify that start_grid and end_grid are different (due to boundary markers)
    start_boundary_char = 66
    end_boundary_char = 63

    start_grid_boundary_count = sum(row.count(start_boundary_char) for row in start_grid)
    end_grid_boundary_count = sum(row.count(end_boundary_char) for row in end_grid)

    assert start_grid_boundary_count > 0, "Start grid should contain start boundary characters (66) for size 5."
    assert sum(row.count(end_boundary_char) for row in start_grid) == 0, "Start grid should not contain end boundary characters (63) for size 5."

    assert end_grid_boundary_count > 0, "End grid should contain end boundary characters (63) for size 5."
    assert sum(row.count(start_boundary_char) for row in end_grid) == 0, "End grid should not contain start boundary characters (66) for size 5."
    
    assert start_grid_boundary_count == end_grid_boundary_count, "Number of boundary markers should be consistent for size 5."


def test_generate_boggle_grids_invalid_size():
    """
    Tests generate_boggle_grids with an invalid size.
    - Asserts that a ValueError is raised.
    """
    with pytest.raises(ValueError) as excinfo:
        generate_boggle_grids(size=3)
    assert "Unsupported Boggle size: 3" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        generate_boggle_grids(size=0)
    assert "Unsupported Boggle size: 0" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        generate_boggle_grids(size=6) # Assuming only 4 and 5 are in BOGGLE_CONFIG
    assert "Unsupported Boggle size: 6" in str(excinfo.value)


# test_initial_boggle_setup can be removed or kept if desired
# def test_initial_boggle_setup():
#     assert True
