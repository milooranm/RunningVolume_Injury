import datetime
import logging
import os
import csv
from getpass import getpass
import requests
from io import BytesIO
import pandas as pd

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def init_api(email, password): #remove tokenstore
    """Initialize Garmin API with your credentials."""
    try:
        garmin = Garmin(email, password)
        garmin.login()
        print("Login successful!")
    except Exception as e:
        logger.error(e)
        print(f"An error occurred during login: {e}")

    return garmin



def get_activity_files(api, start_date, end_date, output_dir="./"):
    """Downloads activity files within a date range."""
    activitytype=""
    try:
        activities = api.get_activities_by_date(
            start_date.isoformat(), end_date.isoformat(), activitytype
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

def get_activity_dataframes(api, start_date, end_date):
    """
    Retrieves activity data within a date range and returns a list of dictionaries,
    each containing the filename and its corresponding DataFrame.
    """
    activitytype = ""
    activity_data = []

    try:
        activities = api.get_activities_by_date(
            start_date.isoformat(), end_date.isoformat(), activitytype
        )

        for activity in activities:
            activity_start_time = datetime.datetime.strptime(
                activity["startTimeLocal"], "%Y-%m-%d %H:%M:%S"
            ).strftime("%d-%m-%Y")
            activity_type = activity.get('activityType', {}).get('typeKey', 'unknown')
        
            activity_id = activity["activityId"]
            csv_data = api.download_activity(
                activity_id, dl_fmt=api.ActivityDownloadFormat.CSV
            )
            filename = f"{activity_type}_{activity_start_time}_{activity_id}.csv"
            # Read CSV data into DataFrame
            df = pd.read_csv(BytesIO(csv_data))
            # Append to the list
            activity_data.append({"filename": filename, "df": df})

            print(f"Activity data for '{filename}' loaded into DataFrame.")

    except (
        GarminConnectConnectionError,
        GarminConnectAuthenticationError,
        GarminConnectTooManyRequestsError,
        requests.exceptions.HTTPError,
    ) as err:
        print(f"Error downloading activities: {err}")

    return activity_data


def main_api_call(email=None, password=None): 
    """Main function to download Garmin Connect activities."""
    print("Garmin Connect API - Activity Downloader")

    
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=60)

    if not email or not password:
        print("Email and password are required for authentication.")
        return 0, 0, 0

    api = init_api(email, password)

    if not api:
        print("Failed to initialize Garmin API. Exiting.")
        return None, None, None

    if not end_date:
        end_date = datetime.datetime.now()

    name_and_data =get_activity_dataframes(api, start_date, end_date)

    return start_date, end_date, name_and_data

if __name__ == "__main__":


    start_date ,end_date, name_and_data = main_api_call()
