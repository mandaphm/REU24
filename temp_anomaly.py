import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Define the coordinates and file path
lat = 63.5
lon = -145.625
summer_months = [6, 7, 8]
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
output_csv_path = '/Users/manda/REU24/Output/MERRA2_processing/heatwave_anomalies.csv'

# Load the dataset
ds_notsubset = xr.open_dataset(file_path)

# Select the T2M variable
t2m = ds_notsubset['T2M']

# Select the nearest point to the given lat/lon
t2m_point = t2m.sel(lat=lat, lon=lon, method='nearest')

# Convert the time dimension to pandas datetime
t2m_point['time'] = pd.to_datetime(t2m_point['time'].values)

# Filter data for summer months
is_summer = t2m_point['time.month'].isin(summer_months)
summer_t2m = t2m_point.sel(time=is_summer)

# Convert to DataFrame for easier handling
df_summer_t2m = summer_t2m.to_dataframe().reset_index()

df_summer_t2m['hour'] = df_summer_t2m['time'].dt.hour
df_summer_t2m['day_of_year'] = df_summer_t2m['time'].dt.dayofyear

hourly_median_temps = df_summer_t2m.groupby(['day_of_year', 'hour'])['T2M'].median().reset_index()

hourly_median_temps['time'] = pd.to_datetime('2000') + pd.to_timedelta(hourly_median_temps['day_of_year'] - 1, unit='D') + pd.to_timedelta(hourly_median_temps['hour'], unit='h')

# Filter data for the heatwave period
start_date = '2004-06-16T00:30:00'
end_date = '2004-06-30T23:30:00'

mask = (df_summer_t2m['time'] >= start_date) & (df_summer_t2m['time'] <= end_date)
df_heatwave = df_summer_t2m[mask]

# Calculate the temperature anomaly for the heatwave period
df_heatwave['hour'] = df_heatwave['time'].dt.hour
df_heatwave['day_of_year'] = df_heatwave['time'].dt.dayofyear

df_heatwave = df_heatwave.merge(hourly_median_temps, on=['day_of_year', 'hour'], suffixes=('', '_median'))
df_heatwave['temperature_anomaly'] = df_heatwave['T2M'] - df_heatwave['T2M_median']

# Convert back to datetime for plotting
df_heatwave['datetime'] = df_heatwave['time']
df_heatwave.to_csv(output_csv_path, index=False)

# Plot the temperature anomaly for the heatwave period
plt.figure(figsize=(15, 7))
plt.plot(df_heatwave['datetime'], df_heatwave['temperature_anomaly'], label='Temperature Anomaly')
plt.title('Temperature Anomaly at 63.5°N, 145.625°W (2004-06-16 to 2004-06-30)')
plt.xlabel('Date and Time')
plt.ylabel('Temperature Anomaly (K)')
plt.legend()
plt.grid(True)
plt.show()