import json
import os.path

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.datasets import DATASETS
from config.google_sheets import CREDENTIALS_FILE
from config.google_sheets import SCOPES
from config.google_sheets import TOKEN_FILE
from utils.validation import validate_dataset


def authenticate(credentials_file=None, token_file=None, scopes=None):
    """
    Authenticate Google Sheets connection with token.

    Returns
    -------
      google.oauth2.credentials.Credentials
    """
    # TODO: continue to iterate on this function
    #   ref: https://stackoverflow.com/questions/66058279/token-has-been-expired-or-revoked-google-oauth2-refresh-token-gets-expired-i

    credentials_file = credentials_file or CREDENTIALS_FILE
    token_file = token_file or TOKEN_FILE
    scopes = scopes or SCOPES
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            token = json.load(f)
        if token.get("scopes") == scopes:
            creds = Credentials.from_authorized_user_file(token_file, scopes)
        else:
            print("Scope has changed (or is not defined)")

    if not creds or not creds.valid:
        # Try refreshing credentials
        re_login = False
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                if e.args[1]["error"] == "invalid_client":  # Unauthorized
                    re_login = True
                elif (
                    e.args[1]["error"] == "invalid_grant"
                ):  # Token has been expired or revoked
                    e.add_note(
                        "Add a new client secret here: "
                        "https://console.cloud.google.com/auth/clients/236291344840-vdd3f9t32k8svbv3mrfvna1vkil41vt8.apps.googleusercontent.com?project=ginnastix"
                    )
                    raise e

        else:
            re_login = True

        # If there are no (valid) credentials available, let the user log in.
        if re_login:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return creds


def get_sheets_service(credentials):
    return build("sheets", "v4", credentials=credentials)


def get_sheet(credentials):
    service = get_sheets_service(credentials)
    sheet = service.spreadsheets()
    return sheet


def read_sheet_data(sheet, spreadsheet_id, sheet_range):
    """
    Return a range of values from a spreadsheet.

    References
    ----------
    https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/get
    """
    result = (
        sheet.values().get(spreadsheetId=spreadsheet_id, range=sheet_range).execute()
    )
    return result


def read_sheet_properties(sheet, spreadsheet_id):
    """
    Return the spreadsheet properties at the given ID.

    References
    ----------
    https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/get
    https://developers.google.com/workspace/sheets/api/guides/field-masks
    """
    result = sheet.get(
        spreadsheetId=spreadsheet_id, fields="sheets.properties"
    ).execute()
    return result


def read_dataset(dataset_name, credentials=None):
    dataset_cfg = _get_dataset_config(dataset_name)
    credentials = credentials or authenticate()
    sheet = get_sheet(credentials)

    data_result = read_sheet_data(
        sheet,
        spreadsheet_id=dataset_cfg["spreadsheet_id"],
        sheet_range=dataset_cfg["sheet_range"],
    )
    df = pd.DataFrame(
        data_result["values"][dataset_cfg.get("data_index", 1) :],
        columns=data_result["values"][dataset_cfg.get("columns_index", 0)],
    )
    validate_dataset(df, dataset_cfg["schema"])
    return df


def append_dataset_rows(dataset_name, df, credentials=None):
    dataset_cfg = _get_dataset_config(dataset_name)
    df = df.fillna("")
    validate_dataset(df, dataset_cfg["schema"])
    print(f"Writing data batch to Google Sheets (n={df.shape[0]})")
    print("\n----------  data sample  ----------\n")
    print(df.head())
    print("...")

    print("\n----------  data sample  ----------\n")
    credentials = credentials or authenticate()
    sheet = get_sheet(credentials)
    result = (
        sheet.values()
        .append(
            spreadsheetId=dataset_cfg["spreadsheet_id"],
            range=dataset_cfg["sheet_range"],
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": df.values.tolist()},
        )
        .execute()
    )
    print(f"{result.get('updates').get('updatedCells')} cells updated.")


def _get_dataset_config(dataset_name):
    dataset = DATASETS.get(dataset_name)
    if not dataset:
        raise Exception(f"Dataset '{dataset_name}' not configured")
    return dataset
