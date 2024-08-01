ebplotting_mandala.ipynb is completely raw code without any clean-up or comments

identifying_heatwaves.py is a code you can run to identify heatwaves in existing MERRA2 temperature datasets

remove_heatwaves.py is a code that replaces previously identified heatwave periods with a median temperature profile and finds a median summer day to use to replace forcing data

temp_anomaly.py identifies the temperature anomaly of a given heatwave and outputs a csv file for use in synthetic_heatwaves.py

synthetic_heatwaves.py allows for you to supplant the desired heatwave from temp_anomaly.py and put it at a different point in time, as well as allowing for modification of the magnitude of the temperature anomaly to decrease or increase the magnitude of the synthetic heatwave
