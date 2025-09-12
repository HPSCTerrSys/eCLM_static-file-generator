#!/usr/bin/env bash

# Load modules
module --force purge
module use $OTHERSTAGES
module load Stages/2024
module load Intel/2023.2.1
module load ParaStationMPI/5.9.2-1
module load ESMF/8.5.0
#
module load Hypre/2.29.0
module load Silo/4.11
module load Tcl/8.6.13
#
module load ecCodes/2.31.0
module load netCDF/4.9.2
module load netCDF-Fortran/4.6.1
module load PnetCDF/1.12.3
module load cURL/8.0.1
module load Perl/5.36.1
module load Python/3.11.3
module load NCO/5.1.8
module load CDO/2.3.0
module load CMake/3.26.3
#
module load xarray/2023.8.0
module load dask/2023.9.2
module li

# Export LIB- and INC-NETCDF
export LIB_NETCDF=${EBROOTNETCDFMINFORTRAN}/lib
export INC_NETCDF=${EBROOTNETCDFMINFORTRAN}/include

