#!/usr/bin/env python3
##source and credit :https://gist.github.com/uturuncoglu/4fdf7d4253b250dcf3cad2335651f162#file-esmf_mesh-py and credit

## Reworked to a simple generation of a SCRIP file for an existing ICON-grid definition.



import os, sys, getopt
import argparse
import numpy as np
import xarray as xr
from datetime import datetime
import pandas as pd



def write_to_scrip(filename, center_lat, center_lon, corner_lat, corner_lon, mask, area=None):
    """
    Writes SCRIP grid definition to file
    xarray doesn't support order='F' for Fortran-contiguous (row-major) order
    the workaround is to arr.T.reshape.T
    """
    # create new dataset for output 
    out = xr.Dataset()

    out['grid_dims'] = xr.DataArray(np.array(center_lat.shape, dtype=np.int32), 
                                    dims=('grid_rank',)) 
    out.grid_dims.encoding = {'dtype': np.int32}

    out['grid_center_lat'] = xr.DataArray(center_lat.T.reshape((-1,)).T, 
                                          dims=('grid_size'),
                                          attrs={'units': 'radians'})

    out['grid_center_lon'] = xr.DataArray(center_lon.T.reshape((-1,)).T, 
                                          dims=('grid_size'),
                                          attrs={'units': 'radians'})

    out['grid_corner_lat'] = xr.DataArray(corner_lat.T.reshape((3, -1)).T,
                                          dims=('grid_size','grid_corners'),
                                          attrs={'units': 'radians'})

    out['grid_corner_lon'] = xr.DataArray(corner_lon.T.reshape((3, -1)).T,
                                          dims=('grid_size','grid_corners'),
                                          attrs={'units': 'radians'})
                                          
    out['grid_imask'] = xr.DataArray(mask.reshape((-1,)), 
                                     dims=('grid_size'),
                                     attrs={'units': 'unitless'})
    out.grid_imask.encoding = {'dtype': np.int32}

    # include area if it is available
    if area.any() != None:
        out['grid_area'] = xr.DataArray(area.T.reshape((-1,)).T, 
                                        dims=('grid_size'),
                                        attrs={'units': 'radians^2',
                                               'long_name': 'area weights'})



    # force no '_FillValue' if not specified
    for v in out.variables:
        if '_FillValue' not in out[v].encoding:
            out[v].encoding['_FillValue'] = None

    # add global attributes
    out.attrs = {'title': 'Triangular grid with {} dimension'.format('x'.join(list(map(str,center_lat.shape)))),
                 'created_by': os.path.basename(__file__),
                 'date_created': '{}'.format(datetime.now()),
                 'conventions': 'SCRIP',
                }

    # write output file
    if filename is not None:
        print('Writing {} ...'.format(filename))
        out.to_netcdf(filename)    



def main(argv):
    """
    Main driver to write SCRIP grid represenation
    """
    # read command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--ifile'    , help='Input grid file name', required=True)
    parser.add_argument('--ofile'    , help='Output file name', required=True)
    parser.add_argument('--overwrite', default=False, help='Overwrites output file, defaults to not', required=False, action='store_true')
    parser.add_argument('--flip'     , default=False, help='Flip mask values. SCRIP requires 0/land and 1/ocean', required=False, action='store_true')
    parser.add_argument('--latrev'   , default=False, help='Reverse latitude axis', required=False, action='store_true')
    parser.add_argument('--latvar'   , default='clat', help='Name of latitude variable, defults to ''lat''', required=False, nargs='?', const='lat')
    parser.add_argument('--lonvar'   , default='clon', help='Name of longitude variable, defaults to ''lon''', nargs='?', const='lon')
    parser.add_argument('--maskvar'  , default='mask', help='Name of mask variable, defaults to ''mask''', nargs='?', const='mask')
    parser.add_argument('--maskcal'  , default=False, help='Calculate mask using fill value from variable defined in maskvar - 0/land and 1/ocean', required=False, action='store_true')
    parser.add_argument('--double'   , default=False, help='Double precision output, defaults to float', required=False, action='store_true')
    args = parser.parse_args()

    ifile = args.ifile
    ofile = args.ofile
    overwrite = args.overwrite
    flip = args.flip
    latrev = args.latrev
    latvar = args.latvar
    lonvar = args.lonvar
    maskvar = args.maskvar
    maskcal = args.maskcal
    if not args.maskvar:
        print('maskcal argument requires maskvar to calculate mask! exiting ...')
        sys.exit()
    double = args.double

    # print out configuration
    print("Configuration:")
    print("ifile     = {}".format(ifile))
    print("ofile     = {}".format(ofile))
    print("overwrite = {}".format(overwrite))
    print("flip      = {}".format(flip))
    print("latrev    = {}".format(latrev))
    print("latvar    = {}".format(latvar))
    print("lonvar    = {}".format(lonvar))
    print("maskvar   = {}".format(maskvar))
    print("maskcal   = {} ({})".format(maskcal, maskvar))
    print("double    = {}".format(double))

    # open file, transpose() fixes dimension ordering and mimic Fortran
    if os.path.isfile(ifile):
        ds = xr.open_dataset(ifile, mask_and_scale=False, decode_times=False).transpose()
    else:
        print('Input file could not find!') 
        sys.exit(2)       

    # check output file
    if overwrite:
        if os.path.isfile(ofile):
            print('Removing existing output file {}.'.format(ofile))
            os.remove(ofile)
    else:
        if os.path.isfile(ofile):
            print('Output file exists. Please provide --overwrite flag.') 
            sys.exit(2)

    # check coordinate variables
    if latvar not in ds.coords and latvar not in ds.data_vars:
        print('Input file does not have variable named {}.'.format(latvar))
        print('File has following {}'.format(ds.coords))
        print('File has following {}'.format(ds.data_vars))
        sys.exit(2)

    if lonvar not in ds.coords and lonvar not in ds.data_vars:
        print('Input file does not have variable named {}.'.format(latvar))
        print('File has following {}'.format(ds.coords))
        print('File has following {}'.format(ds.data_vars))
        sys.exit(2)

    # remove time dimension from coordinate variables
    hasTime = 'time' in ds[latvar].dims
    if hasTime:
        lat = ds[latvar][:,:,0]
    else:
        lat = ds[latvar]

    hasTime = 'time' in ds[lonvar].dims
    if hasTime:
        lon = ds[lonvar][:,:,0]
    else:
        lon = ds[lonvar]

    # reverse latitude dimension
    if latrev:
        lat_name = [x for x in lat.coords.dims if 'lat' in x]
        if lat_name:
            lat = lat.reindex({lat_name[0]: list(reversed(lat[lat_name[0]]))})

    # remove time dimension from mask variable and optionally flip mask values
    # this will also create artifical mask variable with all ones, if it is required
    if maskvar in ds.data_vars:
        print('Using mask values from the file.')

        # check mask has time dimension or not
        hasTime = 'time' in ds[maskvar].dims
        if hasTime:
            mask = ds[maskvar][:,:,0]
        else:
            mask = ds[maskvar][:]
 


    # flip mask values
    if flip:
        print('Flipping mask values to 0 for land and 1 for ocean')
        mask = xr.where(mask > 0, 0, 1)


    corner_lat = ds["clat_vertices"]
    corner_lon = ds["clon_vertices"]
    center_lon = ds[lonvar]
    center_lat = ds[latvar]
    area = ds["cell_area"]
    mask = xr.ones_like(center_lon)
    corner_lat=corner_lat.to_numpy()
    corner_lon=corner_lon.to_numpy()
    center_lon=center_lon.to_numpy()
    center_lat=center_lat.to_numpy()
    area=area.to_numpy()
    mask=mask.to_numpy()


    # create output file

    write_to_scrip(ofile, center_lat, center_lon, corner_lat, corner_lon, mask, area)  


if __name__== "__main__":
	main(sys.argv[1:])
