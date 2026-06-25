# Creation of domain files #

The CIME submodule under `./gen_domain_files/` generates the domain files for CLM.
This repository contains a simplified version of `gen_domain` which is easier to compile on JSC machines and you do not need the CIME repository.
Required modules are imkl, netCDF and netCDF-Fortran (all provided by `jsc.2024_Intel.sh`).
Then compile `src/gen_domain.F90` with

```
gfortran -o gen_domain src/gen_domain.F90 -mkl -I${INC_NETCDF} -lnetcdff -lnetcdf
```

If the Intel Math Kernel Library (MKL) is not available on your system, you can remove the `-mkl` flag without consequences for the output.
After the compilation you can execute `gen_domain` with $MAPFILE being one of the mapping files created in the step before (in `mkmapdata/`) and $GRIDNAME being a string with the name of your grid, e.g. `EUR-R13B05` for the ~12-km icosahedral grid.
The choice of $MAPFILE does not influence the lat- and longitude values in the domain file but can influence the land/sea mask.
If you use the `EUR-R13B05` grid, you could set `MAPFILE="../mkmapdata/map_0.5x0.5_AVHRR_to_${GRIDNAME}_*_c${CDATE}.nc"`.

**Hint:** For better reproducibility, specify the absolute path of
`$MAPFILE`. The absolute path to the file can be printed using
`realpath $MAPFILE`.

```
./gen_domain -m $MAPFILE -o $GRIDNAME -l $GRIDNAME -u $USER
```

The created domain file will later be modified.

<details>
<summary><strong>Create domain file (old) - Click to expand</strong></summary>

In this step you will create the domain file for your case using `gen_domain`. First, you need to navigate into the `gen_domain_files/src/` directory and compile it with the loaded modules ifort, imkl, netCDF and netCDF-Fortran.

```sh
cd ../gen_domain_files/src/

# Compile the script
ifort -o ../gen_domain gen_domain.F90 -mkl -lnetcdff -lnetcdf
```
```{attention}
If you get a message saying "ifort: command line remark #10412: option '-mkl' is deprecated and will be removed in a future release. Please use the replacement option '-qmkl'" or the compiling fails, replace `-mkl` with `-qmkl`.
```

Before running the script you need to export the environment variable `GRIDNAME` (same as what you used for the SCRIP grid file and in the `runscript_mkmapdata.sh` script).

```sh
export GRIDNAME="your gridname"
```
Then you can run the script:
```sh
cd ../
./gen_domain -m $MAPFILE -o $GRIDNAME -l $GRIDNAME
```

The output of this will be two netCDF files `domain.lnd.*.nc` and `domain.ocn.*.nc` that define the land and ocean mask respectively. The land mask will inform the atmosphere and land inputs of eCLM when running a case.

However, `gen_domain` defaults the use of the variables `mask` and `frac` on these files to be for ocean models, i.e. 0 for land and 1 for ocean. So to use them you have to either manipulate the `domain.lnd.*.nc` file to have mask and frac set to 1 instead of 0 (WARNING: some netCDF script languages have `mask` as a reserved keyword e.g. NCO, use single quotation marks as workaround).
Or simply swap/rename the `domain.lnd.*.nc` and `domain.ocn.*.nc` file:

```sh
mv domain.lnd."your gridname"_"your gridname"."yymmdd".nc temp.nc
mv domain.ocn."your gridname"_"your gridname"."yymmdd".nc domain.lnd."your gridname"_"your gridname"."yymmdd".nc
mv temp.nc domain.ocn."your gridname"_"your gridname"."yymmdd".nc
```

**Congratulations!** You successfully created your domain files and can now move on to the final next step to create your surface data.

</details>
