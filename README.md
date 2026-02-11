# eCLM static file generator

[![docs](https://github.com/HPSCTerrSys/eCLM_static-file-generator/actions/workflows/doc.yml/badge.svg)](https://github.com/HPSCTerrSys/eCLM_static-file-generator/actions/workflows/doc.yml)

## Introduction

This repository shows how to generate curvilinear surface and domain fields for eCLM simulations.
The generator follows the official CLM-workflow but makes a few adaptions.

## Usage / Documentation

If on [JSC HPC](https://www.fz-juelich.de/en/jsc/), start with sourcing the provided environment file and set the raw data path:

```
source jsc.2024_Intel.sh
export CSMDATA="/p/scratch/cslts/shared_data/rlmod_eCLM/inputdata/" # this works for JSC users only
```

Otherwise you need to provide for the data and software environment yourself (as documented below).

Then please check the [generated documentation](https://hpscterrsys.github.io/eCLM_static-file-generator/INDEX.html) online, [generate a static version](docs/README.md) yourself or browse it locally: `$VISUAL docs/users_guide/?_*.md` with `$VISUAL` your editor or viewer of choice.

## License
eCLM static file generator is open source software and is licensed under an [MIT License](https://github.com/HPSCTerrSys/eCLM_static-file-generator/blob/master/LICENSE).
