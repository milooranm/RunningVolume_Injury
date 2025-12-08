import pandas as pd
import numpy as np
import re
import logging

from datetime import datetime, timedelta, date
from pathlib import Path

from io import BytesIO
from typing import Dict, List, Optional, Tuple

from apicall_input import main_api_call 

def create_emptydf(start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
    """
    Creates empty DataFrame with date range
    Args:
        start_date (str): Start date in 'yyyy-mm-dd' format
        end_date (str): End date in 'yyyy-mm-dd' format
    Returns:
        empty (df): Eempty df ready for population
    """
    date_range = pd.date_range(start_date, end_date)
    df = pd.DataFrame({'Date': date_range})
    
    df['Date'] = df['Date'].dt.strftime('%d-%m-%Y')
    df['nr. sessions'] = 0
    df['total km'] = 0.00
    df['km Z3-4'] = 0.00
    df['km Z5-T1-T2'] = 0.00
    df['hours alternative'] = 0.00
    return df

# there were files doing this very much not in memory
def populatebydate_memory(emptydf: pd.DataFrame, run_daily: List[Dict], other_daily: List[Dict], Z3_min: int, Z5_min: int)-> pd.DataFrame:
    """
    Populates the empty DataFrame with summed data per date from running and other activities.
    """
    # Build quick lookup maps keyed by day string (DD-MM-YYYY)
    run_map: Dict[str, Dict] = {entry['date']: entry for entry in run_daily}
    other_map: Dict[str, Dict] = {entry['date']: entry for entry in other_daily}

    for day in emptydf['Date']:
        if day in run_map:
            r = run_map[day]
            emptydf.loc[emptydf['Date'] == day, 'nr. sessions'] += r.get('nr. sessions', 0)
            emptydf.loc[emptydf['Date'] == day, 'total km'] += r.get('total_km', 0.0)
            emptydf.loc[emptydf['Date'] == day, 'km Z3-4'] += r.get('km_z34', 0.0)
            emptydf.loc[emptydf['Date'] == day, 'km Z5-T1-T2'] += r.get('km_z5plus', 0.0)
        if day in other_map:
            emptydf.loc[emptydf['Date'] == day, 'hours alternative'] += other_map[day].get('hours_alternative', 0.0)

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

    # drop rows at the top with NaN values 
    df_converted = df_converted.dropna()

    # remove suffix for the first set of columns to match prediction model columns
    df_converted = df_converted.rename(columns={col: col[:-2] for col in df_converted.columns if col.endswith('.0')})

    return df_converted 

def initial_transform(start_date, end_date, runs, other, Z3_min = 135, Z5_min = 173):   
    """
    Main function to extract and transform data.
    """
    try:
        Z3_min = int(Z3_min)
        Z5_min = int(Z5_min)
    except ValueError:
        print("Please enter valid numbers for heart rate zone thresholds.")
   
    empty = create_emptydf(start_date, end_date)
    df_full = populatebydate_memory(empty, runs, other, Z3_min, Z5_min)
    
    # Convert to day approach format
    dfday_user = convert_to_day_approach(df_full)
    
    return dfday_user

# I wanted to feature engineer some columns and condense some others, 
# so I have like three functions of slop trying to apply what I applied to the training dataset here
# took me a lot of painstaking spot checks to be sure they worked, 
# possibly could have written unit tests for them instead
def create_combodf(df):
    """
    Create a DataFrame with day-based aggregations.
    """
    combodf = pd.DataFrame()
    combodf['Date'] = df['Date']
    combodf['Day1 total km'] = df['total km']
    combodf['Day1 km z3+'] = df['km Z3-4'] + df['km Z5-T1-T2']
    combodf['Day1 km z5'] = df['km Z5-T1-T2']
    combodf['Day2-3 nr.sessions'] = df['nr. sessions.1'] + df['nr. sessions.2']
    combodf['Day2-3 total km'] = df['total km.1'] + df['total km.2']
    combodf['Day2-3 km z3+'] = (
        df['km Z3-4.1'] + df['km Z3-4.2'] + df['km Z5-T1-T2.1'] + df['km Z5-T1-T2.2']
    )
    combodf['Day2-3 km z5'] = df['km Z5-T1-T2.1'] + df['km Z5-T1-T2.2']
    combodf['Day4-7 nr.sessions'] = (
        df['nr. sessions.3'] + df['nr. sessions.4'] + df['nr. sessions.5'] + df['nr. sessions.6']
    )
    combodf['Day4-7 total km'] = (
        df['total km.3'] + df['total km.4'] + df['total km.5'] + df['total km.6']
    )
    combodf['Day4-7 km z3+'] = (
        df['km Z3-4.3'] + df['km Z3-4.4'] + df['km Z3-4.5'] + df['km Z3-4.6'] +
        df['km Z5-T1-T2.3'] + df['km Z5-T1-T2.4'] + df['km Z5-T1-T2.5'] + df['km Z5-T1-T2.6']
    )
    return combodf

def create_weekly_df(df):
    """
    Create a DataFrame with week-based aggregations.
    """
    weekly_df = pd.DataFrame()
    weekly_df['Date'] = df['Date']
    weekly_df['Week1 max km one day'] = (
        df[['total km', 'total km.1', 'total km.2', 'total km.3', 'total km.4', 'total km.5', 'total km.6']]
        .shift(7).max(axis=1)
    )
    weekly_df['Week1 total km z3+'] = (
        df[['km Z3-4', 'km Z3-4.1', 'km Z3-4.2', 'km Z3-4.3', 'km Z3-4.4', 'km Z3-4.5', 'km Z3-4.6']]
        .shift(7).sum(axis=1) +
        df[['km Z5-T1-T2', 'km Z5-T1-T2.1', 'km Z5-T1-T2.2', 'km Z5-T1-T2.3', 'km Z5-T1-T2.4', 'km Z5-T1-T2.5', 'km Z5-T1-T2.6']]
        .shift(7).sum(axis=1)
    )
    weekly_df['Week1 max km Z3+ one day'] = (
        df[['km Z3-4', 'km Z3-4.1', 'km Z3-4.2', 'km Z3-4.3', 'km Z3-4.4', 'km Z3-4.5', 'km Z3-4.6']]
        .shift(7).max(axis=1) +
        df[['km Z5-T1-T2', 'km Z5-T1-T2.1', 'km Z5-T1-T2.2', 'km Z5-T1-T2.3', 'km Z5-T1-T2.4', 'km Z5-T1-T2.5', 'km Z5-T1-T2.6']]
        .shift(7).max(axis=1)
    )
    # Repeat for Week2
    weekly_df['Week2 max km one day'] = (
        df[['total km', 'total km.1', 'total km.2', 'total km.3', 'total km.4', 'total km.5', 'total km.6']]
        .shift(14).max(axis=1)
    )
    weekly_df['Week2 total km z3+'] = (
        df[['km Z3-4', 'km Z3-4.1', 'km Z3-4.2', 'km Z3-4.3', 'km Z3-4.4', 'km Z3-4.5', 'km Z3-4.6']]
        .shift(14).sum(axis=1) +
        df[['km Z5-T1-T2', 'km Z5-T1-T2.1', 'km Z5-T1-T2.2', 'km Z5-T1-T2.3', 'km Z5-T1-T2.4', 'km Z5-T1-T2.5', 'km Z5-T1-T2.6']]
        .shift(14).sum(axis=1)
    )
    weekly_df['Week2 max km Z3+ one day'] = (
        df[['km Z3-4', 'km Z3-4.1', 'km Z3-4.2', 'km Z3-4.3', 'km Z3-4.4', 'km Z3-4.5', 'km Z3-4.6']]
        .shift(14).max(axis=1) +
        df[['km Z5-T1-T2', 'km Z5-T1-T2.1', 'km Z5-T1-T2.2', 'km Z5-T1-T2.3', 'km Z5-T1-T2.4', 'km Z5-T1-T2.5', 'km Z5-T1-T2.6']]
        .shift(14).max(axis=1)
    )
    weekly_df.dropna(inplace=True)

    return weekly_df

def calculate_ratios_and_acwr(newdf,combodf,weekly_df):
    '''
    use weekly aggregates and lagged aggregates to calculate some 5 day -> 3 week ratios and the ACWR 
    '''

    # create some lagged values
    # Week 0 (current week)
    Week0_total_km = newdf[['total km', 'total km.1', 'total km.2', 'total km.3', 'total km.4', 'total km.5', 'total km.6']].sum(axis=1)
    Week0_hours_alternative = newdf[['hours alternative', 'hours alternative.1', 'hours alternative.2', 'hours alternative.3', 'hours alternative.4', 'hours alternative.5', 'hours alternative.6']].sum(axis=1)

    # Week 1 (1 week prior)
    Week1_total_km = newdf[['total km', 'total km.1', 'total km.2', 'total km.3', 'total km.4', 'total km.5', 'total km.6']].shift(7).sum(axis=1)
    Week1_n_sessions = newdf[['nr. sessions', 'nr. sessions.1', 'nr. sessions.2', 'nr. sessions.3', 'nr. sessions.4', 'nr. sessions.5', 'nr. sessions.6']].shift(7).sum(axis=1)
    Week1_hours_alternative = newdf[['hours alternative', 'hours alternative.1', 'hours alternative.2', 'hours alternative.3', 'hours alternative.4', 'hours alternative.5', 'hours alternative.6']].shift(7).sum(axis=1)

    # Week 2 (two weeks prior)
    Week2_total_km = newdf[['total km', 'total km.1', 'total km.2', 'total km.3', 'total km.4', 'total km.5', 'total km.6']].shift(14).sum(axis=1)
    Week2_n_sessions = newdf[['nr. sessions', 'nr. sessions.1', 'nr. sessions.2', 'nr. sessions.3', 'nr. sessions.4', 'nr. sessions.5', 'nr. sessions.6']].shift(14).sum(axis=1)
    Week2_hours_alternative = newdf[['hours alternative', 'hours alternative.1', 'hours alternative.2', 'hours alternative.3', 'hours alternative.4', 'hours alternative.5', 'hours alternative.6']].shift(14).sum(axis=1)


    # total km ratio
    day5totkm = newdf[['total km', 'total km.1', 'total km.2', 'total km.3', 'total km.4']].sum(axis=1)
    week3totkm =  Week0_total_km + Week1_total_km + Week2_total_km
    combodf['5day/3W tot km ratio'] = np.where( week3totkm != 0, (day5totkm / week3totkm).round(3),0)

    # kms at z3+ ratio
    day5kmz3plus = newdf[['km Z3-4', 'km Z3-4.1', 'km Z3-4.2', 'km Z3-4.3', 'km Z3-4.4', 'km Z5-T1-T2', 'km Z5-T1-T2.1', 'km Z5-T1-T2.2', 'km Z5-T1-T2.3', 'km Z5-T1-T2.4']].sum(axis=1)
    week3kmz3plus = day5kmz3plus + newdf[['km Z3-4.5', 'km Z3-4.6', 'km Z5-T1-T2.5', 'km Z5-T1-T2.6']].sum(axis=1) + weekly_df[['Week1 total km z3+', 'Week2 total km z3+']].sum(axis=1)
    day5propz3plus = np.where(day5totkm != 0, (day5kmz3plus / day5totkm).round(3), 0)
    week3propz3plus = np.where(week3totkm != 0, (week3kmz3plus / week3totkm).round(3), 0)
    combodf['5day/3W proportion km z3+'] = np.where(
    week3propz3plus != 0, (day5propz3plus / week3propz3plus).round(3), 0)

    # n sessions ratio
    day5nsessions = newdf[['nr. sessions', 'nr. sessions.1', 'nr. sessions.2', 'nr. sessions.3', 'nr. sessions.4']].sum(axis=1)
    week3nsessions = day5nsessions + newdf[['nr. sessions.5', 'nr. sessions.6']].sum(axis=1) + Week1_n_sessions + Week2_n_sessions
    combodf['5day/3W nr. sessions ratio'] = np.where(
    week3nsessions != 0, (day5nsessions / week3nsessions).round(3), 0)

    # hours alt ratio
    day5hoursalt = newdf[['hours alternative', 'hours alternative.1', 'hours alternative.2', 'hours alternative.3', 'hours alternative.4']].sum(axis=1)
    week3hoursalt = Week0_hours_alternative + Week1_hours_alternative + Week2_hours_alternative
    combodf['5day/3W hours alternative training ratio'] = np.where( week3hoursalt != 0, (day5hoursalt / week3hoursalt).round(3),0)
    
    # ACWR
    # explain my arbitrary formula here
    combodf['ACWR'] = np.where(
        (week3totkm + (week3propz3plus * week3totkm)) != 0,
        ((day5totkm + (day5propz3plus* day5totkm))*4)/ 
        (week3totkm + (week3propz3plus * week3totkm)), 0).round(3)

    return combodf

def refactor(df):
    
    combodf = create_combodf(df)
    weekly_df = create_weekly_df(df)
    merge_df = pd.merge(combodf, weekly_df, on='Date', how='inner')
    newdf = df[df['Date'].isin(weekly_df['Date'])]

    combodf = calculate_ratios_and_acwr(newdf, merge_df, weekly_df)
    
    return combodf

def main_extract_transform(start_date, end_date, runs, other, Z3_min = 135, Z5_min = 173):
    df = initial_transform(start_date, end_date, runs, other, Z3_min, Z5_min)
    refactored_df = refactor(df)
    print(refactored_df)
    return refactored_df
