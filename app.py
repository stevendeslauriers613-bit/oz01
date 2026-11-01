import base64
import io
import json
import logging
import os
import sqlite3
import uuid
import zlib
import zipfile
from datetime import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Suppress deprecation warning for components.html
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)

# --- DROPBOX SETUP ---
DROPBOX_CREDENTIALS_FILE = "dropbox_credentials.json"
DROPBOX_FOLDER_PATH = "/OZ_Store_Uploads"


def get_dropbox_client():
    """Get authenticated Dropbox client."""
    try:
        import dropbox
        if not os.path.exists(DROPBOX_CREDENTIALS_FILE):
            return None
        with open(DROPBOX_CREDENTIALS_FILE, "r") as f:
            creds = json.load(f)
        access_token = creds.get("access_token")
        if not access_token:
            return None
        return dropbox.Dropbox(access_token)
    except Exception as e:
        return None


def ensure_dropbox_folder(dbx):
    try:
        dbx.files_get_metadata(DROPBOX_FOLDER_PATH)
    except Exception:
        dbx.files_create_folder_v2(DROPBOX_FOLDER_PATH)


def upload_to_dropbox(dbx, filename, file_data):
    dropbox_path = f"{DROPBOX_FOLDER_PATH}/{filename}"
    dbx.files_upload(file_data, dropbox_path, mode=dropbox.files.WriteMode.overwrite)
    return f"dropbox://{dropbox_path}"


# Set page configuration
st.set_page_config(
    page_title="The OZ Store - Persistent Accountant Package Manager",
    page_icon="🌿",
    layout="wide",
)

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container { padding: 0rem; }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = "oz_store.db"
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, name TEXT, role TEXT, password TEXT)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS store_data (store_period_key TEXT PRIMARY KEY, store TEXT, period TEXT, cooh_text TEXT, cooh_date TEXT, chargebacks_text TEXT, checklist_json TEXT, inventory_json TEXT, inventory_filename TEXT)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS store_files (id INTEGER PRIMARY KEY AUTOINCREMENT, store_period_key TEXT, category TEXT, filename TEXT, filepath TEXT)"
    )

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        default_users = [
            ("admin", "Master Admin", "admin", "admin2026"),
            ("leanne", "Leanne (Accountant)", "accountant", "leanne2026"),
            ("oz1", "Oz 1", "store", "oz1pass2026"),
            ("oz2", "Oz 2", "store", "oz2pass2026"),
            ("oz3", "Oz 3", "store", "oz3pass2026"),
            ("oz4", "Oz 4", "store", "oz4pass2026"),
            ("oz5", "Oz 5", "store", "oz5pass2026"),
            ("oz6", "Oz 6", "store", "oz6pass2026"),
            ("oz7", "Oz 7", "store", "oz7pass2026"),
        ]
        cursor.executemany(
            "INSERT INTO users VALUES (?, ?, ?, ?)", default_users
        )
        conn.commit()
    conn.close()


init_db()

# --- HANDLE QUERY PARAMETER ACTIONS ---
query_params = st.query_params

if "action" in query_params:
    action = query_params["action"]
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if action == "update_user":
        orig_user = query_params.get("orig_username", "").lower().strip()
        new_user = query_params.get("username", "").lower().strip()
        name = query_params.get("name", "")
        role = query_params.get("role", "")
        password = query_params.get("password", "")

        if orig_user and orig_user != new_user:
            cursor.execute("DELETE FROM users WHERE username = ?", (orig_user,))
        cursor.execute(
            "INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)",
            (new_user, name, role, password),
        )
        conn.commit()

    elif action == "delete_user":
        username = query_params.get("username", "").lower().strip()
        if username:
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()

    elif action == "delete_file":
        file_id = query_params.get("file_id")
        if file_id:
            cursor.execute("SELECT filepath FROM store_files WHERE id = ?", (file_id,))
            f_row = cursor.fetchone()
            if f_row:
                filepath = f_row[0]
                if filepath.startswith("dropbox://"):
                    dbx = get_dropbox_client()
                    if dbx:
                        try:
                            dbx.files_delete_v2(filepath.replace("dropbox://", ""))
                        except Exception:
                            pass
                elif os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass
            cursor.execute("DELETE FROM store_files WHERE id = ?", (file_id,))
            conn.commit()

    elif action == "sign_out":
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.name = None
        st.session_state.role = None
        conn.close()
        st.query_params.clear()
        st.rerun()

    elif action == "download_file":
        file_id = query_params.get("file_id")
        if file_id:
            cursor.execute("SELECT filename, filepath FROM store_files WHERE id = ?", (file_id,))
            f_row = cursor.fetchone()
            if f_row:
                import mimetypes

                filename = f_row[0]
                filepath = f_row[1]
                mime_type, _ = mimetypes.guess_type(filename)
                if mime_type is None:
                    mime_type = "application/octet-stream"

                if filepath.startswith("dropbox://"):
                    dbx = get_dropbox_client()
                    if dbx:
                        try:
                            _, res = dbx.files_download(filepath.replace("dropbox://", ""))
                            st.download_button(label=f"Download {filename}", data=res.content, file_name=filename,
                                               mime=mime_type, key=f"dl_{file_id}")
                            st.stop()
                        except Exception:
                            pass
                elif os.path.exists(filepath):
                    with open(filepath, "rb") as f:
                        file_bytes = f.read()
                    st.download_button(label=f"Download {filename}", data=file_bytes, file_name=filename,
                                       mime=mime_type, key=f"dl_{file_id}")
                    st.stop()

    conn.close()
    st.query_params.clear()
    st.rerun()

# --- AUTHENTICATION STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.name = None
    st.session_state.role = None


def get_user(username):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, role, password FROM users WHERE username = ?",
        (username.lower().strip(),),
    )
    res = cursor.fetchone()
    conn.close()
    return res


# --- LOGIN SCREEN ---
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="background-color: #065f46; padding: 30px; border-radius: 16px; color: white; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
                <div style="font-size: 40px; margin-bottom: 10px;">🌿</div>
                <h2 style="margin: 0; font-size: 22px;">The OZ Store Portal</h2>
                <p style="font-size: 12px; color: #a7f3d0; margin-top: 5px;">Secure Persistent Database Manager</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            username_input = st.text_input("Username")
            password_input = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In", use_container_width=True)

            if submit:
                user_record = get_user(username_input)
                if user_record and user_record[2] == password_input:
                    st.session_state.logged_in = True
                    st.session_state.username = username_input.lower().strip()
                    st.session_state.name = user_record[0]
                    st.session_state.role = user_record[1]
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
    st.stop()

# --- FETCH USERS, FILES & STORE DATA FOR JAVASCRIPT INJECTION ---
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("SELECT username, name, role, password FROM users")
db_users = cursor.fetchall()

users_dict = {}
for u, n, r, p in db_users:
    users_dict[u] = {"name": n, "role": r, "pass": p}

# Fetch files
cursor.execute("SELECT id, store_period_key, category, filename FROM store_files")
db_files = cursor.fetchall()

files_json = "{}"
if db_files:
    fj = {}
    for fid, spk, cat, fname in db_files:
        if spk not in fj:
            fj[spk] = {}
        if cat not in fj[spk]:
            fj[spk][cat] = []
        fj[spk][cat].append({"id": fid, "filename": fname})
    files_json = json.dumps(fj)

# Fetch store data (checklist & inventory)
cursor.execute(
    "SELECT store_period_key, cooh_text, cooh_date, chargebacks_text, checklist_json, inventory_json, inventory_filename FROM store_data")
db_store_data = cursor.fetchall()
store_data_json = "{}"
if db_store_data:
    sdj = {}
    for spk, cooh_t, cooh_d, cb_t, chk_j, inv_j, inv_fname in db_store_data:
        sdj[spk] = {
            "cooh_text": cooh_t or "",
            "cooh_date": cooh_d or "",
            "chargebacks_text": cb_t or "Nothing to report.",
            "checklist_json": json.loads(chk_j) if chk_j else {},
            "inventory_data": json.loads(inv_j) if inv_j else None,
            "inventory_filename": inv_fname or ""
        }
    store_data_json = json.dumps(sdj)

conn.close()

current_role = st.session_state.role
current_name = st.session_state.name
is_store_manager = "true" if current_role == "store" else "false"
is_admin = "true" if current_role == "admin" else "false"

cred_table_rows = ""
for u, d in users_dict.items():
    actions_html = (
        f"""
        <button onclick="editUser('{u}', '{d['name']}', '{d['role']}', '{d['pass']}')" class="text-emerald-700 font-bold underline mr-2">Edit</button>
        <button onclick="deleteUser('{u}')" class="text-red-600 font-bold underline">Delete</button>
        """
        if current_role == "admin"
        else ""
    )
    cred_table_rows += f"""
        <tr>
            <td class="p-3 font-mono font-medium text-emerald-800">{u}</td>
            <td class="p-3">{d["name"]}</td>
            <td class="p-3 uppercase text-[10px] font-bold"><span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded">{d["role"]}</span></td>
            <td class="p-3 font-mono">{d["pass"]}</td>
            <td class="p-3 text-right">{actions_html}</td>
        </tr>
    """

admin_hidden_class = "" if current_role == "admin" else "hidden"
accountant_hidden_class = "hidden" if current_role == "accountant" else ""
add_user_btn_html = (
    '<button onclick="openAddUserModal()" class="bg-emerald-700 hover:bg-emerald-800 text-white px-3.5 py-1.5 rounded-xl text-xs font-bold transition shadow-xs">+ Add New User</button>'
    if current_role == "admin"
    else ""
)

# --- FULL HTML UI WITH EMBEDDED PERSISTENCE & AUTO-SUMMING FINANCIAL CALCULATOR ---
html_code = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The OZ Store - Executive Financial Report & Package Manager</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.4.1/papaparse.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/FileSaver.js/2.0.5/FileSaver.min.js"></script>
</head>
<body class="bg-zinc-100 text-zinc-900 min-h-screen flex flex-col items-center py-8 px-4 font-sans">

    <div class="max-w-7xl w-full bg-white rounded-2xl shadow-xl overflow-hidden border border-zinc-200">

        <header class="bg-emerald-800 text-white p-6 md:p-8 flex flex-col md:flex-row justify-between items-center gap-4 border-b border-emerald-900">
            <div class="flex items-center gap-4">
                <div class="bg-white p-2.5 rounded-xl shadow-md flex items-center justify-center">
                    <span class="text-2xl">🌿</span>
                </div>
                <div>
                    <h1 class="text-xl md:text-2xl font-extrabold text-white tracking-tight">The OZ Store</h1>
                    <p class="text-emerald-100/80 text-xs mt-0.5">Executive Financial & Accountant Document Package Manager</p>
                </div>
            </div>

            <div class="flex items-center gap-4">
                <div class="flex items-center gap-3 bg-white text-zinc-900 px-4 py-2 rounded-xl shadow-md border border-emerald-700">
                    <span class="text-xs font-bold text-emerald-800 uppercase tracking-wider">Period:</span>
                    <select id="select-month" onchange="updatePeriod()" class="bg-zinc-50 text-zinc-900 text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-zinc-300 focus:outline-none focus:border-emerald-600">
                        <option value="January">January</option>
                        <option value="February">February</option>
                        <option value="March">March</option>
                        <option value="April">April</option>
                        <option value="May">May</option>
                        <option value="June">June</option>
                        <option value="July">July</option>
                        <option value="August">August</option>
                        <option value="September">September</option>
                        <option value="October" selected>October</option>
                        <option value="November">November</option>
                        <option value="December">December</option>
                    </select>
                    <select id="select-year" onchange="updatePeriod()" class="bg-zinc-50 text-zinc-900 text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-zinc-300 focus:outline-none focus:border-emerald-600">
                        <option value="2025">2025</option>
                        <option value="2026" selected>2026</option>
                        <option value="2027">2027</option>
                        <option value="2028">2028</option>
                    </select>
                </div>
                <button onclick="window.location.href='?action=sign_out'" class="bg-emerald-900 hover:bg-emerald-950 text-emerald-100 px-3.5 py-2 rounded-xl text-xs font-semibold border border-emerald-700 transition">
                    Sign Out (REPLACE_CURRENT_NAME)
                </button>
            </div>
        </header>

        <div class="p-6 md:p-8">

            <div class="flex flex-col md:flex-row justify-between items-center mb-6 gap-4 pb-4 border-b border-zinc-200">
                <div class="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin w-full md:w-auto" id="store-tabs"></div>
                <div class="flex items-center gap-3">
                    REPLACE_ADD_USER_BTN_HTML
                    <div class="text-xs text-zinc-500 font-medium bg-zinc-50 px-3 py-1.5 rounded-lg border border-zinc-200">
                        👤 Logged in as: <span class="font-bold text-emerald-800">REPLACE_CURRENT_NAME</span>
                    </div>
                </div>
            </div>

            <!-- COLLAPSIBLE CREDENTIAL MANAGER (ADMIN ONLY) -->
            <details id="credential-manager-view" class="REPLACE_ADMIN_HIDDEN_CLASS mb-8 bg-zinc-50 rounded-2xl border border-zinc-300 shadow-xs overflow-hidden">
                <summary class="p-4 bg-emerald-50 hover:bg-emerald-100 cursor-pointer font-bold text-emerald-900 text-xs flex items-center justify-between transition">
                    <span class="flex items-center gap-2"><span>🔐</span> Employee & Store Login Credentials Directory (Click to Edit)</span>
                    <span class="text-[11px] text-emerald-700 underline font-normal">Expand / Collapse</span>
                </summary>
                <div class="p-5 border-t border-zinc-200 bg-white space-y-4">
                    <div class="bg-white rounded-xl border border-zinc-200 overflow-hidden shadow-xs">
                        <table class="w-full text-left border-collapse text-xs">
                            <thead class="bg-emerald-50 text-emerald-900 border-b border-emerald-200">
                                <tr>
                                    <th class="p-3 font-semibold">Username</th>
                                    <th class="p-3 font-semibold">Display Name</th>
                                    <th class="p-3 font-semibold">Role</th>
                                    <th class="p-3 font-semibold">Password</th>
                                    <th class="p-3 font-semibold text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-zinc-100 text-zinc-700">
                                REPLACE_CRED_TABLE_ROWS
                            </tbody>
                        </table>
                    </div>

                    <div id="user-edit-form-box" class="hidden bg-emerald-50/60 p-4 rounded-xl border border-emerald-300 mt-4">
                        <h4 class="font-bold text-emerald-900 text-xs mb-3" id="edit-form-title">Edit User Credential</h4>
                        <form onsubmit="submitUserEdit(event)" class="grid grid-cols-1 md:grid-cols-5 gap-3 text-xs">
                            <input type="hidden" id="edit-orig-username">
                            <div>
                                <label class="block font-semibold mb-1 text-zinc-700">Username</label>
                                <input type="text" id="edit-username" required class="w-full border border-zinc-300 rounded px-2 py-1.5 bg-white">
                            </div>
                            <div>
                                <label class="block font-semibold mb-1 text-zinc-700">Display Name</label>
                                <input type="text" id="edit-name" required class="w-full border border-zinc-300 rounded px-2 py-1.5 bg-white">
                            </div>
                            <div>
                                <label class="block font-semibold mb-1 text-zinc-700">Role</label>
                                <select id="edit-role" class="w-full border border-zinc-300 rounded px-2 py-1.5 bg-white">
                                    <option value="store">Store</option>
                                    <option value="accountant">Accountant</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                            <div>
                                <label class="block font-semibold mb-1 text-zinc-700">Password</label>
                                <input type="text" id="edit-password" required class="w-full border border-zinc-300 rounded px-2 py-1.5 bg-white">
                            </div>
                            <div class="flex items-end gap-2">
                                <button type="submit" class="bg-emerald-700 hover:bg-emerald-800 text-white font-bold px-3 py-1.5 rounded transition w-full">Save</button>
                                <button type="button" onclick="document.getElementById('user-edit-form-box').classList.add('hidden')" class="bg-zinc-200 text-zinc-700 px-3 py-1.5 rounded transition">Cancel</button>
                            </div>
                        </form>
                    </div>
                </div>
            </details>

            <div class="flex justify-between items-center mb-6 bg-emerald-50/60 p-4 rounded-xl border border-emerald-200 shadow-xs">
                <div>
                    <span class="text-xs uppercase tracking-wider text-emerald-800 font-bold block mb-0.5">Active Workspace</span>
                    <h2 class="text-xl font-extrabold text-zinc-900" id="workspace-store-name">Oz 1</h2>
                </div>
                <div class="flex items-center gap-3 text-xs text-zinc-600">
                    <button type="button" onclick="saveAllData()" class="bg-emerald-700 hover:bg-emerald-800 text-white px-4 py-1.5 rounded-full font-semibold shadow-xs border border-emerald-600 transition cursor-pointer">
                        💾 Save All
                    </button>
                    <span id="active-period-label" class="bg-white text-emerald-800 border border-emerald-300 px-3 py-1 rounded-full font-semibold shadow-xs">October 2026</span>
                    <span id="store-completion-badge" class="bg-amber-50 text-amber-800 border border-amber-300 px-3 py-1 rounded-full font-semibold shadow-xs">Checklist: 0/10 Completed</span>
                </div>
            </div>

            <!-- SIDE-BY-SIDE SECTIONS -->
            <div class="grid grid-cols-1 xl:grid-cols-12 gap-6 mb-8 REPLACE_ACCOUNTANT_HIDDEN_CLASS">

                <!-- LEFT SIDE: Inventory Report Formatter -->
                <div class="xl:col-span-5 bg-zinc-50 rounded-xl p-5 border border-zinc-200 flex flex-col justify-between shadow-xs">
                    <div>
                        <div class="flex justify-between items-center mb-3">
                            <h3 class="text-base font-bold text-emerald-800 flex items-center gap-2">Inventory Report Formatter</h3>
                            <span id="inv-status-badge" class="text-[11px] text-zinc-600 bg-white border border-zinc-300 px-2 py-0.5 rounded shadow-xs">Not Loaded</span>
                        </div>
                        <p class="text-zinc-600 text-xs mb-4">Upload raw monthly CSV. Rows are sorted with a blank space after row 14 (Vapes - Pods), styled with a green header, and pushed to Greenline Inventory Summary.</p>

                        <div id="drop-zone" class="border-2 border-dashed border-emerald-400 hover:border-emerald-700 rounded-xl p-5 text-center cursor-pointer transition-all bg-white group mb-4 shadow-xs">
                            <input type="file" id="file-input" accept=".csv" class="hidden">
                            <svg class="w-8 h-8 mx-auto text-emerald-700 mb-2 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                            </svg>
                            <p class="text-xs font-medium text-zinc-700">Drag & drop store CSV here</p>
                            <p class="text-[11px] text-emerald-700 underline mt-0.5">or click to browse</p>
                        </div>
                        <div id="csv-file-info" class="hidden mb-4 bg-emerald-50 border border-emerald-200 rounded-xl p-3 flex items-center justify-between">
                            <div class="flex items-center gap-2">
                                <span class="text-emerald-700">📄</span>
                                <span id="csv-file-name" class="text-xs font-medium text-emerald-800"></span>
                            </div>
                            <button type="button" onclick="clearCSVUpload()" class="bg-red-100 hover:bg-red-200 text-red-700 text-xs font-bold px-3 py-1.5 rounded-lg border border-red-300 transition">
                                🗑️ Delete & Re-upload
                            </button>
                        </div>

                        <div class="bg-white rounded-lg border border-zinc-200 overflow-hidden max-h-56 overflow-y-auto mb-4 shadow-xs">
                            <table class="w-full text-left border-collapse text-[11px]">
                                <thead class="bg-emerald-800 text-white sticky top-0 z-10 border-b border-emerald-900">
                                    <tr id="table-header"><th class="p-2 font-semibold">Category</th><th class="p-2 font-semibold">Opening</th><th class="p-2 font-semibold">Sold</th><th class="p-2 font-semibold">Closing</th></tr>
                                </thead>
                                <tbody id="table-body" class="divide-y divide-zinc-100 text-zinc-700"><tr><td colspan="4" class="p-4 text-center text-zinc-400">No report uploaded yet.</td></tr></tbody>
                            </table>
                        </div>
                    </div>

                    <div id="action-area" class="hidden">
                        <button id="download-excel-btn" class="w-full bg-emerald-700 hover:bg-emerald-800 text-white font-bold py-2.5 px-4 rounded-xl shadow-md transition-all flex items-center justify-center gap-2 text-xs">
                            Download Formatted Excel (.xlsx)
                        </button>
                    </div>
                </div>

                <!-- RIGHT SIDE: Monthly Accountant Document Checklist -->
                <div class="xl:col-span-7 bg-zinc-50 rounded-xl p-5 border border-zinc-200 flex flex-col justify-between shadow-xs">
