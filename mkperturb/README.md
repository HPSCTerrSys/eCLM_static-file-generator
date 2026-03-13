# mkperturb — Soil property perturbation for eCLM ensembles

Generates an ensemble of perturbed eCLM surface files by randomising
soil properties. Each ensemble member is written as a separate NetCDF
file named after the input file with a zero-padded index appended
(e.g. `surfdata_..._00001.nc`).

Original author: Yorck Ewerdwalbesloh

## Requirements

- Python 3
- `numpy`
- `netCDF4`

## Usage

```
python perturb_soil_properties.py <input_file> <output_dir> [options]
```

### Positional arguments

| Argument     | Description                                               |
|--------------|-----------------------------------------------------------|
| `input_file` | Source eCLM surface file (NetCDF)                         |
| `output_dir` | Directory for output files (created if it does not exist) |

### General options

| Option                       | Default     | Description                                           |
|------------------------------|-------------|-------------------------------------------------------|
| `--mode {hydraulic,texture}` | `hydraulic` | Perturbation mode (see below)                         |
| `--start N`                  | `0`         | First ensemble member index (0-based)                 |
| `--count N`                  | `50`        | Number of ensemble members to generate                |
| `--seed N`                   | *(auto)*    | RNG seed; if omitted, one is generated and printed    |
| `--state-file FILE`          | *(none)*    | JSON file to save/restore RNG state for resuming runs |

### Perturbation parameters — hydraulic mode

Each hydraulic property is multiplied by a scalar drawn from N(1, std).

| Option                 | Default   | Description                                                |
|------------------------|-----------|------------------------------------------------------------|
| `--std-sucsat`         | `0.2`     | Std dev for saturated matric potential (PSIS_SAT_adj)      |
| `--std-watsat`         | `0.05`    | Std dev for porosity (THETAS_adj)                          |
| `--std-bsw`            | `0.1`     | Std dev for Clapp-Hornberger b parameter (SHAPE_PARAM_adj) |
| `--std-hksat`          | `0.1`     | Std dev for saturated hydraulic conductivity (KSAT_adj)    |
| `--max-watsat`         | `0.93`    | Upper clip for perturbed porosity                          |
| `--hksat-clip MIN MAX` | `0.5 2.0` | Clip bounds for the Ksat multiplicative factor             |
| `--n-perturb-levels N` | `25`      | Number of levels from the surface to perturb; deeper levels receive unperturbed CLM mean values |

### Perturbation parameters — texture mode

| Option          | Default | Description                                                           |
|-----------------|---------|-----------------------------------------------------------------------|
| `--noise-range` | `10.0`  | Half-range of uniform noise added to sand/clay/OM (percentage points) |

## Perturbation modes

### `hydraulic` (default)

Soil hydraulic properties are computed from the Clapp-Hornberger
pedotransfer functions as implemented in CLM5, adjusted for organic
matter content, and then multiplied by a spatially uniform scalar
random factor. Four new variables are added to each output file:
`PSIS_SAT_adj`, `THETAS_adj`, `SHAPE_PARAM_adj`, and `KSAT_adj`,
defined on the full CLM ground layer grid (25 levels). All original
variables are copied unchanged.

The perturbation is applied only to the uppermost `--n-perturb-levels`
levels (default: all 25). Deeper levels receive the unperturbed CLM
mean values, ensuring all levels always contain physically consistent
data.

### `texture`

Sand (`PCT_SAND`), clay (`PCT_CLAY`), and organic matter (`ORGANIC`)
fractions are perturbed by adding a spatially uniform scalar drawn
from a uniform distribution. Physical constraints (non-negativity,
sand + clay ≤ 100 %) are enforced after perturbation.

## Reproducibility

If `--seed` is not provided, a random seed is generated and printed to
stdout so any run can be reproduced exactly by passing that
seed. Alternatively, `--state-file` saves the full NumPy RNG state
after the run and restores it at the start, which also enables
resuming an interrupted run:

```bash
# Start a run, save state
python perturb_soil_properties.py surfdata.nc ./ensemble --count 50 --state-file run.json

# Resume from member 50
python perturb_soil_properties.py surfdata.nc ./ensemble --start 50 --count 150 --state-file run.json
```

## Examples

```bash
# 50-member hydraulic ensemble with default settings
python perturb_soil_properties.py surfdata.nc ./ensemble/

# Reproducible run with a fixed seed
python perturb_soil_properties.py surfdata.nc ./ensemble/ --seed 42

# Texture perturbation, 100 members, ±5 % noise
python perturb_soil_properties.py surfdata.nc ./ensemble/ --mode texture --count 100 --noise-range 5

# Hydraulic ensemble with wider spread on Ksat
python perturb_soil_properties.py surfdata.nc ./ensemble/ --std-hksat 0.25 --hksat-clip 0.2 5.0

# Perturb only the top 10 levels; deeper levels get unperturbed mean values
python perturb_soil_properties.py surfdata.nc ./ensemble/ --n-perturb-levels 10
```
