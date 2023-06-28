import xarray as xr
import numpy as np
import sys

path_clm_3_5 = sys.argv[1]
path_clm_5 = sys.argv[2]


clm_3_5_source = xr.open_dataset(path_clm_3_5)

pft_3_5 = clm_3_5_source['PCT_PFT']
pft_3_5 = pft_3_5.to_numpy()


pft_natural = pft_3_5[0:15,:,:]
cft = pft_3_5[15:,:,:]


clm5_dest = xr.open_dataset(path_clm_5, mode='a')
#clm5_dest = clm5_dest.isel(cft=slice(0, 2))
#clm5_dest = clm5_dest.isel(lsmpft=slice(0, 17))

clm5_dest.attrs['Urban_raw_data_file_name'] = 'None'
clm5_dest.attrs['Vegetation_type_raw_data_filename'] = 'GLC2000'

clm5_dest['PCT_URBAN'][:] = 0 



clm5_dest["PCT_NAT_PFT"]=(['natpft', 'lsmlat', 'lsmlon'],  pft_natural)
clm5_dest["PCT_CFT"]=(['cft', 'lsmlat', 'lsmlon'],  cft)

clm5_dest.to_netcdf(path_clm_5)


clm_3_5_source.close()
clm5_dest.close()
