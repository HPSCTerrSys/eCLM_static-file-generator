# -*- coding: utf-8 -*-
"""
Created on Fri May 31 11:44:57 2024

@author: olgad
"""

# This script creates a SCRIP grid file for a land-only point or regional case.
# It is a python version of mkscripgrid.ncl originally written by Erik Kluzek Dec/07/2011

import os
import numpy as np
from datetime import datetime
from netCDF4 import Dataset

def getenv_double(var_name, default):
    value = os.getenv(var_name)
    return float(value) if value else default

def getenv_int(var_name, default):
    value = os.getenv(var_name)
    return int(value) if value else default

def getenv_str(var_name, default):
    value = os.getenv(var_name)
    return value if value else default

def fspan1up(fbegin, fend, number):
    # Account for meridian crossing
    if fend < fbegin:
        fend +=360

    if number == 1:
        return np.array([(fbegin + fend) / 2.0])
    else:
        return np.linspace(fbegin, fend, number)

def check_latitude(lat, var_name):
    # Check if the latitude is within the valid range [-90, 90].
    if lat < -90 or lat > 90:
        raise ValueError(f"{var_name} must be in the range [-90, 90]. Got {lat}")

def check_longitude(lon, var_name):
    # Check if the longitude is within the valid range [0, 360].
    if lon < 0 or lon >= 360:
        raise ValueError(f"{var_name} must be in the range [0, 360). Got {lon}")

# ===========================================================================================================
# Set a few constants needed later
cdate = datetime.now().strftime("%y%m%d")
ldate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# IMPORTANT NOTE: EDIT THE FOLLOWING TO CUSTOMIZE OR PASS AS ENV VARIABLES.

# Input resolution and position
name = getenv_str("PTNAME", None) # Set your grid name here

latS = getenv_double("S_LAT", 45.5098) # Set the south latitude here, valid values: [-90,90]
latN = getenv_double("N_LAT", 45.6098) # Set the north latitude here, valid values: [-90,90]
lonE = getenv_double("E_LON", 275.3362) # Set the east longitude here, valid values: [0,360]
lonW = getenv_double("W_LON", 275.2362) # Set the west longitude here, valid values: [0,360]

nx = getenv_int("NX", 1) # Set the number of grids along longitude lines here
ny = getenv_int("NY", 1) # Set the number of grids along latitude lines here

# Check for correct ranges
check_latitude(latS, "S_LAT")
check_latitude(latN, "N_LAT")
check_longitude(lonE, "E_LON")
check_longitude(lonW, "W_LON")

imask = getenv_int("IMASK", 1)

print_str = getenv_str("PRINT", "TRUE")
printn = True if print_str == "TRUE" else False

outfilename = getenv_str("GRIDFILE", None)

if name is None:
    name = f"{nx}x{ny}pt_US-UMB"

if outfilename is None:
    if imask == 1:
        outfilename = f"SCRIPgrid_{name}_nomask_c{cdate}.nc"
    elif imask == 0:
        outfilename = f"SCRIPgrid_{name}_noocean_c{cdate}.nc"
    else:
        outfilename = f"SCRIPgrid_{name}_mask_c{cdate}.nc"

os.system(f"/bin/rm -f {outfilename}")
if printn:
    print(f"output file: {outfilename}")

# Calculate raw difference for longitudes
diffX = lonE - lonW

# Adjust for wrap-around if lonE is less than lonW
if lonE < lonW:
    diffX += 360

# Compute derived quantitites
delX = diffX / nx
delY = (latN - latS) / ny

lonCenters = fspan1up((lonW + delX/2.0), (lonE - delX/2.0), nx)
# Make sure longitudes are within [0,360] range
lonCenters = np.where(lonCenters>360,lonCenters-360,lonCenters) 

latCenters = fspan1up((latS + delY/2.0), (latN - delY/2.0), ny)

lon = np.zeros((ny, nx))
lat = np.zeros((ny, nx))
lonCorners = np.zeros((ny, nx, 4))
latCorners = np.zeros((ny, nx, 4))

for i in range(nx):
    lat[:, i] = latCenters
    latCorners[:, i, 0] = latCenters - delY/2.0
    latCorners[:, i, 1] = latCenters + delY/2.0
    latCorners[:, i, 2] = latCenters + delY/2.0
    latCorners[:, i, 3] = latCenters - delY/2.0

for j in range(ny):
    lon[j, :] = lonCenters
    lonCorners[j, :, 0] = lonCenters - delX/2.0
    lonCorners[j, :, 1] = lonCenters - delX/2.0
    lonCorners[j, :, 2] = lonCenters + delX/2.0
    lonCorners[j, :, 3] = lonCenters + delX/2.0

Mask2D = np.full((ny, nx), imask, dtype=int)
gridSize = f"{delX}x{delY}"

# Create SCRIP grid file
with Dataset(outfilename, "w", format="NETCDF4") as nc:
    nc.createDimension('grid_size', size=nx*ny)
    nc.createDimension('grid_corners', size=4)
    nc.createDimension('grid_rank', size=2)

    grid_dims = nc.createVariable('grid_dims','i4',('grid_rank',), fill_value=-2147483647)
    grid_dims[:] = [nx, ny]

    grid_center_lat = nc.createVariable('grid_center_lat', 'f8', ('grid_size',))
    grid_center_lon = nc.createVariable('grid_center_lon', 'f8', ('grid_size',))
    grid_corner_lat = nc.createVariable('grid_corner_lat', 'f8', ('grid_size', 'grid_corners'))
    grid_corner_lon = nc.createVariable('grid_corner_lon', 'f8', ('grid_size', 'grid_corners'))
    grid_imask = nc.createVariable('grid_imask', 'i4', ('grid_size',))
    
    #Adding units attribute
    grid_center_lat.units = 'degrees'
    grid_center_lon.units = 'degrees'
    grid_corner_lat.units = 'degrees'
    grid_corner_lon.units = 'degrees' 
    grid_imask.units = 'unitless'

    grid_center_lat[:] = lat.flatten()
    grid_center_lon[:] = lon.flatten()
    grid_corner_lat[:] = latCorners.reshape(nx*ny, 4)
    grid_corner_lon[:] = lonCorners.reshape(nx*ny, 4)
    grid_imask[:] = Mask2D.flatten()
    
    nc.title = f"SCRIP grid file for {name}"
    nc.history = f"{ldate}: create using mkscripgrid.py"
    nc.comment = "Ocean is assumed to non-existant at this point"

if printn:
    print("================================================================================================")
    print(f"Successfully created SCRIP grid file: {outfilename}")
