# Creation of mapping files #

For the creation of the mapping files of CLM inputdata to our grid use `mkmapdata/runscript_mkmapdata.sh`.
Adjust the Slurm directives to your compute time project and partition.
Below the Slurm directives, modify `GRIDNAME` and `GRIDFILE` to your grid and previously created SCRIP file.
The script can be used on JURECA and JUWELS but it is advisable to use the large memory partitions for larger domains.

The files are at JSC available below `$CSMDATA/lnd/clm2/mappingdata/grids/`.
If you don't have access to the CLM mappingdata you have to download it.

There are two possible ways to download the grids

1. Use:
```
wget --no-check-certificate -i clm_mappingfiles.txt
```

2. Run `download_grids.sh` after adapting inputs (in particular the path `myraw`).
   You need Subversion (`svn`) for this.
```
./download_grids.sh
```

When all grids are downloaded, start the creation of the weights with
```
sbatch runscript_mkmapdata.sh
```

This will create regridding and netCDF mapping files in the current
directory.

## Icosahedral grid ##

Experience has shown that conservative remapping does not always work for icosahedral grids (EUR-R13B05 and EUR-R13B07).
In that case `runscript_mkmapdata.sh` decides to create a mapping file that bilinearly interpolates fields.

# Create mapping files (old)

To start the mapping file creation navigate into the `mkmapdata` directory where you will find the script needed for this step.

```sh
cd ../mkmapdata
```

Before you run `runscript_mkmapdata.sh` you need to adapt some environment variables in lines 23-25 of the script. For this open the script (for example using vim text editor) and enter the name of your grid under `GRIDNAME` (same as what you used for the SCRIP grid file). For `CDATE`, use the date that your SCRIP grid file was created (per default the script uses the current date, if you created the SCRIPgrid file at some other point, you find the date of creation at the end of your SCRIPgrid file or in the file information). Lastly, provide the full path and name of your SCRIP grid file under `GRIDFILE`. Save and close the script.

To create your mapping files, you need a set of rawdata. If you are a JSC user you can simply refer to the common data repository by adapting the "rawpath" path in line 29 of the script.

```
rawpath="/p/scratch/cslts/shared_data/rlmod_eCLM/inputdata/surfdata/lnd/clm2/mappingdata/grids"
```

For non JSC users, download the data and adapt "rawpath" to their new location. To download the data to the directory use:

```sh
wget --no-check-certificate -i clm_mappingfiles.txt
```

Now you can execute the script:

```sh
sbatch runscript_mkmapdata.sh
```

The output will be a `map_*.nc` file for each of the rawdata files. These files are the input for the surface parameter creation weighted to your grid specifications.

To generate the domain file in the next step a mapfile is needed. This can be any of the generated `map_*.nc` files. So, set the environment variable `MAPFILE` for later use:

```sh
export MAPFILE="path to your mapfiles"/"name of one of your map files"
```

---

**Congratulations!** You successfully created your mapping files and can now move on to the next step.
