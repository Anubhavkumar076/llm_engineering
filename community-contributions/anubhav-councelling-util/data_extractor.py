import os
import base64
import json
import tempfile
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd



SPREADSHEET_NAME = "CounselingDataDump"
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


def read_grok_table(sh):
    ws = sh.worksheet("Grok")
    df = pd.DataFrame(ws.get_all_records())
    return df


def read_gemini_table(sh):
    ws = sh.worksheet("Gemini")
    df = pd.DataFrame(ws.get_all_records())
    return df


def read_claude_table(sh):
    ws = sh.worksheet("Claude")
    df = pd.DataFrame(ws.get_all_records())
    return df


def read_chatgpt_table(sh):
    ws = sh.worksheet("ChatGPT")
    df = pd.DataFrame(ws.get_all_records())
    return df


def get_questionnaire_data(llm_model):
    sh = open_sheet(SPREADSHEET_NAME)
    df = None
    if (llm_model == "Grok"):
        df = read_grok_table(sh)
    elif (llm_model == "Gemini"):
        df = read_gemini_table(sh)
    elif (llm_model == "Claude"):
        df = read_claude_table(sh)
    elif (llm_model == "ChatGPT"):
        df = read_chatgpt_table(sh)

    if df is not None:
        return df
    else:
        print(f"No data found for the given LLM model {llm_model}")
        return None
