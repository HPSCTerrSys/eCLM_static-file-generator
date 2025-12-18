# Creation of gridfile #

First, we need to create a gridfile that describes our simulation domain.
These come in two resolutions: ~12 km resolution (EUR-R13B05) and ~3 km resolution (EUR-R13B07).
Choose one of these two grids if you want to use this with TSMP2.
In this guide the default is EUR-R13B05, meaning that you will end up with all low-resolution static files on the *icosahedral* grid if you do not modify any of the following commands or scripts.
For other purposes guidelines for the *rectilinear* and *curvilinear* grids are here as well.
A curvilinear grid is normally used for CLM5, and when you run eCLM stand-alone you might choose to use a curvilinear grid as well.

The relevant scripts to create the grid files are in `./mkmapgrids/`.
The gridfile will contain arrays of longitudes and latitudes of the gridboxes' centres and corners.
The simulation domain is the EURO-CORDEX pan-European domain, which at high latitudes, for the Earth's canonical curvilinear grid, has significant convergence of the zonal dimension with increasing latitude.
Therefore we *rotate* the grid (of a same size) centred at the equator to the pan-European domain.

Grid files are available on the JSC machines in the DETECT CentralDB below `/p/largedata2/detectdata/CentralDB/projects/z04/detect_grid_specs/grids/` (`$CSMDATA/detect_grid_specs/grids`).
This is part of a Git repository that is also available [here](https://gitlab.jsc.fz-juelich.de/detect/detect_z03_z04/detect_grid_specification).

## Rectilinear grid ##

You can create a SCRIP file from a *rectilinear grid* with `mkscrip_rect.py`.
The Python packages numpy, xarray and dask-expr need to be available.
They are loaded by the environment file `jsc.2024_Intel.sh` (sourced above).
On machines without the modules from the environment file, you can install the Python packages with `pip3`, probably best in a [virtual environment](https://docs.python.org/3/library/venv.html), if they are not all available as a package in your operating system.
The script was modified from `mesh_maker.py` from the CTSM repository to accept 2D lon / lat.
The main caveat is that the resulting surface files are in 1D which makes them harder to handle.
The python script `mkscrip_rect.py` can create SCRIP files including the calculation of corners.
It takes command line arguments like this:

```
./mkscrip_rect.py --ifile EUR-regLonLat01deg_1204x548_grid_inclbrz_v2.nc --ofile EUR-regLonLat01deg_659792_grid_SCRIP.nc --oformat SCRIP
```

`--help` provides additional information.

### Rectilinear grid II: Python script for direct SCRIP-grid-file generation ###

One can create a SCRIP file for a rectilinear script using the Python
script `mkmapgrids/mkscripgrid.py`.

For its usage, in particular setting inputs, please refer to the
script itself.

### Rectilinear grid III: External Perl script from CTSM/CLM5 repo ###

The following Perl script from CTSM/CLM5 provides an interface to
similar functionality as the Python script
`mkmapgrids/mkscripgrid.py`:

https://github.com/ESCOMP/CTSM/blob/994e02983cf557410fe455b6bd64ee61ca50d488/tools/site_and_regional/mknoocnmap.pl

## Curvilinear grid ##

eCLM can be used with a *curvilinear grid*.

You can, e.g., use the 450x438 gridfile including boundary relaxation zone, `EUR-11_450x438_grid_inclbrz13gp_v2.nc`, as the input file.
If you want a high-resolution curvilinear grid, use `EUR-0275_1600x1552_grid_inclbrz_v2.nc`.
However, in eCLM we use a slightly smaller domain, so you must truncate the files:

```
cd mkmapgrids/
ncks -d rlat,3,434 -d rlon,3,446 $CSMDATA/detect_grid_specs/grids/EUR-11_450x438_grid_inclbrz13gp_v2.nc EUR-11_444x432_grid_inclbrz13gp_v2.nc
ncks -d rlat,3,1548 -d rlon,3,1596 $CSMDATA/detect_grid_specs/grids/EUR-0275_1600x1552_grid_inclbrz_v2.nc EUR-0275_1594x1546_grid_inclbrz_v2.nc
```

At the moment SCRIP generation from curvilinear grids can be done and is tested to work with the NCAR Command Language (NCL), even though it is [deprecated](https://www.ncl.ucar.edu/open_letter_to_ncl_users.shtml).
NCL can be installed through Conda.
If you have no Conda yet on your system, you can install it, including the conda-forge channel, following [this guide](https://github.com/conda-forge/miniforge?tab=readme-ov-file#unix-like-platforms-macos-linux--wsl).
Then follow [this guide](https://yonsci.github.io/yon_academic/portfolio/portfolio-9/#installing-ncl) to install NCL.
The repository contains the NCL-script `mkscrip_curv.ncl` that can create a SCRIP file from a netCDF that contains the lat- and lon-center coordinates.
It is not necessary to provide the corners because the internal routine of NCL seems to calculate them correctly for the later steps.
Adapt the variable `f` in `mkscrip_curv.ncl` to your gridfile and execute:

```
conda activate NCL_environment
ncl mkscrip_curv.ncl
conda deactivate
conda deactivate
```

## Icosahedral grid ##

The atmospheric model ICON runs on an *icosahedral grid*, sometimes called *triangular grid*.
The land model eCLM, when coupled to ICON (in TSMP2), also uses this grid.

Check out https://zonda.ethz.ch/ for generating icosahedral input grids for `mkscrip_icos.py` (specified under option `--ifile`).

Then convert your ICON gridfile to the SCRIP format with the python script `mkscrip_icos.py`:

```
./mkscrip_icos.py --ifile EUR-R13B05_199920_grid_inclbrz_v2.nc --ofile EUR-R13B05_199920_grid_SCRIP.nc
```

For [TSMP2](https://github.com/HPSCTerrSys/TSMP2), on a 0.11 degree (~12 km) resolution, you probably want to use the EUR-R13B05 grid including boundary relaxation zone, `EUR-R13B05_199920_grid_inclbrz_v2.nc`, as the input file.
If you want a high-resolution icosahedral grid, use `EUR-R13B07_2473796_grid_inclbrz_v1.nc`.

Further information about the DETECT grid specification can be found [here](https://gitlab.jsc.fz-juelich.de/detect/detect_z03_z04/detect_grid_specification).


<details>
<summary><strong>Create SCRIP grid file (old) - Click to expand</strong></summary>

The first step in creating your input data is to define your model domain and the grid resolution you want to model in. There are several options to create the SCRIP grid file that holds this information:
1. Using the `mkscripgrid.py` script to create a regular latitude longitude grid.
2. Using the `produce_scrip_from_griddata.ncl` script to convert an existing netCDF file that holds the latidude and longitude centers of your grid in 2D (This allows you to create a curvilinear grid).
3. Similar to the first option but using the `scrip_mesh.py` script to create the SCRIP grid file.

To start the SCRIP grid file creation navigate into the `mkmapgrids` directory where you will find the above mentioned scripts.

```sh
cd mkmapgrids
```

</details>

<details>
<summary><strong>1. Create SCRIP grid file with `mkscripgrid.py` - Click to expand</strong></summary>

To use `mkscripgrid.py`, first open the script (for example using vim text editor) and adapt the variables that describe your grid. These include your grid name, the four corner points of your model domain as well as the resolution (lines 42-50 of the script). Then you can execute the script:

```sh
python mkscripgrid.py
```

```{attention}
The `mkscripgrid.py` script requires numpy and netCDF4 python libraries to be installed (use pip install to do that if not already installed).
```

The output will be a SCRIP grid netCDF file containing the grid dimension and the center and corners for each grid point. It will have the format `SCRIPgrid_"Your grid name"_nomask_c"yymmdd".nc`

</details>

<details>
<summary><strong>2. Create SCRIP grid file from griddata with `produce_scrip_from_griddata.ncl` - Click to expand</strong></summary>

Unfortunately, NCL is not maintained anymore in the new software stages. Therefore, in order to use it you first need to load an older Stage and the required software modules:

```sh
module load Stages/2020
module load Intel/2020.2.254-GCC-9.3.0
module load ParaStationMPI/5.4.7-1
module load NCL
```

Next, adapt the input in `produce_scrip_from_griddata.ncl` to your gridfile.This includes choosing a name for your output file "OutFileName", adjusting the filename of your netcdf file in line 9 and the variable names for longitude/latitude in lines 10-11. Then execute:

```sh
ncl produce_scrip_from_griddata.ncl
```

</details>

<details>
<summary><strong> 3. Create SCRIP grid file from griddata using `scrip_mesh.py` - Click to expand</strong></summary>


Alternatively to the first option, you can use the python script `scrip_mesh.py`. Like the ncl script it can create SCRIP files including the calculation of corners. It takes command line arguments like this:

```sh
python3 scrip_mesh.py --ifile NC_FILE.nc --ofile OUTPUT_SCRIP.nc --oformat SCRIP # replace NC_FILE.nc with your netcdf file and choose a name for your output SCRIP grid file for OUTPUT_SCRIP.nc
```

---

**Congratulations!** You successfully created your SCRIP grid file and can now move on to the next step.

</details>
