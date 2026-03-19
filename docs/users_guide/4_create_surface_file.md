# Creation of surface file #

The surface creation tool is found under `./mksurfdata/`.
The required modules Intel and netCDF-Fortran are loaded by `jsc.2024_Intel.sh`.

First, compile `mksurfdata_map`:

```
cd mksurfdata/src
gmake
```

Then check that `mksurfdata_map` is available inside `./mksurfdata/`.

After compilation execute

```
export GRIDNAME="EUR-R13B05"    # in case of the low-resolution icosahedral grid
export CDATE="`date +%y%m%d`"   # should match mapping files creation date

# generate surfdata
./mksurfdata.pl -r usrspec -usr_gname $GRIDNAME -usr_gdate $CDATE -l $CSMDATA -allownofile -y 2005 -hirespft
```

to create a real domain with hires pft.
Again, you need to have set $GRIDNAME, the date $CDATE in yymmdd format (matching the mapping files) and the path $CSMDATA where the raw data of CLM is stored.
You have to download the data from https://svn-ccsm-inputdata.cgd.ucar.edu/trunk/inputdata/lnd/clm2/rawdata/ if you have no access to JSC machines.
Also make sure that mksurfdata and mkmapdata have the same parent directory.

At least in the original UCAR rawdata input files, not all variables are available (under the correct name).
Instead you can create the surface file with *mostly* constant values (apparently `SOIL_COLOR` is not homogeneous) with the following command.
In a later step we are anyway going to replace variables in this file that are specific for eCLM (TSMP2).

```
./mksurfdata.pl -r usrspec -usr_gname $GRIDNAME -usr_gdate $CDATE -l $CSMDATA -allownofile -y 2005 -hirespft -usr_mapdir="../mkmapdata/" -no-crop -pft_idx 13 -pft_frc 100 -soil_cly 60 -soil_col 10 -soil_fmx 0.5 -soil_snd 40
```


## `mksurfdata.pl` Help Message

For the convenience of the user, below is the help message for
`mksurfdata.pl`.

```
SYNOPSIS

	 For supported resolutions:
	 mksurfdata.pl -res <res>  [OPTIONS]
		-res [or -r] "resolution" is the supported resolution(s) to use for files (by default all ).

	 For unsupported, user-specified resolutions:
	 mksurfdata.pl -res usrspec -usr_gname <user_gname> -usr_gdate <user_gdate>  [OPTIONS]
		-usr_gname "user_gname"    User resolution name to find grid file with
								   (only used if -res is set to 'usrspec')
		-usr_gdate "user_gdate"    User map date to find mapping files with
								   (only used if -res is set to 'usrspec')
								   NOTE: all mapping files are assumed to be in mkmapdata
									- and the user needs to have invoked mkmapdata in
									  that directory first
		-usr_mapdir "mapdirectory" Directory where the user-supplied mapping files are
								   Default: ../mkmapdata

OPTIONS
	 NOTE: The three critical options are (-years, -glc_nec, and -ssp_rcp) they are marked as such.

	 -allownofile                  Allow the script to run even if one of the input files
								   does NOT exist.
	 -dinlc [or -l]                Enter the directory location for inputdata
								   (default /glade/p/cesm/cseg/inputdata)
	 -debug [or -d]                Do not actually run -- just print out what
								   would happen if ran.
	 -dynpft "filename"            Dynamic PFT/harvesting file to use if you have a manual list you want to use
								   (rather than create it on the fly, must be consistent with first year)
								   (Normally NOT used)
	 -fast_maps                    Toggle fast mode which doesn't use the large mapping files
	 -glc_nec "number"             Number of glacier elevation classes to use (by default 10)
								   (CRITICAL OPTION)
	 -merge_gis                    If you want to use the glacier dataset that merges in
								   the Greenland Ice Sheet data that CISM uses (typically
								   used only if consistency with CISM is important)
	 -hirespft                     If you want to use the high-resolution pft dataset rather
								   than the default lower resolution dataset
								   (low resolution is at half-degree, high resolution at 3minute)
								   (hires only available for present-day [2000])
	 -exedir "directory"           Directory where mksurfdata_map program is
								   (by default assume it is in the current directory)
	 -inlandwet                    If you want to allow inland wetlands
	 -no-crop                      Create datasets without the extensive list of prognostic crop types
	 -no_surfdata                  Do not output a surface dataset
								   This is useful if you only want a landuse_timeseries file
	 -years [or -y] "years"        Simulation year(s) to run over (by default 1850,2000)
								   (can also be a simulation year range: i.e. 1850-2000 or 1850-2100 for ssp_rcp future scenarios)
								   (CRITICAL OPTION)
	 -help  [or -h]                Display this help.

	 -rundir "directory"           Directory to run in
								   (by default current directory $cwd)

	 -ssp_rcp "scenario-name"      Shared Socioeconomic Pathway and Representative Concentration Pathway Scenario name(s).
								   "hist" for historical, otherwise in form of SSPn-m.m where n is the SSP number
								   and m.m is the radiative forcing in W/m^2 at the peak or 2100.
								   (normally use thiw with -years 1850-2100)
								   (CRITICAL OPTION)

	 -usrname "clm_usrdat_name"    CLM user data name to find grid file with.

	 -vic                          Add the fields required for the VIC model
	 -glc                          Add the optional 3D glacier fields for verification of the glacier model

	  NOTE: years, res, and ssp_rcp can be comma delimited lists.


OPTIONS to override the mapping of the input gridded data with hardcoded input

	 -pft_frc "list of fractions"  Comma delimited list of percentages for veg types
	 -pft_idx "list of veg index"  Comma delimited veg index for each fraction
	 -soil_cly "% of clay"         % of soil that is clay
	 -soil_col "soil color"        Soil color (1 [light] to 20 [dark])
	 -soil_fmx "soil fmax"         Soil maximum saturated fraction (0-1)
	 -soil_snd "% of sand"         % of soil that is sand

OPTIONS to work around bugs?
	 -urban_skip_abort_on_invalid_data_check
								   do not abort on an invalid data check in urban.
								   Added 2015-01 to avoid recompiling as noted in
								   /glade/p/cesm/cseg/inputdata/lnd/clm2/surfdata_map/README_c141219

EOF
```


<details>
<summary><strong>Create surface file (old) - Click to expand</strong></summary>

In this step you will create the surface data file using the `mksurfdata.pl` script.
First, we will compile the script with `make` in the `mksurfdata/src` directory.


```sh
cd ../mksurfdata/src

# Compile the script
make
```

The script needs a few environment variables such as `GRIDNAME` (exported in the previous step), `CDATE` (date of creation of the mapping files which can be found at the end of each `map_*` file before the file extension) and `CSMDATA` (the path where the raw data for the surface file creation is stored) before executing the script.

```sh
export CDATE=`date +%y%m%d`
export CSMDATA="/p/scratch/cslts/shared_data/rlmod_eCLM/inputdata/" # this works for JSC users only, for non JSC users see below

# generate surfdata
./mksurfdata.pl -r usrspec -usr_gname $GRIDNAME -usr_gdate $CDATE -l $CSMDATA -allownofile -y 2000 -crop
```

```{tip}
The `-crop` option used in `./mksurfdata.pl` will create a surface file for BGC mode with all crops active. If you want to use SP mode, you should run without this option.

Use `./mksurfdata.pl -help` to display all options possible for this script.
For example:
- `hirespft` - If you want to use the high-resolution pft dataset rather than the default lower resolution dataset (low resolution is at half-degree, high resolution at 3minute), hires is only available for present-day (2000)
```

**For non JSC users**:
Non JSC users can download the raw data from HSC datapub using this <a href="https://datapub.fz-juelich.de/slts/eclm/surfdata/rawdata/" target="_blank">link</a> or from the official <a href="https://svn-ccsm-inputdata.cgd.ucar.edu/trunk/inputdata/lnd/clm2/rawdata/" target="_blank">rawdata repository</a> using `wget` before submitting the script.

```sh
wget "RAWDATA_LINK"/"NAME_OF_RAWDATA_FILE" --no-check-certificate # repeat this for every rawdata file
```

You will see a "Successfully created fsurdat files" message displayed at the end of the script if it ran through.

The output will be a netCDF file similar to `surfdata_"your grid name"_hist_78pfts_CMIP6_simyr2000_c"yymmdd".nc`.

**Congratulations!** You successfully created your surface data file! In the next step you will learn how to create your own atmospheric forcings.

</details>
