import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#Isolating the Max Daily Temperatures

lat = 63.5
lon = -145.625
summer_months = [6, 7, 8]
month_names = ['June', 'July', 'August']

file_path = '/Users/manda/REU24/climate_data/MERRA2/T2M/MERRA2_T2M_60_-150.nc'
output_file_path_max = '/Users/manda/REU24/Output/MERRA2_processing/daily_max_temps.nc'

ds_notsubset = xr.open_dataset(file_path)

# Select the T2M variable (assuming it's named 'T2M' in the dataset)
t2m = ds_notsubset['T2M']

# Select the nearest point to the given lat/lon
t2m_point = t2m.sel(lat=lat, lon=lon, method='nearest')

# Convert the time dimension to pandas datetime
t2m_point['time'] = pd.to_datetime(t2m_point['time'].values)

# Resample to daily frequency and take the maximum temperature for each day
daily_max_temps = t2m_point.resample(time='D').max()

daily_max_temps.to_netcdf(output_file_path_max)

#Identify 90th Percentile

output_file_path_90 = '/Users/manda/REU24/Output/MERRA2_processing/daily_max_temps_90th_percentile.nc'
percentile_90 = daily_max_temps.groupby('time.dayofyear').reduce(np.percentile, q=90)

percentile_90.to_netcdf(output_file_path_90)

#Subset Data to Get Summer Months

time_index = pd.to_datetime(daily_max_temps['time'].values)
is_2004_summer = (time_index.year == 2004) & (time_index.month.isin(summer_months))
ds_2004_summer = daily_max_temps.isel(time=is_2004_summer)

df_percentile_90 = percentile_90.to_dataframe(name='90thPercentileTemperature').reset_index()
df_percentile_90['Date'] = pd.to_datetime(df_percentile_90['dayofyear'], format='%j')
df_percentile_90['Date'] = df_percentile_90['Date'].apply(lambda x: x.replace(year=2004))
df_percentile_90 = df_percentile_90[df_percentile_90['Date'].dt.month.isin(summer_months)]

df_percentile_90_copy = df_percentile_90.copy()

#Find Periods Exceeding 90th Percentile

def merge_overlapping_periods(periods):
    sorted_periods = sorted(periods)
    merged_periods = []

    for start, end in sorted_periods:
        if merged_periods and start <= merged_periods[-1][1]:  # Overlapping or consecutive
            merged_periods[-1] = (merged_periods[-1][0], max(end, merged_periods[-1][1]))
        else:
            merged_periods.append((start, end))

    return merged_periods

def find_periods_exceeding_threshold(daily_max_temps, percentile_data, summer_months, consecutive_days_threshold):
    periods_exceeding_mask = []

    is_summer = daily_max_temps['time.month'].isin(summer_months)
    ds_summer = daily_max_temps.sel(time=is_summer)

    years = range(2000, 2024)
    df_percentile_copy = percentile_data.copy()
    df_percentile_copy['Date'] = pd.to_datetime(df_percentile_copy['dayofyear'], format='%j')

    for year in years:
        df_percentile_copy_year = df_percentile_copy.copy()
        df_percentile_copy_year['Date'] = df_percentile_copy_year['Date'].apply(lambda x: x.replace(year=year))

        percentile_mask = df_percentile_copy_year['90thPercentileTemperature'].values

        temperatures = ds_summer.values

        exceed_count = 0
        exceed_start = None
        exceed_end = None

        for i in range(len(temperatures)):
            if temperatures[i] > percentile_mask[i%92]:
                if exceed_count == 0:
                    exceed_start = ds_summer['time'][i].values
                exceed_count += 1
            else:
                if exceed_count >= consecutive_days_threshold:
                    exceed_end = ds_summer['time'][i-1].values
                    periods_exceeding_mask.append((exceed_start, exceed_end))
                exceed_count = 0

        if exceed_count >= consecutive_days_threshold:
            exceed_end = ds_summer['time'][-1].values
            periods_exceeding_mask.append((exceed_start, exceed_end))

    periods_exceeding_mask = merge_overlapping_periods(periods_exceeding_mask)

    return periods_exceeding_mask

# Example usage:

consecutive_days_threshold = 6

periods_exceeding_threshold = find_periods_exceeding_threshold(daily_max_temps, df_percentile_90_copy, summer_months, consecutive_days_threshold)

for start, end in periods_exceeding_threshold:
    print(f"Period exceeding {consecutive_days_threshold} consecutive days above 90th percentile: {start} to {end}")