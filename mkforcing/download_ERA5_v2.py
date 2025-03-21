#!/usr/bin/env python3
import cdsapi

c = cdsapi.Client()

for year in [2017]:
        for month in range(1,13,1):
                if month<10:
                        month="0"+str(month)
                file="era5_"+str(year)+"_"+str(month)+".nc"
                c.retrieve(
    'reanalysis-era5-single-levels',
    {
        'product_type': 'reanalysis',
        'variable': [
            'surface_pressure', 'mean_surface_downward_long_wave_radiation_flux', 'mean_surface_downward_short_wave_radiation_flux', 'mean_total_precipitation_rate', 'boundary_layer_height'
        ],
        'year': year,
            'month': month,
        'day': [
            '01', '02', '03',
            '04', '05', '06',
            '07', '08', '09',
            '10', '11', '12',
            '13', '14', '15',
            '16', '17', '18',
            '19', '20', '21',
            '22', '23', '24',
            '25', '26', '27',
            '28', '29', '30',
            '31',
        ],
        'time': [
            '00:00', '01:00', '02:00',
            '03:00', '04:00', '05:00',
            '06:00', '07:00', '08:00',
            '09:00', '10:00', '11:00',
            '12:00', '13:00', '14:00',
            '15:00', '16:00', '17:00',
            '18:00', '19:00', '20:00',
            '21:00', '22:00', '23:00',
        ],
        'area': [
            74, -48, 20,
            69,
        ],
        'format': 'netcdf',
    },
                        file)

