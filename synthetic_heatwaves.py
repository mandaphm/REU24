import xarray as xr
import pandas as pd
import numpy as np

# Define the coordinates and file paths
lat = 63.5
lon = -145.625
heatwave_period = ('2004-05-01T00:30:00', '2004-05-09T23:30:00')  # Example new heatwave period
original_heatwave_period = ('2004-06-16T00:30:00', '2004-06-30T23:30:00')  # Original period of heatwave
input_file_path = '/Users/manda/REU24/climate_data/MERRA2/T2M/MERRA2_T2M_no_heatwave.nc'
output_file_path = '/Users/manda/REU24/climate_data/MERRA2/T2M/MERRA2_T2M_no_heatwave_with_anomaly.nc'
csv_path = '/Users/manda/REU24/Output/MERRA2_processing/heatwave_anomalies.csv'

# Load the dataset to be modified
ds_modify = xr.open_dataset(input_file_path)

# Select the T2M variable for the dataset to be modified
t2m_modify = ds_modify['T2M']

# Load precomputed temperature anomalies
df_heatwave = pd.read_csv(csv_path)

# Convert CSV datetime to pandas datetime
df_heatwave['datetime'] = pd.to_datetime(df_heatwave['datetime'])

# Define the heatwave start and end dates for the new period
heatwave_start = pd.to_datetime(heatwave_period[0])
heatwave_end = pd.to_datetime(heatwave_period[1])

# Define the original heatwave start and end dates
original_heatwave_start = pd.to_datetime(original_heatwave_period[0])
original_heatwave_end = pd.to_datetime(original_heatwave_period[1])

# Calculate the offset between the original and new heatwave periods
original_period_days = (original_heatwave_end - original_heatwave_start).days
new_period_days = (heatwave_end - heatwave_start).days

# Create a mask for the new heatwave period
mask_time_range = (t2m_modify['time'] >= heatwave_start) & (t2m_modify['time'] <= heatwave_end)

# Extract the subset of the data for the new heatwave period
t2m_subset = t2m_modify.sel(time=slice(heatwave_start, heatwave_end))

# Ensure the anomalies are aligned with the original heatwave period
anomaly_data = df_heatwave.set_index('datetime').reindex(pd.date_range(start=original_heatwave_start, end=original_heatwave_end, freq='H'))['temperature_anomaly'].values

# Handle any potential NaNs
if np.any(np.isnan(anomaly_data)):
    print("Warning: NaNs detected in anomaly data")

# Adjust the anomalies to the new period
anomaly_data_expanded = np.tile(anomaly_data, int(np.ceil(new_period_days / original_period_days)))[:len(t2m_subset.time)]
anomaly_data_expanded = anomaly_data_expanded.reshape(-1, 1, 1)  # Expand dimensions to match (time, lat, lon)

magnitude = 1 #Adjust to change the magnitude of the heatwave, or keep at 1 to remain the same

# Add the temperature anomalies to the subset
t2m_subset.values += anomaly_data_expanded*magnitude

# Update the original dataset with the modified values
ds_modify['T2M'].loc[dict(time=slice(heatwave_start, heatwave_end))] = t2m_subset

unique_lats = np.unique(ds_modify['lat'].values)
unique_lons = np.unique(ds_modify['lon'].values)

lat_dim = xr.DataArray(unique_lats, dims='lat', name='lat')
lon_dim = xr.DataArray(unique_lons, dims='lon', name='lon')
reshaped_T2M = ds_modify['T2M'].values.reshape(len(ds_modify['time']), len(unique_lats), len(unique_lons))

ds_new_restructured = xr.Dataset(
    {'T2M': (['time', 'lat', 'lon'], reshaped_T2M)},
    coords={'time': ds_modify['time'], 'lat': lat_dim, 'lon': lon_dim}
)
ds_new_restructured['T2M'].attrs['units'] = 'K'

# Save the modified dataset
ds_modify.to_netcdf(output_file_path)
