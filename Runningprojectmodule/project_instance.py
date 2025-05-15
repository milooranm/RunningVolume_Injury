import pandas as pd
import numpy as np
import pickle
from APIcall_v2 import main_api_call
from data_extraction import main_extract_transform_memory

# call the two preprocessing functions
start_date, end_date, df_memory = main_api_call()
df = main_extract_transform_memory(start_date, end_date, df_memory)

# Return statistics relating to user data
def normalize_user(row, mean_df, std_df):
    mu = mean_df
    su = std_df
    z = (row - mu)/su
    return z

# Calculate the means and standard deviations of all healthy events per athlete
def getMeanStd_user(data):
    mean = data.mean()
    std = data.std()
    std.replace(to_replace=0.0, value=0.01, inplace=True)
    return mean, std

user_test_means, user_test_std = getMeanStd_user(df.copy())
# Normalize the data
user_normalized = df.apply(lambda x: normalize_user(x, user_test_means,user_test_std), axis=1)
user_normalized = user_normalized.drop(columns=[ 'Date'], errors='ignore')

# import the model
with open('.\models\mvp1_logistic_model.pkl', 'rb') as file:
    model = pickle.load(file)

# make predictions
predictions = model.predict(user_normalized)
# make probability predictions
probs = model.predict_proba(user_normalized)[:, 1]

# create a df of predictions using the date column from dfday_user and the predictions
df['injury predictions'] = predictions
df['injury probabilities'] = probs
df[['Date','injury predictions','injury probabilities']].head(30)

# plot the probabilities over time
import matplotlib.pyplot as plt
# add a colour gradient to the plot based on the injury probabilities -red is high, blue is low

import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.dates as mdates

# add a colour gradient to the background based on the x axis -red is high, blue is low, with adjustable transparency
cmap = cm.get_cmap('coolwarm')
norm = mcolors.Normalize(vmin=0, vmax=1)



#plt.figure(figsize=(16,8))
#plt.plot(df['Date'],df['injury probabilities'])
# fix the date axis titles to use every 3rd date in the format mm/dd
# select the last 5 chars of the date string to get the mm/dd format
#plt.xticks(df['Date'][::5], rotation=20, ha='right')
# plot the probabilities over time with a rolling mean
plt.figure(figsize=(10,5))
plt.plot(df['Date'],df['injury probabilities'].rolling(window=5).mean())
plt.xticks(df['Date'][::5], rotation=45, ha='right')
plt.savefig('rolling_mean_plot.png')
# save and display the images
plt.show()