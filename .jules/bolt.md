## 2024-03-05 - MySQL ORDER BY RAND() Optimization
**Learning:** The legacy codebase used `ORDER BY RAND() LIMIT 1` on an inner `id` query. While this avoids full row scans by only selecting the `id`, it still requires an index scan and temporary sort of *every single ID* in the table, creating an O(N log N) bottleneck that gets linearly worse as the sayings/art tables grow.
**Action:** Replace `ORDER BY RAND()` with an O(1) mathematical index offset using `MAX(id)` and `MIN(id)` limits to jump directly to a random offset location via the primary key index.

## 2024-03-05 - Precomputing Game Board Coordinates
**Learning:** The legacy codebase for `generate_boggle_grids` was looping through a 6x22 Vestaboard grid to find the placeholder cells for dice letters every time a Boggle game started. It was also converting string dice representations (`"A"`) to integer codes dynamically on each generation. This was creating an O(R×C) search pattern and redundant `ord()` conversions for every game initialization.
**Action:** Move static grid configuration into pre-computed module-level state. Pre-calculate the dice integers `[[ord(c.lower()) - offset ...]]` and the placeholder grid coordinates `[(r, c) ...]` at import time, reducing `generate_boggle_grids` to an O(N) assignment operation where N is the number of dice.

## 2024-03-05 - Method Lookup Overhead in Python Loops
**Learning:** Python has measurable overhead for method lookups (like `dict.get()`) when called in tight loops. In `app/connectors/vestaboard.py`'s text-to-array conversion, calling `CHAR_CODE_MAP.get(char, 0)` for every character in a message was causing unnecessary slowdowns.
**Action:** Pull frequently used methods or properties out of the loop into local variables (e.g., `get_code = CHAR_CODE_MAP.get`) and call the local variable directly. This structural refactoring, along with condensing bounds-checking logic, can yield >50% performance improvements in string parsing algorithms.

## 2024-03-05 - Avoid Manual Coordinate Tracking in Python Loops
**Learning:** The `convert_text_to_array` method maintained an explicit `row` and `col` coordinate variable while iterating through each character. These manual loop invariants and explicit coordinate checks for bounds (like `row >= 6`) incur a high overhead per iteration. Re-writing string parsing to leverage Python's optimized list slicing, comprehensions, and `.extend()` methods is significantly faster.
**Action:** Replace `for char in string:` iterations that manually track X/Y grids with line splits (`split('\n')`) and chunking comprehensions (`codes[i:i+22]`). This shifts the heavy lifting from Python bytecode to C-level list operations.

## 2024-03-05 - Bounded O(1) String Processing
**Learning:** When attempting to optimize Python loop bottlenecks with list comprehensions and generator patterns like `text.split('\n')`, it is critical to observe algorithmic complexity bounds. The original `convert_text_to_array` implementation maintained O(1) complexity relative to the input text length because it broke out early after parsing 132 characters (6 rows × 22 cols). The naïve "optimization" of splitting lines broke this bound, causing it to eagerly scan and allocate O(N) memory for arbitrarily large input strings before throwing it away.
**Action:** Always maintain early exit conditions. For finite buffers like a Vestaboard grid, pre-allocate a fixed-size 1D array (`codes = [0] * 132`) and manage a single pointer (`idx`). This preserves the strict O(1) early exit while eliminating multi-dimensional coordinate tracking overhead.

## 2024-03-05 - Avoid 'encode(errors="ignore")' for strict-length grid parsing
**Learning:** When parsing arbitrary text into a strictly bounded fixed-grid system (like the 6x22 Vestaboard array), using `text.encode('latin-1', errors='ignore')` to iterate through bytes instead of characters introduces a layout-breaking bug. Silently dropping characters (e.g., emojis or unsupported Unicode) changes the length of the string, left-shifting all subsequent text and ruining carefully padded layouts.
**Action:** Always maintain the exact character count of the input string when formatting for a physical grid. Iterate over characters using `ord(char)`, use a precomputed array lookup for valid ASCII/Latin-1 codes to maintain speed, and explicitly handle `IndexError` or out-of-bounds `ord` values by falling back to a blank placeholder tile (e.g., `0`), rather than dropping the character entirely.
