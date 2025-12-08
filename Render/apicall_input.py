import datetime
import logging
import os
import csv
import sys
from getpass import getpass
import requests
from io import BytesIO
import pandas as pd
import re
from dotenv import load_dotenv


from typing import List, Dict, Optional, Tuple
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()



def init_api(email: str, password: str) -> Optional[Garmin]:
    """Initialize Garmin API with your credentials."""
    try:
        garmin = Garmin(email, password)
        garmin.login()
        print("Login successful!")
    except Exception as e:
        logger.error(e)
        print(f"An error occurred during login: {e}")

    return garmin


# Deprecated function prior to in-memory handling!!!
'''
def get_activity_files(api, start_date, end_date, output_dir="./"):
    """Downloads activity files within a date range."""
    
    try:
        activities = api.get_activities_by_date(
            start_date.isoformat(), end_date.isoformat()
        )

        for activity in activities:
            activity_start_time = datetime.datetime.strptime(
                activity["startTimeLocal"], "%Y-%m-%d %H:%M:%S"
            ).strftime("%d-%m-%Y")
            activity_id = activity["activityId"]
            activity_name = activity["activityName"]

            csv_data = api.download_activity(
                activity_id, dl_fmt=api.ActivityDownloadFormat.CSV
            )
            output_file = os.path.join(output_dir, f"{str(activity_name)}_{str(activity_start_time)}_{str(activity_id)}.csv")
            with open(output_file, "wb") as fb:
                fb.write(csv_data)
            print(f"Activity data downloaded to file {output_file}")

    except (
        GarminConnectConnectionError,
        GarminConnectAuthenticationError,
        GarminConnectTooManyRequestsError,
        requests.exceptions.HTTPError,
    ) as err:
        logger.error(err)
        print("Error downloading activities.")
'''

# create a map for what cols I want and apply it to everything going through?
def get_activities(api: Garmin, start_date: datetime.date, end_date: datetime.date, Z3_min: int = 135, Z5_min: int  = 172) -> Tuple[List[Dict], List[Dict]]: 
    """
    Retrieves activity data within a date range and returns two lists of per-day dicts:
    - run_daily: [{ 'date': DD-MM-YYYY, 'total_km': float, 'km_z34': float, 'km_z5plus': float }]
    - other_daily: [{ 'date': DD-MM-YYYY, 'hours_alternative': float }]
    """
    run_by_date: Dict[str, Dict] = {}
    other_by_date: Dict[str, Dict] = {}
    run_cols = ['Distance', 'Avg HR','Time']
    other_cols = ['Time']
    try:
        activities = api.get_activities_by_date(
            start_date.isoformat(), end_date.isoformat()
        )

        for activity in activities:
            activity_start_date = datetime.datetime.strptime(
                activity["startTimeLocal"], "%Y-%m-%d %H:%M:%S"
            ).strftime("%d-%m-%Y")
            activity_type = activity.get('activityType', {}).get('typeKey', 'unknown')
            activity_id = activity["activityId"]
            csv_data = api.download_activity(
                activity_id, dl_fmt=api.ActivityDownloadFormat.CSV
            )
            # Is it a running activity?
            if activity_type and activity_type.lower() == 'running':
                run_df = pd.read_csv(BytesIO(csv_data), usecols = run_cols)
                total_km = float(run_df['Distance'].iloc[-1])
                segment = run_df.iloc[:-1]
                hr = segment['Avg HR']
                distance = segment['Distance']
                z34_sum = float(distance[(hr >= Z3_min) & (hr < Z5_min)].sum())
                z5_sum  = float(distance[hr >= Z5_min].sum())

                # Aggregate into per-day dict
                if activity_start_date not in run_by_date:
                    run_by_date[activity_start_date] = {'total_km': 0.0,'km_z34': 0.0,'km_z5plus': 0.0, 'nr. sessions': 0}
                run_by_date[activity_start_date]['total_km'] += total_km
                run_by_date[activity_start_date]['km_z34'] += z34_sum
                run_by_date[activity_start_date]['km_z5plus'] += z5_sum
                run_by_date[activity_start_date]['nr. sessions'] += 1
            else: 
                other_df = pd.read_csv(BytesIO(csv_data), usecols = other_cols)
                # Parse to hours and aggregate per-day
                time_str = other_df['Time'].iloc[-1]
                time_obj = datetime.datetime.strptime(time_str, '%H:%M:%S.%f').time()
                time_delta = datetime.timedelta(hours=time_obj.hour, minutes=time_obj.minute, seconds=time_obj.second, microseconds=getattr(time_obj, 'microsecond', 0))
                hours_alternative = round(time_delta.total_seconds() / 3600, 2)

                if activity_start_date not in other_by_date:
                    other_by_date[activity_start_date] = {'hours_alternative': 0.0,}
                other_by_date[activity_start_date]['hours_alternative'] += hours_alternative                

    except (
        GarminConnectConnectionError,
        GarminConnectAuthenticationError,
        GarminConnectTooManyRequestsError,
        requests.exceptions.HTTPError,
    ) as err:
        logger.error(f'error in get_activity_dataframes :{err}')
        print(f"Error downloading activities: {err}")
        return [], []

    # Convert aggregated maps to lists of single dicts per date
    run_daily: List[Dict] = [{'date': d, **vals} for d, vals in run_by_date.items()]
    other_daily: List[Dict] = [{'date': d, **vals} for d, vals in other_by_date.items()]
    return run_daily, other_daily


def main_api_call(email: str =None, password: str = None, Z3_min: int  = 135, Z5_min: int = 172) -> Tuple[datetime.date, datetime.date, Dict[str, pd.DataFrame]]: 
    """Main function to download Garmin Connect activities."""
    print("Garmin Connect API - Activity Downloader")

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=120)

    if not email or not password:
        logger.error("Email and password are required for authentication.")
        print("Email and password are required for authentication.")
        return 0, 0, 0

    api = init_api(email, password)

    if not api:
        logger.error("Failed to initialize Garmin API. Exiting.")
        print("Failed to initialize Garmin API. Exiting.")
        return None, None, None

    runs, alt = get_activities(api, start_date, end_date, Z3_min=135, Z5_min=172)

    return start_date, end_date, runs, alt

if __name__ == "__main__":


        
    email = os.getenv('EMAIL')
    password = os.getenv('PASSWORD')


    start_date ,end_date, runs, alt = main_api_call(email, password)
    print(runs)
