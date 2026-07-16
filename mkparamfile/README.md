# eCLM Parameter file utility scripts

Utility scripts for adjusting the original CLM5/eCLM parameter file
from NCAR, checking parameter files and visualizing parameter files.

Obtaining the original file from NCAR / DataPub-FZJ:
```bash
wget -nv https://svn-ccsm-inputdata.cgd.ucar.edu/trunk/inputdata/lnd/clm2/paramdata/clm5_params.c171117.nc
## wget -nv https://datapub.fz-juelich.de/slts/eclm/inputdata/common/clm5_params.c171117.nc
```

Utility scripts (see headers for more documentation):

1) Adjusting

- `set_pftname.py`: Changing the name of a PFT
- `setup_new_vars.py`: Adding new variables to the parameter file

2) Checking

- `compare_params.py`: Compare parameter files (text output)

3) Visualizing

- `compare_paramfile.py`: HTML visual comparison of two parameter
  files
- `visualize_paramfile.py`: HTML visualization of eCLM parameter file
