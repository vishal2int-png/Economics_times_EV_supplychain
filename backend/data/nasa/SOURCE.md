# NASA PCoE Li-ion Battery Aging Dataset

## Provenance

- **Origin:** NASA Ames Prognostics Center of Excellence (PCoE), Li-ion Battery
  Aging Datasets.
- **Retrieved via:** community mirror at
  `github.com/natskiu/Nasa-Battery` (`processed_csv/`), because NASA's own
  Open Data Portal page for this dataset no longer serves the files.
- **License:** CC0 / public domain (NASA-originated).
- **Cite as:** "NASA PCoE Li-ion Battery Aging Dataset (via community mirror)."
  Do **not** describe this as a live or direct NASA feed.

## What is here

Four 18650 Li-ion cells cycled to failure at room temperature — the benchmark
set used across the RUL-prediction literature.

| Cell  | Cycles | Initial capacity (Ah) | Final capacity (Ah) | Fade |
|-------|--------|-----------------------|---------------------|------|
| B0005 | 168    | 1.856                 | 1.325               | 28.6% |
| B0006 | 168    | 2.035                 | 1.186               | 41.7% |
| B0007 | 168    | 1.891                 | 1.432               | 24.3% |
| B0018 | 132    | 1.855                 | 1.341               | 27.7% |

Cells are rated 2.0 Ah nominal. SoH is computed against that rating.

Relevant columns:

- `capacity` — measured discharge capacity (Ah) for that cycle
- `remaining_cycles` — ground-truth remaining useful life, in cycles
- `max_temp_D`, `slope_temp_D` — discharge thermal behaviour
- `max_temp_C` — charge thermal behaviour

## Cells deliberately excluded

The mirror also carries B0049–B0056. These are **not** included, for cause:

- **B0050** terminates at a measured capacity of 0.000 Ah (truncated/corrupt).
- **B0051, B0054, B0055, B0056** show capacity *increasing* across the test
  (−5% to −44% "fade"). These are low-ambient protocols (4–22 °C) where
  measured capacity recovers; they are not monotonic degradation curves and
  would corrupt a degradation validation.
- **B0053** shows only 5.5% fade over 55 cycles — too little signal to
  validate an end-of-life forecast against.

Verified on download: all four retained cells are monotonically decreasing in
capacity and sit in a 36–42 °C ambient band.
