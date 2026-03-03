import json
import os.path
from datetime import datetime

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ginnastix_class.config.datasets import DATASETS
from ginnastix_class.config.google_sheets import CREDENTIALS_FILE
from ginnastix_class.config.google_sheets import SCOPES
from ginnastix_class.config.google_sheets import TOKEN_FILE
from ginnastix_class.utils.validation import standardize
from ginnastix_class.utils.validation import validate_dataset


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
    df = standardize(df, dataset_cfg["schema"])
    validate_dataset(df, dataset_cfg["schema"])
    return df


def append_dataset_rows(dataset_name, df, credentials=None, truncate=False):
    # Validate
    dataset_cfg = _get_dataset_config(dataset_name)
    df = standardize(df, dataset_cfg["schema"])
    validate_dataset(df, dataset_cfg["schema"])

    # Convert dataframe to JSON-serializable array
    gsheet_body = _dataframe_to_gsheet_body(
        df, include_columns=True if truncate else False
    )

    # Get current state of sheet
    credentials = credentials or authenticate()
    sheet = get_sheet(credentials)

    # Truncate data
    rand_id = datetime.now().strftime("%Y%m%d%H%M%S")
    temp_sheet_name = f"_temp_{rand_id}"
    if truncate:
        print("Copying data in sheet to temporary location")
        duplicate_sheet(
            dataset_cfg["spreadsheet_id"],
            sheet_name=dataset_cfg["sheet_range"],
            new_sheet_name=temp_sheet_name,
        )
        print("Truncating sheet")
        truncate_sheet(
            dataset_cfg["spreadsheet_id"],
            sheet_name=dataset_cfg["sheet_range"],
        )

    try:
        # Write data
        print(f"Writing n={df.shape[0]} records to Google Sheets")
        result = (
            sheet.values()
            .append(
                spreadsheetId=dataset_cfg["spreadsheet_id"],
                range=dataset_cfg["sheet_range"],
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=gsheet_body,
            )
            .execute()
        )
        url = f"https://docs.google.com/spreadsheets/d/{dataset_cfg['spreadsheet_id']}"
        print(f"{result.get('updates').get('updatedCells')} cells updated in {url}")
        delete_sheet(
            dataset_cfg["spreadsheet_id"],
            sheet_name=temp_sheet_name,
        )
    except Exception:
        # Do rollback
        print(
            f"""Encountered an error when writing new data to '{dataset_cfg["sheet_range"]}'"""
        )
        print("Copying data in temporary location back to original location")
        delete_sheet(
            dataset_cfg["spreadsheet_id"],
            sheet_name=dataset_cfg["sheet_range"],
            prompt_user=False,
        )
        duplicate_sheet(
            dataset_cfg["spreadsheet_id"],
            sheet_name=temp_sheet_name,
            new_sheet_name=dataset_cfg["sheet_range"],
        )
        raise


def _get_dataset_config(dataset_name):
    dataset = DATASETS.get(dataset_name)
    if not dataset:
        raise Exception(f"Dataset '{dataset_name}' not configured")
    return dataset


def _dataframe_to_gsheet_body(df, include_columns=False):
    _df = df.copy()
    _df = _df.fillna("").astype(str)  # prevent JSON serialization error
    print("Preparing data batch for Google Sheets API")
    print("\n----------  data sample  ----------\n")
    print(_df.head())
    print("...")
    print("\n----------  data sample  ----------\n")
    values = _df.values.tolist()
    if include_columns:
        values = [list(_df.columns)] + values

    gsheet_body = {"values": values}
    try:
        json.dumps(gsheet_body)
        return gsheet_body
    except TypeError as e:
        raise ValueError(
            f"Failed to convert dataframe to JSON-serializable dictionary: {e}"
        )


def create_sheet_in_workbook(spreadsheet_id, sheet_name, credentials=None):
    credentials = credentials or authenticate()
    sheet = get_sheet(credentials)
    body = {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
    response = sheet.batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    print(
        f"Sheet '{sheet_name}' added successfully to spreadsheet ID: {spreadsheet_id}"
    )

    new_sheet_id = None
    reply = response.get("replies", [])
    if reply:
        new_sheet_id = reply[0]["addSheet"]["properties"]["sheetId"]
        print(f"New sheet ID: {new_sheet_id}")
    return new_sheet_id


def get_sheet_id(spreadsheet_id, sheet_name, sheet=None, credentials=None):
    credentials = credentials or authenticate()
    sheet = sheet or get_sheet(credentials)

    spreadsheet_metadata = sheet.get(
        spreadsheetId=spreadsheet_id, fields="sheets(properties(sheetId,title))"
    ).execute()

    sheet_id = None
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    sheets = spreadsheet_metadata.get("sheets", [])
    for _sheet in sheets:
        properties = _sheet.get("properties", {})
        if properties.get("title") == sheet_name:
            sheet_id = properties.get("sheetId")
    if not sheet_id:
        raise ValueError(f"Sheet with name '{sheet_name}' not found in {url}")

    return sheet_id


def duplicate_sheet(spreadsheet_id, sheet_name, new_sheet_name, credentials=None):
    credentials = credentials or authenticate()
    sheet = get_sheet(credentials)

    sheet_id = get_sheet_id(spreadsheet_id, sheet_name, sheet, credentials)

    body = {
        "requests": [
            {
                "duplicateSheet": {
                    "sourceSheetId": sheet_id,
                    "newSheetName": new_sheet_name,
                }
            }
        ]
    }
    response = sheet.batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    print(f"Sheet duplicated to '{new_sheet_name}' in {url}")
    print(f"New sheet ID: {sheet_id}")
    return response


def truncate_sheet(spreadsheet_id, sheet_name, credentials=None):
    credentials = credentials or authenticate()
    sheet = get_sheet(credentials)
    result = (
        sheet.values()
        .clear(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
        )
        .execute()
    )
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    print(f"Sheet '{sheet_name}' truncated in {url}")
    return result


def delete_sheet(spreadsheet_id, sheet_name, credentials=None, prompt_user=True):
    credentials = credentials or authenticate()
    sheet = get_sheet(credentials)
    sheet_id = get_sheet_id(spreadsheet_id, sheet_name, sheet, credentials)
    requests = [{"deleteSheet": {"sheetId": sheet_id}}]

    body = {"requests": requests}
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

    answer = "Y"
    if prompt_user:
        answer = input(
            f"\nAre you sure you want to delete sheet '{sheet_name}' in {url}\n\n(Y/n) >> "
        )
    if answer == "Y":
        response = sheet.batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
        print(f"Sheet '{sheet_name}' (ID={sheet_id}) deleted successfully in {url}")
        return response
