# gs_helper.py
import os
import base64
import json
import tempfile
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd


SPREADSHEET_NAME = "SalonBookings"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def auth_gs():
    # Expect env var 'GSA_JSON_B64' with base64-encoded service account JSON
    # b64 = os.environ.get("GSA_JSON_B64")

    b64 = "<Your B64 Google sheet Token here>"
    if not b64:
        raise RuntimeError("GSA_JSON_B64 environment variable not found")
    data = base64.b64decode(b64)
    # Write to temp file for google-auth
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    tf.write(data)
    tf.flush()
    tf.close()
    creds = Credentials.from_service_account_file(tf.name, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client

def open_sheet(spreadsheet_name):
    client = auth_gs()
    sh = client.open(spreadsheet_name)
    return sh

def read_occ_table(sh):
    ws = sh.worksheet("occupancy")
    df = pd.DataFrame(ws.get_all_records())
    return df

def read_appointments(sh):
    ws = sh.worksheet("appointments")
    df = pd.DataFrame(ws.get_all_records())
    return df

def list_my_appointments(phone):
    phone = str(phone).strip()

    sh = open_sheet(SPREADSHEET_NAME)
    df = read_appointments(sh)

    if df.empty:
        return "No appointments found"

    # Normalize phone column
    df["phone"] = (
        df["phone"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )

    # If blank phone → show all
    if phone == "":
        return df.to_string(index=False)

    # Filter exact phone
    matches = df[df["phone"] == phone]

    if matches.empty:
        return f"No appointments found for {phone}"

    return matches.to_string(index=False)

def append_appointment(sh, appointment_dict):
    ws = sh.worksheet("appointments")
    row = [
        appointment_dict.get("id"),
        appointment_dict.get("date"),
        appointment_dict.get("slot_label"),
        appointment_dict.get("salon_name",""),
        appointment_dict.get("location",""),
        appointment_dict.get("name",""),
        appointment_dict.get("phone",""),
        appointment_dict.get("service",""),
        appointment_dict.get("created_at","")
    ]
    ws.append_row(row, value_input_option='USER_ENTERED')

def find_occ_row(sh, date, slot_label, salon_name=""):
    ws = sh.worksheet("occupancy")
    vals = ws.get_all_values()  # includes header
    header = vals[0]
    # find column indexes
    # header: date, slot_label, capacity, occupied, services, salon_name, location
    for i, r in enumerate(vals[1:], start=2):  # 1-indexed rows; header row is 1
        row_date = r[0]
        row_slot = r[1]
        row_salon = r[5] if len(r) > 5 else ""
        if row_date == date and row_slot == slot_label and (not salon_name or row_salon == salon_name):
            return i  # the row number in sheet
    return None

def get_occ_values(sh, row_number):
    ws = sh.worksheet("occupancy")
    # read the row
    return ws.row_values(row_number)

def update_occupied(sh, row_number, new_value):
    ws = sh.worksheet("occupancy")
    # occupied is column D (4)
    ws.update_cell(row_number, 4, new_value)
