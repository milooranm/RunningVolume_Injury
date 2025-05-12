import pandas as pd
import numpy as np
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from APIcall_v2 import main_api_call

def create_emptydf(start_date,end_date):
    """
    Creates empty DataFrame with date range
    Args:
        start_date (str): Start date in 'yyyy-mm-dd' format
        end_date (str): End date in 'yyyy-mm-dd' format
        
    Returns:
        empty (df): Eempty df ready for population
    """
    start_date = str(start_date)
    end_date = str(end_date)
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    date_range = pd.date_range(start, end)

    df = pd.DataFrame({'Date': date_range})
    
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    df['nr. sessions'] = 0
    df['total km'] = 0.00
    df['km Z3-4'] = 0.00
    df['km Z5-T1-T2'] = 0.00
    df['hours alternative'] = 0.00
    return df

def read_df_memory(saved_activity_dictionary):
    '''
    separates out two lists of dictionaries from the downloaded_activities list

    Args: 
        df_memory (list): the list of dictionaries that contains all the downloaded activities in the format:
        {'filename': filename, 'data': data}

    Returns:
        run_activities (list), other_activities (list): two lists of dictionaries that contain the activities that are running and the rest of the activities
    '''
    run_activities = []
    other_activities = []
    for item in saved_activity_dictionary:
        filename = item["filename"]
        data = item["df"]
        # if filename  matches '*Running_*.csv':
        if re.match(r".*Running_.*\.csv$", filename):
            run_activities.append({'filename': filename, 'df': data})
        else:
            other_activities.append({'filename': filename, 'df': data})
    for item in run_activities:
        filename = item["filename"]
        print(filename)
    for item in other_activities:
        filename = item["filename"]
        print(filename)
    
    return run_activities, other_activities

def populateone_memory(df_prepop, file_df, filedate, Z3_min, Z5_min):
    """
    Populates the empty DataFrame with the data from the file
    Args:
        df_prepop (df): DataFrame to be populated
        file_df (df): DataFrame containing activity data
        filedate (str): Date of the activity
        Z3_min (int): Minimum heart rate for Z3 zone
        Z5_min (int): Minimum heart rate for Z5 zone
    Returns:
        df_postpop (df): Populated DataFrame
    """
    file_df['Distance'] = pd.to_numeric(file_df['Distance'], errors='coerce')

    df_prepop.loc[df_prepop['Date'] == filedate, 'total km'] += file_df['Distance'].iloc[-1]

    for idx, row in file_df.iloc[:-1].iterrows():
        print(row['Avg HR']) 
        hr = int(row['Avg HR'])
        distance = row['Distance']
        if Z3_min <= hr < Z5_min:
            df_prepop.loc[df_prepop['Date'] == filedate, 'km Z3-4'] += distance
        elif hr >= Z5_min:
            df_prepop.loc[df_prepop['Date'] == filedate, 'km Z5-T1-T2'] += distance

    return df_prepop

def populatebydate_memory(emptydf, run_activities, other_activities, Z3_min, Z5_min):
    """
    Populates the empty DataFrame with the data from the files
    Args:
        emptydf (df): DataFrame to be populated
        run_activities (list): List of dictionaries containing running activities
        other_activities (list): List of dictionaries containing other activities
        Z3_min (int): Minimum heart rate for Z3 zone
        Z5_min (int): Minimum heart rate for Z5 zone
    Returns:
        emptydf (df): Populated DataFrame
    """
    for i in emptydf['Date']:
        for activity in run_activities:
            filedate = datetime.strptime(activity['filename'].split('_')[1], '%d-%m-%Y').strftime('%Y-%m-%d')
            if filedate == i:
                emptydf.loc[emptydf['Date'] == filedate, 'nr. sessions'] += 1
                populateone_memory(emptydf, activity['df'], filedate, Z3_min, Z5_min)

        for activity in other_activities:
            filedate = datetime.strptime(activity['filename'].split('_')[1], '%d-%m-%Y').strftime('%Y-%m-%d')
            if filedate == i:
                temp_df = activity['df']
                time_str = temp_df['Time'].iloc[-1]
                time_obj = datetime.strptime(time_str, '%H:%M:%S.%f').time()
                time_delta = timedelta(hours=time_obj.hour, minutes=time_obj.minute, seconds=time_obj.second, microseconds=time_obj.microsecond)

                hours_alternative = round(time_delta.total_seconds() / 3600, 2)
                emptydf.loc[emptydf['Date'] == filedate, 'hours alternative'] = hours_alternative

    return emptydf

def convert_to_day_approach(df):
    """
    Converts the DataFrame to a day approach format.
    Args:
        df (DataFrame): The DataFrame to convert.       
    Returns:
        DataFrame: The converted DataFrame into a format with 7 lagging days 
        before each date in the format 
    """
    feature_cols = ['nr. sessions', 'total km', 'km Z3-4', 'km Z5-T1-T2', 'hours alternative']
    df_converted = pd.DataFrame()
    for i in range(0,7):
        for col in feature_cols:
            df_converted[f'{col}.{i}'] = df[col].shift(i)  
    df_converted['Date'] = df['Date']
    # drop rows with NaN values using dropna() with index as the row
    df_converted = df_converted.dropna()

    # replace the name of column.0 with the name of the column
    df_converted = df_converted.rename(columns={col: col[:-2] for col in df_converted.columns if col.endswith('.0')})

    return df_converted 

def main_extract_transform_memory(date_start, date_end, df_memory, Z3_min = 135, Z5_min = 173):   
    """
    Main function to extract and transform data.
    """
    while True:
        # the z3_min and Z5 min need to be inputted by the user here
        #Z3_min = input("Enter the minimum heart rate for your Z3 according to garmin: ") 
        # Z5_min = input("Enter the minimim heart rate for your Z5 according to garmin: ")
        # wrap the input in a try except block to check if the input is a number
        try:
            Z3_min = int(Z3_min)
            Z5_min = int(Z5_min)
            break
        except ValueError:
            print("Please enter valid numbers for heart rate zone thresholds.")
 
    empty = create_emptydf(date_start, date_end)
    r,o = read_df_memory(df_memory)
    
    df_full = populatebydate_memory(empty, r, o, Z3_min, Z5_min)
    
    # Convert to day approach format
    dfday_user = convert_to_day_approach(df_full)
    
    return dfday_user

if __name__ == "__main__":

    start_date, end_date, df_memory = main_api_call()
    main_extract_transform_memory(start_date, end_date, df_memory)
    