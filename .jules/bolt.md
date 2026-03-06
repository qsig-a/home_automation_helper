## 2024-03-05 - MySQL ORDER BY RAND() Optimization
**Learning:** The legacy codebase used `ORDER BY RAND() LIMIT 1` on an inner `id` query. While this avoids full row scans by only selecting the `id`, it still requires an index scan and temporary sort of *every single ID* in the table, creating an O(N log N) bottleneck that gets linearly worse as the sayings/art tables grow.
**Action:** Replace `ORDER BY RAND()` with an O(1) mathematical index offset using `MAX(id)` and `MIN(id)` limits to jump directly to a random offset location via the primary key index.

## 2024-03-05 - Precomputing Game Board Coordinates
**Learning:** The legacy codebase for `generate_boggle_grids` was looping through a 6x22 Vestaboard grid to find the placeholder cells for dice letters every time a Boggle game started. It was also converting string dice representations (`"A"`) to integer codes dynamically on each generation. This was creating an O(R×C) search pattern and redundant `ord()` conversions for every game initialization.
**Action:** Move static grid configuration into pre-computed module-level state. Pre-calculate the dice integers `[[ord(c.lower()) - offset ...]]` and the placeholder grid coordinates `[(r, c) ...]` at import time, reducing `generate_boggle_grids` to an O(N) assignment operation where N is the number of dice.

## 2024-03-05 - Method Lookup Overhead in Python Loops
**Learning:** Python has measurable overhead for method lookups (like `dict.get()`) when called in tight loops. In `app/connectors/vestaboard.py`'s text-to-array conversion, calling `CHAR_CODE_MAP.get(char, 0)` for every character in a message was causing unnecessary slowdowns.
**Action:** Pull frequently used methods or properties out of the loop into local variables (e.g., `get_code = CHAR_CODE_MAP.get`) and call the local variable directly. This structural refactoring, along with condensing bounds-checking logic, can yield >50% performance improvements in string parsing algorithms.
