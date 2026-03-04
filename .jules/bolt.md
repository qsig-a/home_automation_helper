## 2024-03-05 - MySQL ORDER BY RAND() Optimization
**Learning:** The legacy codebase used `ORDER BY RAND() LIMIT 1` on an inner `id` query. While this avoids full row scans by only selecting the `id`, it still requires an index scan and temporary sort of *every single ID* in the table, creating an O(N log N) bottleneck that gets linearly worse as the sayings/art tables grow.
**Action:** Replace `ORDER BY RAND()` with an O(1) mathematical index offset using `MAX(id)` and `MIN(id)` limits to jump directly to a random offset location via the primary key index.
