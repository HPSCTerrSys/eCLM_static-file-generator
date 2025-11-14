import xarray as xr
import numpy as np
import sys

path_clm_3_5 = sys.argv[1]
path_clm_5 = sys.argv[2]


clm_3_5_source = xr.open_dataset(path_clm_3_5)

pft_3_5 = clm_3_5_source['PCT_PFT']
#sai_3_5 = clm_3_5_source['MONTHLY_SAI']
lai_3_5 = clm_3_5_source['MONTHLY_LAI']
#top_3_5 = clm_3_5_source['MONTHLY_HEIGHT_TOP']
#bot_3_5 = clm_3_5_source['MONTHLY_HEIGHT_BOT']


pft_3_5 = pft_3_5.to_numpy()
#sai_3_5 = sai_3_5.to_numpy()
lai_3_5 = lai_3_5.to_numpy()
#top_3_5 = top_3_5.to_numpy()
#bot_3_5 = bot_3_5.to_numpy()



pft_natural = pft_3_5[0:15,:,:]
cft = pft_3_5[15,:,:]
lakes_3_5 = pft_3_5[17,:,:]
glacier_3_5 = pft_3_5[18,:,:]
urban_3_5 = pft_3_5[19,:,:]


#sai = sai_3_5[:,0:15,:,:]
lai = lai_3_5[:,0:15,:,:]
#top = top_3_5[:,0:15,:,:]
#bot = bot_3_5[:,0:15,:,:]



clm5_dest = xr.open_dataset(path_clm_5, mode='a')
#clm5_dest = clm5_dest.isel(cft=slice(0, 2))
#clm5_dest = clm5_dest.isel(lsmpft=slice(0, 17))

clm5_dest.attrs['Urban_raw_data_file_name'] = 'GLC2000'
clm5_dest.attrs['Vegetation_type_raw_data_filename'] = 'GLC2000'

clm5_dest['PCT_URBAN'][2,:,:] = urban_3_5
clm5_dest['PCT_URBAN'][1,:,:] = 0

clm5_dest['PCT_CROP'][:,:] = cft

clm5_dest['PCT_GLACIER'][:,:] = glacier_3_5

clm5_dest['PCT_LAKE'][:,:] = lakes_3_5

clm5_dest['PCT_NATVEG'][:,:] = np.sum(pft_natural, axis=0)

clm5_dest['PCT_NAT_PFT'][:,:,:] = pft_natural


#clm5_dest['MONTHLY_SAI'][:,0:15,:,:]  = sai

clm5_dest['MONTHLY_LAI'][:,0:15,:,:]  = lai

#clm5_dest['MONTHLY_HEIGHT_TOP'][:,0:15,:,:]  = top

#clm5_dest['MONTHLY_HEIGHT_BOT'][:,0:15,:,:]  = bot



#sai_clm5 = clm5_dest['MONTHLY_SAI'].to_numpy()

#lai_clm5 = clm5_dest['MONTHLY_LAI'].to_numpy()

#top_clm5 = clm5_dest['MONTHLY_HEIGHT_TOP'].to_numpy()

#bot_clm5 = clm5_dest['MONTHLY_HEIGHT_BOT'].to_numpy()


#sai_clm5[:,0:15,:,:] = sai

#lai_clm5[:,0:15,:,:]  = lai

#top_clm5[:,0:15,:,:]  = top

#bot_clm5[:,0:15,:,:]  = bot




#clm5_dest["PCT_NAT_PFT"]=(['natpft', 'lsmlat', 'lsmlon'],  pft_natural)
#clm5_dest["MONTHLY_SAI"]=(['time','lsmpft', 'lsmlat', 'lsmlon'],  sai_clm5)
#clm5_dest["MONTHLY_LAI"]=(['time','lsmpft', 'lsmlat', 'lsmlon'],  lai_clm5)
#clm5_dest["MONTHLY_HEIGHT_TOP"]=(['time','lsmpft', 'lsmlat', 'lsmlon'],  top_clm5)
#clm5_dest["MONTHLY_HEIGHT_BOT"]=(['time','lsmpft', 'lsmlat', 'lsmlon'],  bot_clm5)


#clm5_dest["PCT_CFT"]=(['cft', 'lsmlat', 'lsmlon'],  cft)

clm5_dest.to_netcdf(path_clm_5)


clm_3_5_source.close()
clm5_dest.close()
