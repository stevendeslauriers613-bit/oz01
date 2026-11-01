import base64
import io
import json
import logging
import os
import sqlite3
import dropbox
import streamlit as st
import streamlit.components.v1 as components

# --- DROPBOX SETUP & AUTO-SYNC ---
DROPBOX_CREDENTIALS_FILE = "dropbox_credentials.json"
DROPBOX_FOLDER_PATH = "/OZ_Store_Uploads"

def get_dropbox_client():
    """Initializes and returns an authenticated Dropbox client using refresh tokens."""
    try:
        if not os.path.exists(DROPBOX_CREDENTIALS_FILE):
            return None
        with open(DROPBOX_CREDENTIALS_FILE, "r") as f:
            creds = json.load(f)
        
        app_key = creds.get("app_key")
        app_secret = creds.get("app_secret")
        refresh_token = creds.get("refresh_token")
        
        if app_key and refresh_token:
            return dropbox.Dropbox(
                app_key=app_key,
                app_secret=app_secret,
                oauth2_refresh_token=refresh_token
            )
    except Exception as e:
        print("Dropbox auth error:", e)
    return None

def sync_from_dropbox_on_startup():
    """Automatically downloads and restores master store state from Dropbox on app boot."""
    try:
        dbx = get_dropbox_client()
        if not dbx:
            return
        
        _, res = dbx.files_download(f"{DROPBOX_FOLDER_PATH}/master_store_state.json")
        state_data = json.loads(res.content.decode('utf-8'))
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        for spk, val in state_data.items():
            cursor.execute(
                """
                INSERT OR REPLACE INTO store_data 
                (store_period_key, cooh_text, prev_cooh, brinks_total, chargebacks_text, checklist_json, inventory_json, inventory_filename) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    spk,
                    val.get("cooh_text", ""),
                    val.get("prev_cooh", ""),
                    val.get("brinks_total", ""),
                    val.get("chargebacks_text", "Nothing to report."),
                    json.dumps(val.get("checklist_json", {})),
                    json.dumps(val.get("inventory_data")) if val.get("inventory_data") else None,
                    val.get("inventory_filename", "")
                )
            )
        conn.commit()
        conn.close()
    except Exception as e:
        print("Startup sync skipped:", e)
