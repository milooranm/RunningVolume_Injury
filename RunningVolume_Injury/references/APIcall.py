import datetime
from datetime import timezone
import logging
import os
import sys
import csv
from getpass import getpass

import readchar
import requests
from garth.exc import GarthHTTPError

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

# Configure debug logging
# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables if defined
email = os.getenv("EMAIL")
password = os.getenv("PASSWORD")
tokenstore = os.getenv("GARMINTOKENS") or "~/.garminconnect"
tokenstore_base64 = os.getenv("GARMINTOKENS_BASE64") or "~/.garminconnect_base64"
#api = None

# Example selections and settings

# Let's say we want to scrape all activities using switch menu_option "p". We change the values of the below variables, IE startdate days, limit,...
# today = datetime.date.today()
today = datetime.datetime.strptime('2024-09-15', '%Y-%m-%d').date()
startdate = today - datetime.timedelta(days=200)  # 
start = 0
#limit = 100
activitytype = ""

def get_credentials():
    """Get user credentials."""
    email = input("Login e-mail: ")
    password = getpass("Enter password: ")
    return email, password


def init_api(email, password):
    """Initialize Garmin API with your credentials."""
    try:
        # Using Oauth1 and OAuth2 token files from directory
        print(
            f"Trying to login to Garmin Connect using token data from directory '{tokenstore}'...\n"
        )
        garmin = Garmin()
        garmin.login(tokenstore)

    except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError):
        # Session is expired. You'll need to log in again
        print(
            "Login tokens not present, login with your Garmin Connect credentials to generate them.\n"
            f"They will be stored in '{tokenstore}' for future use.\n"
        )
        try:
            # Ask for credentials if not set as environment variables
            if not email or not password:
                email, password = get_credentials()

            garmin = Garmin(
                email=email, password=password, is_cn=False, return_on_mfa=True
            )
            result1, result2 = garmin.login()
            if result1 == "needs_mfa":  # MFA is required
                mfa_code = get_mfa()
                garmin.resume_login(result2, mfa_code)

            # Save Oauth1 and Oauth2 token files to directory for next login
            garmin.garth.dump(tokenstore)
            print(
                f"Oauth tokens stored in '{tokenstore}' directory for future use. (first method)\n"
            )

            # Encode Oauth1 and Oauth2 tokens to base64 string and safe to file for next login (alternative way)
            token_base64 = garmin.garth.dumps()
            dir_path = os.path.expanduser(tokenstore_base64)
            with open(dir_path, "w") as token_file:
                token_file.write(token_base64)
            print(
                f"Oauth tokens encoded as base64 string and saved to '{dir_path}' file for future use. (second method)\n"
            )

            # Re-login Garmin API with tokens
            garmin.login(tokenstore)
        except (
            FileNotFoundError,
            GarthHTTPError,
            GarminConnectAuthenticationError,
            requests.exceptions.HTTPError,
        ) as err:
            logger.error(err)
            return None

    return garmin


def get_mfa():
    """Get MFA."""
    return input("MFA one-time code: ")

def get_activity_files(api):
    """Downloads activity files within a date range."""
    try:
        activities = api.get_activities_by_date(
            startdate.isoformat(), today.isoformat(), activitytype
        )

        # Download activities
        for activity in activities:
            activity_start_time = datetime.datetime.strptime(
                activity["startTimeLocal"], "%Y-%m-%d %H:%M:%S"
            ).strftime(
                "%d-%m-%Y"
            )  # Format as DD-MM-YYYY, for creating unique activity names for scraping
            activity_id = activity["activityId"]
            activity_name = activity["activityName"]

            csv_data = api.download_activity(
                activity_id, dl_fmt=api.ActivityDownloadFormat.CSV
            )
            output_file = f"./{str(activity_name)}_{str(activity_start_time)}_{str(activity_id)}.csv"
            with open(output_file, "wb") as fb:
                fb.write(csv_data)
    except (
                GarminConnectConnectionError,
                GarminConnectAuthenticationError,
                GarminConnectTooManyRequestsError,
                requests.exceptions.HTTPError,
                GarthHTTPError,
    ) as err:
        logger.error(err)
        print("Error downloading activities. Exiting.")

    # Remove stored login tokens for Garmin Connect portal
    tokendir = os.path.expanduser(tokenstore)
    print(f"Removing stored login tokens from: {tokendir}")
    try:
        for root, dirs, files in os.walk(tokendir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        print(f"Directory {tokendir} removed")
    except FileNotFoundError:
        print(f"Directory not found: {tokendir}")
    api = None
    

def main():
    """Main function."""
    print('Garmin Connect API - Activity Downloader')
    
    # gloabal api

    api = init_api(email, password)     
    get_activity_files(api)
    

main()