# eCLM static file generator

This repository shows how to generate curvilinear surface and domain fields for eCLM simulations.
The generator follows the official CLM-workflow but makes a few adaptions.

It is not necessary to clone CTSM and cime, as this generator is independent.
However, the basis is the CLM5.0 release and there might be newer developments in the official repositories below

```
https://github.com/ESCOMP/CTSM.git
https://github.com/ESMCI/cime.git
```

By sourcing the provided enviroment file

```
source jsc.2024_Intel.sh
```

the necessary compilations in this repository can be performed consistently. It also contains the export of necessary paths for netCDF.

## Creation of gridfile

First, we need to create a gridfile that describes our simulation domain.
In TSMP2 for eCLM and ICON the **icosahedral (EUR-R13B05; and EUR-R13B07 (WIP)) grid** is used.
Follow that in this guide if you want to use this with TSMP2; for other purposes guidelines for the **curvilinear** and **rectilinear** are here as well.
The relevant scripts are in `./mkmapgrids/`.
The gridfile will contain arrays of longitudes and latitudes of the gridboxes' centres and corners.
The simulation domain is the EURO-CORDEX pan-European domain, which at high latitudes, for the Earth's canonical curvilinear grid, has significant convergence of the zonal dimension with increasing latitude.
Therefore we *rotate* the grid (of a same size) centred at the equator to the pan-European domain.

At the moment SCRIP generation from **curvilinear grids** can be done and is tested to work with the NCAR Command Language (NCL), even though it is [deprecated](https://www.ncl.ucar.edu/open_letter_to_ncl_users.shtml).
NCL can be installed through Conda.
If you have no Conda yet on your system, you can install it, including the conda-forge channel, following [this guide](https://github.com/conda-forge/miniforge?tab=readme-ov-file#unix-like-platforms-macos--linux).
Then follow [this guide](https://yonsci.github.io/yon_academic/portfolio/portfolio-9/#installing-ncl) to install NCL.
The repository contains the NCL-script [`produce_scrip_from_griddata.ncl`](mkmapgrids/produce_scrip_from_griddata.ncl) that can create a SCRIP file from a netCDF that contains the lat- and lon-center coordinates.
It is not necessary to provide the corners because the internal routine of NCL seems to calculate them correctly for the later steps.
Adapt the input in `produce_scrip_from_griddata.ncl` to your gridfile and execute:

```
ncl produce_scrip_from_griddata.ncl
```

Grid files are available on the JSC machines in the DETECT CentralDB below `/p/largedata2/detectdata/CentralDB/projects/z04/detect_grid_specs/grids/`.
You can, e.g., use [the 450x438 gridfile including boundary relaxation zone](https://gitlab.jsc.fz-juelich.de/detect/detect_z03_z04/detect_grid_specification/-/blob/main/grids/EUR-11_450x438_grid_inclbrz13gp_v2.nc) as the input file (`f` in the script).

To use `mksurfdata.pl`, regridding weights have to be created. For this the grid has to be properly defined in one of the following formats:

- SCRIP
- ESMF-Mesh
- CF-convention-file

SCRIP is a very old format not maintained anymore but is still the most effective solution.
ESMF is able to basically handle any netCDF file that follows the CF-conventions version 1.6 and includes lat/lon values and corners.
This means that ESMF mesh files are also able to describe unstructured grids.

You can create a SCRIP file from a **rectilinear grid** with [`scrip_mesh.py`](mkmapgrids/scrip_mesh.py).
The Python packages numpy, xarray and dask-expr need to be available.
They are loaded by the [environment file](jsc.2024_Intel.sh) (sourced above).
The script was modified from `mesh_maker.py` from the CTSM repository to accept 2D lon / lat.
The main caveat is that the resulting surface files are in 1D which makes them harder to handle.
The python script `scrip_mesh.py` can create SCRIP files including the calculation of corners.
It takes command line arguments like this:

```
./scrip_mesh.py --ifile EURregLonLat01deg_1204x548_grid_inclbrz_v2.nc --ofile cordex_SCRIP.nc --oformat SCRIP
```

`--help` provides additional information.

SCRIP files for **icosahedral grids**, like the ICON grid, are a special case because the usual calculation of corners is not usable.
The best practice is to transform already existing ICON gridfiles to the SCRIP format.
This can be done with the python script [`ICON_SCRIP.py`](mkmapgrids/ICON_SCRIP.py):

```
./ICON_SCRIP.py --ifile EUR-R13B05_199920_grid_inclbrz_v2.nc --ofile EUR-R13B05_199920_grid_SCRIP.nc
```

For [TSMP2](https://github.com/HPSCTerrSys/TSMP2), on a 0.11 degree (12 km) resolution, you probably want to use [the EUR-R13B05 grid including boundary relaxation zone](https://gitlab.jsc.fz-juelich.de/detect/detect_z03_z04/detect_grid_specification/-/blob/main/grids/EUR-R13B05_199920_grid_inclbrz_v2.nc) as the input file (`f` in the script).
This file is also on the JSC machines as `/p/largedata2/detectdata/CentralDB/projects/z04/detect_grid_specs/grids/EUR-R13B05_199920_grid_inclbrz_v2.nc`.

Further information about the DETECT grid specification can be found [here](https://gitlab.jsc.fz-juelich.de/detect/detect_z03_z04/detect_grid_specification).

## Creation of mapping files

For the creation of the mapping files of CLM inputdata to our grid use `mkmapdata/runscript_mkmapdata.sh`.
Adjust the Slurm directives to your compute time project and modify `DATAFILE` to your previously created SCRIP file.
The script can be used on JURECA and JUWELS but it is advisable to use the large memory partitions for larger domains.
If you don't have access to the CLM mappingdata you have to download it.
Use:

```
wget --no-check-certificate -i clm_mappingfiles.txt
```
Then start the creation of the weights with
```
sbatch runscript_mkmapdata.sh
```

This will create regridding and netCDF mapping files in the current directory.

### ICON grid

Experience has shown that conservative remapping does not always work for ICON grids.
As an alternative you can adapt `runscript_mkmapdata.sh`.
Change `-m conserve` to `-m bilinear` and add the options `--src_loc center` `--dst_loc center` inside the script.

## Creation of domain files

The CIME submodule under `./gen_domain_files/` generates the domain files for CLM.
This repository contains a simplified version of `gen_domain` which is easier to compile on [JSC](https://www.fz-juelich.de/en/ias/jsc) machines and you do not need the CIME repository.
Required modules are imkl, netCDF and netCDF-Fortran (all provided by `jsc.2024_Intel.sh`).
Then compile `src/gen_domain.F90` with

```
gfortran -o gen_domain src/gen_domain.F90 -mkl -I${INC_NETCDF} -lnetcdff -lnetcdf
```

After the compilation you can execute `gen_domain` with $MAPFILE being one of the mapping files created in the step before (in `mkmapdata/`) and $GRIDNAME being a string with the name of your grid, e.g. `EUR-11`.
The choice of $MAPFILE does not influence the lat- and longitude values in the domain file but can influence the land/sea mask.

```
./gen_domain -m $MAPFILE -o $GRIDNAME -l $GRIDNAME
```

The created domain file will later be modified.

## Creation of surface file

The surface creation tool is found under `./mksurfdata/`.
You have to compile it with gmake in src-directory.
The required modules Intel and netCDF-Fortran are loaded by `jsc.2024_Intel.sh`.

After compilation, modify corresponding paths and execute

```
export GRIDNAME="EUR-11"
export CDATE="`date +%y%m%d`"   # should match mapping files creation date
export CSMDATA="/p/largedata2/detectdata/CentralDB/projects/z04"

# generate surfdata
./mksurfdata.pl -r usrspec -usr_gname $GRIDNAME -usr_gdate $CDATE -l $CSMDATA -allownofile -y 2005 -hirespft
```

to create a real domain with hires pft.
Again, you need to have set $GRIDNAME, the date $CDATE in yymmdd format (matching the mapping files) and the path $CSMDATA where the raw data of CLM is stored.
You have to download the data from https://svn-ccsm-inputdata.cgd.ucar.edu/trunk/inputdata/lnd/clm2/rawdata/ if you have no access to JSC machines.
Also make sure that mksurfdata and mkmapdata have the same parent directory.

At least in the original UCAR rawdata input files, not all variables are available (as the correct name).
Instead you can create the surface file with *mostly* constant values (apparently `SOIL_COLOR` is not homogeneous) with the following command.
In a later step we are anyway going to replace variables in this file that are specific for eCLM (TSMP2).

```
./mksurfdata.pl -r usrspec -usr_gname $GRIDNAME -usr_gdate $CDATE -l $CSMDATA -allownofile -y 2005 -hirespft -usr_mapdir="../mkmapdata/" -no-crop -pft_idx 13 -pft_frc 100 -soil_cly 60 -soil_col 10 -soil_fmx 0.5 -soil_snd 40
```

PS: There are many versions mksurfdata.pl in the CTSM github. Stick to the CLM5-release version!
Other versions use other mapping files and are not compatible with negative longitudes.

## Modification of the surface and domain file

The created surface and domain file have negative longitudes that CLM5 does not accept and inherently has no landmask. To modify the longitudes and to add a landmask use `mod_domain.sh` after inserting the paths to your files.

## Creation of forcing data from ERA5

A possible source of atmospheric forcing for CLM5 is ERA5.
The folder `mkforcing/` contains two scripts that assist the ERA5 retrieval.
- `download_ERA5.py` contains a prepared retrieval for the cdsapi python module.
By modifying the two loops inside the script it is possible to download ERA5 for any timerange.
However, the script requires that cdsapi is installed with an user specific key.
More information about the installation can be found [here](https://cds.climate.copernicus.eu/api-how-to).
- `prepare_ERA5.sh` prepares ERA5 as an input by changing names and modifying units.
ERA5 has to be regridded to your resolution before the script can be used.

`download_ERA5_v2.py`, `prepare_ERA5_v2.sh` and `extract_ERA5_meteocloud.sh` provide an alternative pathway. [This issue](https://gitlab.jsc.fz-juelich.de/HPSCTerrSys/tsmp-internal-development-tracking/-/issues/36) provides some details. Basically it is safer to extract the lowermost level of temperature, humidity and wind of ERA5 instead of taking 2m-values. The workflow goes like this:

```
bash extract_ERA5_meteocloud.sh
python download_ERA5_v2.py
regridding
bash prepare_ERA5_v2.sh
```

Note: This worfklow is not fully tested.

