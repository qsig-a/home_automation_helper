## 2024-05-24 - [Avoid over-optimizing regex]
**Learning:** Checking string characters with regex `re.match` is actually ~4x faster than using `set(text).issubset(_ALLOWED_SET)` in Python for moderate sized strings.
**Action:** Leave the `re.compile` checks alone in Python strings.

## 2024-05-24 - [Pre-calculating Structural Templates]
**Learning:** In dynamically constructed structural layouts like Vestaboard grids (6x22 arrays), dynamically merging components (headers, bodies, footers) and transforming boundaries on every request incurs significant O(R*C) allocation and iteration overhead.
**Action:** When the structural layout is static, pre-calculate the flat templates at module load time. Using pre-calculated absolute index maps alongside fast C-level shallow copies (`[row[:] for row in template]`) and updating both state grids simultaneously eliminates redundant iteration overhead.
