import xarray as xr
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error

# Define coordinates, file paths, and other constants
lat = 63.5
lon = -145.625
summer_months = [6, 7, 8]
exclude_years = [2004, 2005, 2006, 2007, 2023]  # Previously identified heatwave years
heatwave_periods = [
    ('2004-06-16', '2004-06-30'),
    ('2004-08-17', '2004-08-24'),
    ('2005-06-09', '2005-06-14'),
    ('2005-08-10', '2005-08-16'),
    ('2006-06-10', '2006-06-15'),
    ('2007-08-26', '2007-08-31'),
    ('2023-07-23', '2023-07-29')
]

file_path = '/Users/manda/REU24/climate_data/MERRA2/T2M/MERRA2_T2M_60_-150.nc'
output_file_path = '/Users/manda/REU24/climate_data/MERRA2/T2M/MERRA2_T2M_no_heatwave.nc'
variables = [
    'BCDP002', 'BCWT002', 'CLDTOT', 'DUDP003', 'DUWT003', 'LWGAB',
    'PRECTOTCORR', 'PS', 'RH2M', 'SWGDN', 'U2M', 'V2M'
]

# Load the dataset
ds = xr.open_dataset(file_path)
t2m = ds['T2M'].sel(lat=lat, lon=lon, method='nearest')

# Convert time to pandas datetime
t2m['time'] = pd.to_datetime(t2m['time'].values)

# Filter for summer months
summer_t2m = t2m.sel(time=t2m['time.month'].isin(summer_months))

# Convert to DataFrame for easier handling
df_summer_t2m = summer_t2m.to_dataframe().reset_index()
df_summer_t2m['hour'] = df_summer_t2m['time'].dt.hour
df_summer_t2m['day_of_year'] = df_summer_t2m['time'].dt.dayofyear

# Calculate the median temperature for each hour of the summer period
hourly_median_temps = df_summer_t2m.groupby(['day_of_year', 'hour'])['T2M'].median().reset_index()
hourly_median_temps['time'] = pd.to_datetime('2000') + pd.to_timedelta(hourly_median_temps['day_of_year'] - 1, unit='D') + pd.to_timedelta(hourly_median_temps['hour'], unit='h')

# Create a new DataFrame to hold the modified data
df_t2m_point = t2m.to_dataframe().reset_index()

# Identify the best median summer day to replace forcing data for heatwave periods
best_day, lowest_mse = None, float('inf')
for day in df_summer_t2m['time'].dt.date.unique():
    day_df = df_summer_t2m[df_summer_t2m['time'].dt.date == day]
    if len(day_df) == 24:  # Ensure complete day with 24 hourly temperatures
        merged_df = day_df.merge(hourly_median_temps, on='hour', suffixes=('_day', '_median'))
        mse = mean_squared_error(merged_df['T2M_day'], merged_df['T2M_median'])
        if mse < lowest_mse:
            lowest_mse = mse
            best_day = day

# Replace heatwave days with the median temperature profile
for start_date, end_date in heatwave_periods:
    for date in pd.date_range(start_date, end_date):
        day_of_year = date.dayofyear
        for hour in range(24):
            mask = (
                (df_t2m_point['time'].dt.year == date.year) & 
                (df_t2m_point['time'].dt.dayofyear == day_of_year) & 
                (df_t2m_point['time'].dt.hour == hour)
            )
            median_temp = hourly_median_temps[
                (hourly_median_temps['day_of_year'] == day_of_year) & 
                (hourly_median_temps['hour'] == hour)
            ]['T2M'].values[0]
            df_t2m_point.loc[mask, 'T2M'] = median_temp

# Convert the modified DataFrame back to an xarray Dataset
ds_modified = df_t2m_point.set_index(['time']).to_xarray()

unique_lats = np.unique(ds_modified['lat'].values)
unique_lons = np.unique(ds_modified['lon'].values)

# Reshape the T2M variable and create a new dataset with the desired structure
reshaped_T2M = ds_modified['T2M'].values.reshape(len(ds_modified['time']), len(unique_lats), len(unique_lons))
ds_new_restructured = xr.Dataset(
    {'T2M': (['time', 'lat', 'lon'], reshaped_T2M)},
    coords={'time': ds_modified['time'], 'lat': unique_lats, 'lon': unique_lons}
)
ds_new_restructured['T2M'].attrs['units'] = 'K'
ds_new_restructured.to_netcdf(output_file_path)

# Replace forcing data with identified best day
for var in variables:
    filename = f'/Users/manda/REU24/climate_data/MERRA2/{var}/MERRA2_{var}_60_-150.nc'
    data = xr.open_dataset(filename)
    data_location = data.sel(lat=lat, lon=lon, method='nearest')
    data_location['time'] = pd.to_datetime(data_location['time'].values)

    replacement_data = data_location.sel(time=slice(f'{best_day} 00:30:00', f'{best_day} 23:30:00'))[var]
    
    for start_date, end_date in heatwave_periods:
        for date in pd.date_range(start_date, end_date):
            time_slice = slice(f'{date.strftime("%Y-%m-%d")} 00:30:00', f'{date.strftime("%Y-%m-%d")} 23:30:00')
            data_location[var].loc[{'time': time_slice}] = replacement_data.values

    data.loc[{'lat': lat, 'lon': lon}] = data_location
    output_filename = f'/Users/manda/REU24/climate_data/MERRA2/{var}/MERRA2_{var}_no_heatwave.nc'
    data.to_netcdf(output_filename)
