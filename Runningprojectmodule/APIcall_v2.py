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


def get_credentials():
    """Get user credentials."""
    email = input("Login e-mail: ")
    password = getpass("Enter password: ")
    return email, password


def init_api(email, password): #remove tokenstore
    """Initialize Garmin API with your credentials."""
    '''
    try:
        garmin = Garmin(
            email=email, password=password, is_cn=False, return_on_mfa=True
        )
        garmin.login()

    except (GarminConnectAuthenticationError,
            GarminConnectConnectionError,
            GarminConnectTooManyRequestsError,
            requests.exceptions.HTTPError) as err:
        logger.error(err)
        return None
    '''
    try:
        garmin = Garmin(email, password)
        garmin.login()
        print("Login successful!")
        # Proceed with your data retrieval and processing here
    except Exception as e:
        print(f"An error occurred during login: {e}")
    return garmin


def get_mfa():
    """Get MFA."""
    return input("MFA one-time code: ")


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
            activity_id = activity["activityId"]
            activity_name = activity["activityName"]

            csv_data = api.download_activity(
                activity_id, dl_fmt=api.ActivityDownloadFormat.CSV
            )
            filename = f"{activity_name}_{activity_start_time}_{activity_id}.csv"
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


def main_api_call(email=None, password=None, start_date=None, end_date=None): 
    """Main function to download Garmin Connect activities."""
    print("Garmin Connect API - Activity Downloader")

    custom_start = input("Do you want to enter a custom start date? Default start date is 200 days before today (y/n): ").lower()
    if custom_start == 'y':
        while True:
            start_date_str = input("Enter start date (YYYY-MM-DD): ")
            try:
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
                break
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD.")
    else:
        end_date = datetime.date.today()


        # change the days here!


        start_date = end_date - datetime.timedelta(days=50)
    print("start date: ", start_date,'start_date type: ', type(start_date))
    print("end date: ", end_date,'end_date type: ', type(end_date))

    if not email or not password:
        email, password = get_credentials()

    api = init_api(email, password)

    if not api:
        print("Failed to initialize Garmin API. Exiting.")
        return None, None

    if not end_date:
        end_date = datetime.datetime.now()

    name_and_data =get_activity_dataframes(api, start_date, end_date)

    return start_date, end_date, name_and_data

if __name__ == "__main__":


    start_date ,end_date, name_and_data = main_api_call()
