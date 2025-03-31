#!/usr/bin/env python
import calendar
import cdsapi
import sys
import os

def generate_days(year, month):
    # Get the number of days in the given month
    num_days = calendar.monthrange(year, month)[1]

    # Generate the list of days as integers
    days = [day for day in range(1, num_days + 1)]
    
    return days

def generate_datarequest(year, monthstr, days):
    
    # active download client for climate data service (cds)
    client = cdsapi.Client()
    
    # dataset to download rom cds
    dataset = "reanalysis-era5-single-levels"
    # request for cds
    request = {
        "product_type": ["reanalysis"],
        "variable": [
            "surface_pressure",
            "mean_surface_downward_long_wave_radiation_flux",
            "mean_surface_downward_short_wave_radiation_flux",
            "mean_total_precipitation_rate"
        ],
        "year": [str(year)],
        "month": [monthstr],
        "day": days,
        "time": [
            "00:00", "01:00", "02:00",
            "03:00", "04:00", "05:00",
            "06:00", "07:00", "08:00",
            "09:00", "10:00", "11:00",
            "12:00", "13:00", "14:00",
            "15:00", "16:00", "17:00",
            "18:00", "19:00", "20:00",
            "21:00", "22:00", "23:00"
        ],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": [74, -42, 20, 69]
    }
    # filename of downloaded file
    target = 'download_era5_'+str(year)+'_'+monthstr+'.zip'
    
    # Get the data from cds
    client.retrieve(dataset, request, target)

if __name__ == "__main__":
    # Check if the correct number of arguments are provided
    if len(sys.argv) != 4:
        print("Usage: python download_ERA5_input.py <year> <month> <output_directory>")
        sys.exit(1)

    # Get the year and month from command-line arguments
    year = int(sys.argv[1])
    month = int(sys.argv[2])
    dirout = sys.argv[3]

    # Ensure the output directory exists, if not, create it
    if not os.path.exists(dirout):
        os.makedirs(dirout)

    # change to output directory
    os.chdir(dirout)

    # Format the month with a leading zero if needed
    monthstr = f"{month:02d}"

    # Get the list of days for the request
    days = generate_days(year, month)

    # do download request
    generate_datarequest(year, monthstr, days)
