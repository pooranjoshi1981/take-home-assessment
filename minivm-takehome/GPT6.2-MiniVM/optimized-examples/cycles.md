# Sample cycle comparison

Calculated on the bundled example data using the documented MiniVM cost model; these are not native VM timings or new native VM measurements.

All eight original cycle counts and ordered results matched the bundled expected JSON. Each optimized result matched the original, including column order and duplicate rows.

| Plan | Original | Optimized | Saved | Reduction |
|---|---:|---:|---:|---:|
| [q0001](q0001.mini) | 13,766 | 11,725 | 2,041 | 14.83% |
| [q0002](q0002.mini) | 3,617 | 3,527 | 90 | 2.49% |
| [q0003](q0003.mini) | 8,562 | 8,496 | 66 | 0.77% |
| [q0004](q0004.mini) | 18,442 | 13,582 | 4,860 | 26.35% |
| [q0005](q0005.mini) | 5,518 | 4,723 | 795 | 14.41% |
| [q0006](q0006.mini) | 6,338 | 6,168 | 170 | 2.68% |
| [q0007](q0007.mini) | 2,596 | 2,170 | 426 | 16.41% |
| [q0008](q0008.mini) | 1,524 | 1,249 | 275 | 18.04% |
| **Total** | 60,363 | 51,640 | 8,723 | 14.45% |

To reproduce from the parent directory, run `python build_examples.py` and then `python sample_cycles.py`. To confirm on the native VM, run `./evaluate ./optimize` from the assignment root on Linux or macOS.
