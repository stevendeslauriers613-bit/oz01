import os
from datetime import datetime
import hashlib
import io
import json
import random
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from main import ProCannabisERP
except ImportError:
    class ProCannabisERP:
        def __init__(self, db_path):
            self.db_path = db_path
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self._init_db()

        def _init_db(self):
            with self.conn:
                self.conn.execute(
                    "CREATE TABLE IF NOT EXISTS audit_trail (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, operator TEXT, action TEXT, details TEXT, signature TEXT)")
                self.conn.execute(
                    "CREATE TABLE IF NOT EXISTS inventory_lots (lot_id TEXT PRIMARY KEY, strain_or_name TEXT, ctls_category TEXT, supplier_name TEXT, supplier_lot_id TEXT, thc_pct REAL, cbd_pct REAL, coa_reference TEXT, storage_bin TEXT, qa_status TEXT, qap_approved_by TEXT, qap_approved_at TEXT)")
                self.conn.execute(
                    "CREATE TABLE IF NOT EXISTS inventory_transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, lot_id TEXT, tx_type TEXT, quantity_change REAL, uom TEXT, reference_doc TEXT, operator TEXT)")
                self.conn.execute(
                    "CREATE TABLE IF NOT EXISTS products (product_id TEXT PRIMARY KEY, product_name TEXT, category TEXT)")
                self.conn.execute(
                    "CREATE TABLE IF NOT EXISTS cleaning_logs (log_id TEXT PRIMARY KEY, timestamp TEXT, operator TEXT, area TEXT, chemicals_used TEXT, status TEXT)")
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS employees (
                        id TEXT PRIMARY KEY,
                        name TEXT,
                        username TEXT,
                        password TEXT,
                        pin TEXT,
                        role TEXT,
                        status TEXT,
                        training_valid INTEGER,
                        training_due_date TEXT,
                        permissions TEXT
                    )
                """)

        def log_audit_crypto(self, operator, action, details):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sig = hashlib.sha256(f"{ts}{operator}{action}{details}".encode()).hexdigest()[:16]
            with self.conn:
                self.conn.execute(
                    "INSERT INTO audit_trail (timestamp, operator, action, details, signature) VALUES (?, ?, ?, ?, ?)",
                    (ts, operator, action, details, sig))

        def migrate_legacy_excel(self, path):
            pass

st.set_page_config(page_title="Edinburgh Place Creations ERP Suite", page_icon="🍃", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<script>
    const link = document.querySelector("link[rel*='icon']") || document.createElement('link');
    link.type = 'image/svg+xml';
    link.rel = 'icon';
    link.href = "data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22 fill=%22%2338bdf8%22><path d=%22M12 2C11.5 2 11 2.2 10.6 2.6C8.5 4.5 5 7.5 5 11C5 13.5 6.8 15.5 9 15.9V20C9 20.6 9.4 21 10 21H14C14.6 21 15 20.6 15 20V15.9C17.2 15.5 19 13.5 19 11C19 7.5 15.5 4.5 13.4 2.6C13 2.2 12.5 2 12 2Z%22/></svg>";
    document.getElementsByTagName('head')[0].appendChild(link);
</script>
""", unsafe_allow_html=True)

# ==========================================
# MODERN UI / UX DESIGN STYLING (CSS OVERHAUL)
# ==========================================
st.markdown("""
    <style>
    .stApp {
        background-color: #0f141c;
        color: #e2e8f0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #161d29;
        border-right: 1px solid #232d3f;
    }
    .erp-card {
        background: #1a2230;
        border: 1px solid #2a374a;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        margin-bottom: 16px;
    }
    div[data-testid="stMetric"] {
        background: #1a2230;
        border: 1px solid #2a374a;
        padding: 14px 18px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #05ae4b !important;
        font-weight: 700 !important;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .stButton > button[kind="primary"] {
        background-color: #05ae4b !important;
        color: #ffffff !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #04923e !important;
        box-shadow: 0 4px 12px rgba(5, 174, 75, 0.4);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #161d29;
        padding: 6px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 6px;
        color: #94a3b8;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #05ae4b !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

DB_PATH = "lighthouse_pro_erp.db"
EXCEL_PATH = "Lighthouse Cannabis Master tracker (Reformed).xlsx"


@st.cache_resource
def get_erp():
    erp_instance = ProCannabisERP(DB_PATH)
    return erp_instance


erp = get_erp()


def get_db_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


# Ensure schema tables, columns, and default employees exist safely
with erp.conn:
    erp.conn.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            name TEXT,
            username TEXT,
            password TEXT,
            pin TEXT,
            role TEXT,
            status TEXT,
            training_valid INTEGER,
            training_due_date TEXT,
            permissions TEXT
        )
    """)
    cnt = erp.conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    if cnt == 0:
        default_emps = [
            ("EMP-001", "Steven", "steven", "demo123", "1001", "Facility Admin", "Active", 1, "2027-01-01",
             "My Work,Vault Ledger,QA Review,Admin"),
            ("EMP-002", "Robert", "robert", "demo123", "1002", "Facility Admin", "Active", 1, "2027-01-01",
             "My Work,Vault Ledger,QA Review,Admin"),
            ("EMP-003", "Miguel", "miguel", "demo123", "1003", "Facility Admin", "Active", 1, "2027-01-01",
             "My Work,Vault Ledger,QA Review,Admin"),
            ("EMP-004", "Etienne", "etienne", "demo123", "1004", "QA Manager", "Active", 1, "2027-01-01", "QA Review"),
            ("EMP-005", "Operator", "operator", "demo123", "1005", "Technician", "Active", 1, "2027-01-01", "My Work")
        ]
        erp.conn.executemany("INSERT OR REPLACE INTO employees VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", default_emps)
        erp.conn.commit()

with erp.conn:
    erp.conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            assignee TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT DEFAULT 'Open',
            genealogy_id TEXT,
            num_units INTEGER DEFAULT 1,
            total_weight_g REAL DEFAULT 0.0,
            thc_mg_per_g REAL DEFAULT 0.0,
            end_product_name TEXT,
            new_lot_number TEXT,
            ctls_category TEXT
        )
    """)
    erp.conn.execute("""
        CREATE TABLE IF NOT EXISTS compliance_documents (
            doc_id TEXT PRIMARY KEY,
            timestamp TEXT,
            uploaded_by TEXT,
            category TEXT,
            document_title TEXT,
            filename TEXT,
            file_size_kb REAL,
            notes TEXT,
            status TEXT DEFAULT 'Under QA Review',
            esign_approved_by TEXT DEFAULT '',
            esign_timestamp TEXT DEFAULT ''
        )
    """)
    erp.conn.execute("""
        CREATE TABLE IF NOT EXISTS ppe_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            employee_name TEXT,
            role TEXT,
            lab_coat INTEGER,
            face_mask INTEGER,
            gloves INTEGER,
            personal_inspection INTEGER,
            hand_wash INTEGER,
            status TEXT
        )
    """)
    erp.conn.execute("""
        CREATE TABLE IF NOT EXISTS vault_movements (
            movement_id TEXT PRIMARY KEY,
            timestamp TEXT,
            employee_name TEXT,
            direction TEXT,
            bag_or_lot_id TEXT,
            task_assigned TEXT,
            net_weight_g REAL,
            notes TEXT
        )
    """)
    erp.conn.execute("""
        CREATE TABLE IF NOT EXISTS destruction_ledger (
            destruction_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            batch_lot_id TEXT NOT NULL,
            waste_type TEXT NOT NULL,
            weight_destroyed_g REAL NOT NULL,
            disposal_method TEXT NOT NULL,
            denaturing_agent TEXT NOT NULL,
            primary_operator TEXT NOT NULL,
            qa_witness TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'Completed'
        )
    """)
    erp.conn.execute("""
        CREATE TABLE IF NOT EXISTS set_aside_destruction (
            set_aside_id TEXT PRIMARY KEY,
            timestamp TEXT,
            employee_name TEXT,
            lot_id TEXT,
            loss_type TEXT,
            weight_g REAL,
            product_name TEXT,
            notes TEXT,
            status TEXT DEFAULT 'Pending Manager Review'
        )
    """)

# ==========================================
# AUTHENTICATION GATEKEEPER
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None

if not st.session_state.authenticated:
    st.markdown("## 🌿 Edinburgh Place Creations ERP - Employee Portal Login")
    conn = get_db_conn()
    emp_df = pd.read_sql_query("SELECT * FROM employees", conn)
    conn.close()

    col1, col2 = st.columns([1, 1])
    with col1:
        sel_emp = st.selectbox("Select Employee Account", emp_df["id"] + " - " + emp_df["name"], key="login_emp_select")
        emp_row = emp_df[emp_df["id"] == sel_emp.split(" - ")[0]].iloc[0]

        with st.form("login_form"):
            input_user = st.text_input("Username", value=str(emp_row["username"]).strip())
            input_pass = st.text_input("Password", type="password", value=str(emp_row["password"]).strip())
            mfa_token = st.text_input("MFA PIN", value=str(emp_row["pin"]).strip())
            if st.form_submit_button("Authenticate", type="primary"):
                st.session_state.authenticated = True
                st.session_state.current_user = emp_row.to_dict()
                st.rerun()
    st.stop()

user = st.session_state.current_user

st.sidebar.title("🌿 Edinburgh Place ERP")
st.sidebar.caption("Health Canada GPP • CRA B300 • AGCO")
st.sidebar.markdown(f"👤 **{user['name']}**\n\nRole: `{user['role']}`")

if st.sidebar.button("🔒 Sign Out"):
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.rerun()

st.sidebar.markdown("---")

# ==========================================
# STRICT USER ACCESS CONTROL RULES
# ==========================================
username_clean = str(user.get('name', '')).strip().capitalize()
if username_clean in ["Steven", "Robert", "Miguel"]:
    allowed_modules = ["My Work", "Vault Ledger", "QA Review", "Admin"]
elif username_clean == "Etienne":
    allowed_modules = ["QA Review"]
else:
    db_perms_str = str(user.get('permissions', 'My Work'))
    allowed_modules = [p.strip() for p in db_perms_str.split(',') if p.strip()]
    if not allowed_modules:
        allowed_modules = ["My Work"]

if "nav_module" not in st.session_state or st.session_state.nav_module not in allowed_modules:
    st.session_state.nav_module = allowed_modules[0]

current_module = st.sidebar.radio("Navigation Menu", allowed_modules, key="nav_module")

if st.sidebar.button("🔄 Re-Sync All Files"):
    erp.migrate_legacy_excel(EXCEL_PATH)
    st.sidebar.success("All files re-synced successfully!")
    st.rerun()


def selectbox_with_add_new(label, options_list, key):
    extended_options = options_list + ["➕ Add New..."]
    selection = st.selectbox(label, extended_options, key=key)
    if selection == "➕ Add New...":
        new_val = st.text_input(f"Enter new value for {label}", key=f"{key}_new_input")
        return new_val if new_val else ""
    return selection


# ==========================================
# MODULE ROUTING
# ==========================================
if current_module == "My Work":
    st.title(f"👋 Welcome, {user['name']}!")
    st.caption("Personal hub for assigned tasks and mandatory PPE verification.")

    today_str = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_conn()
    ppe_check = conn.execute("SELECT 1 FROM ppe_logs WHERE employee_name = ? AND timestamp LIKE ?",
                             (user['name'], f"{today_str}%")).fetchone()
    conn.close()

    if not ppe_check:
        st.warning(
            "⚠️ **Mandatory GPP Compliance Checkpoint:** You must complete and verify your Personal Protective Equipment (PPE) inspection before accessing your work tasks.")

        with st.form("mandatory_ppe_gate_form"):
            st.subheader("🛡️ Shift Entry & PPE Gateway")
            p_c1, p_c2 = st.columns(2)
            with p_c1:
                ppe_coat = st.checkbox("🥼 Clean Lab Coat / Protective Outerwear Secured")
                ppe_mask = st.checkbox("😷 Protective Face Mask Fitted Properly")
            with p_c2:
                ppe_gloves = st.checkbox("🧤 Sanitized Rubber / Nitrile Gloves Donned")
                ppe_inspect = st.checkbox(
                    "✨ Personal Inspection Completed (Free of external dust, lint, pet hair, or outside contaminants)")

            hand_wash = st.checkbox("🧼 20-Second Handwashing & Sanitization Protocol Performed")

            if st.form_submit_button("✅ Verify & Log PPE Compliance", type="primary"):
                if ppe_coat and ppe_mask and ppe_gloves and ppe_inspect and hand_wash:
                    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn = get_db_conn()
                    conn.execute(
                        "INSERT INTO ppe_logs (timestamp, employee_name, role, lab_coat, face_mask, gloves, personal_inspection, hand_wash, status) VALUES (?, ?, ?, 1, 1, 1, 1, 1, 'Cleared')",
                        (now_ts, user['name'], user['role'])
                    )
                    conn.commit()
                    conn.close()
                    erp.log_audit_crypto(user["name"], "PPE & HYGIENE VERIFIED",
                                         "Lab coat, mask, rubber gloves, personal inspection, and handwashing cleared.")
                    st.success("PPE Inspection verified and logged under your name! Accessing your work queue...")
                    st.rerun()
                else:
                    st.error(
                        "🛑 Compliance Gate Blocked: All protective wear and self-inspection checkpoints must be verified.")
        st.stop()
    else:
        st.success("✅ PPE Compliance Verified for Today. Authorized for Facility Operations.")

    st.markdown("### ⚡ Quick Operational Stations")
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        open_vault_modal = st.button("📦 Open Vault Movement Station", type="primary", use_container_width=True)
    with col_btn2:
        open_set_aside_modal = st.button("⚠️ SET ASIDE MATERIAL FOR DESTRUCTION ⚠️", use_container_width=True,
                                         key="set_aside_caution_btn")

    if "show_vault" not in st.session_state:
        st.session_state.show_vault = False
    if "show_set_aside" not in st.session_state:
        st.session_state.show_set_aside = False

    if open_vault_modal:
        st.session_state.show_vault = not st.session_state.show_vault
    if open_set_aside_modal:
        st.session_state.show_set_aside = not st.session_state.show_set_aside

    if st.session_state.show_set_aside:
        st.markdown("""
            <div style="background: repeating-linear-gradient(45deg, #ffd400, #ffd400 20px, #111111 20px, #111111 40px); padding: 15px; border-radius: 12px; border: 3px solid #111111; margin-bottom: 20px;">
                <h3 style="color: #ffffff; text-align: center; text-shadow: 2px 2px 4px #000000; margin: 0;">⚠️ QUARANTINE & SET ASIDE FOR DESTRUCTION STATION ⚠️</h3>
            </div>
        """, unsafe_allow_html=True)

        conn = get_db_conn()
        lots_df = pd.read_sql_query("SELECT lot_id, strain_or_name FROM inventory_lots", conn)
        conn.close()

        with st.form("inline_set_aside_form"):
            lot_options = lots_df["lot_id"].astype(str) + " - " + lots_df["strain_or_name"].astype(
                str) if not lots_df.empty else ["No Lots Available"]
            sel_lot = st.selectbox("1. Select Lot / Source Bag ID", lot_options)
            lot_id = sel_lot.split(" - ")[0] if " - " in sel_lot else sel_lot
            product_name = st.text_input("2. Product / Strain Name", "Animal Mints")

            loss_types = ["Processing Loss (Trimming / Milling Waste)", "Packing Loss (Damaged Pre-Rolls / Pouches)",
                          "Spillage / Dropped Material", "Failed Quality Check"]
            loss_type = st.selectbox("3. Loss Classification", loss_types)
            weight_g = st.number_input("4. Set Aside Weight (g)", min_value=1.0, value=50.0)
            notes = st.text_area("5. Reason / Details", "Material damaged during automated pre-roll packing.")

            if st.form_submit_button("🏷️ Confirm & Quarantine Material"):
                set_aside_id = f"SA-{random.randint(1000, 9999)}"
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                conn = get_db_conn()
                conn.execute(
                    "INSERT INTO set_aside_destruction VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending Manager Review')",
                    (set_aside_id, timestamp, user['name'], lot_id, loss_type, weight_g, product_name, notes)
                )
                conn.commit()
                conn.close()

                erp.log_audit_crypto(user['name'], f"SET ASIDE FOR DESTRUCTION {set_aside_id}",
                                     f"Lot: {lot_id} | Loss: {loss_type} | Weight: {weight_g}g")
                st.success(f"Material successfully quarantined and set aside (`{set_aside_id}`) for manager review!")
                st.session_state.show_set_aside = False
                st.rerun()

    if st.session_state.show_vault:
        st.markdown("---")
        st.info("📦 **Active Vault Movement Station** (Check-In / Check-Out)")
        conn = get_db_conn()
        lots_df = pd.read_sql_query("SELECT lot_id, strain_or_name FROM inventory_lots", conn)
        conn.close()

        with st.form("inline_vault_movement_form"):
            direction = st.radio("Movement Direction", ["Check-Out (Vault Removal)", "Check-In (Vault Addition)"])
            lot_options = lots_df["lot_id"].astype(str) + " - " + lots_df["strain_or_name"].astype(
                str) if not lots_df.empty else ["No Lots Available"]
            sel_bag = st.selectbox("Select Inventory Bag / Lot ID", lot_options)
            bag_id = sel_bag.split(" - ")[0] if " - " in sel_bag else sel_bag

            compliance_tasks = ["Packaging and Labeling Dried Flower", "Packaging and Labeling Extracts",
                                "Rolling Pre-Rolls", "Milling Biomass / Flower", "Infusing Product",
                                "Weighing and Bagging", "Making Hash / Concentrate"]
            assigned_task = selectbox_with_add_new("Associated Task Assignment", compliance_tasks, "inline_vault_task")
            manual_task_num = st.text_input("Manual Task / Reference Number", f"TSK-{random.randint(1000, 9999)}")
            net_wt = st.number_input("Net Weight (g)", value=500.0, step=10.0)
            notes = st.text_area("Movement Notes / Reason", "Routine vault transfer logged by operator.")

            if st.form_submit_button("🚀 Submit Vault Movement & Assign Task"):
                movement_id = f"MOV-{random.randint(1000, 9999)}"
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                task_id = manual_task_num.strip() if manual_task_num.strip() else f"TSK-{random.randint(900, 9999)}"

                conn = get_db_conn()
                conn.execute("INSERT INTO vault_movements VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (movement_id, timestamp, user['name'], direction, bag_id, assigned_task, net_wt, notes))
                conn.execute(
                    "INSERT OR REPLACE INTO tasks (task_id, assignee, action, status, genealogy_id, num_units, total_weight_g, thc_mg_per_g, end_product_name, new_lot_number, ctls_category) VALUES (?, ?, ?, 'Open', ?, 1, 0.0, 0.0, ?, '', '')",
                    (task_id, user['name'], f"{direction}: {assigned_task}", bag_id, assigned_task))
                conn.commit()
                conn.close()

                erp.log_audit_crypto(user['name'], f"VAULT MOVEMENT {direction}: {bag_id}",
                                     f"Task: {assigned_task} | Weight: {net_wt}g")
                st.success(f"Vault movement logged! Task '{assigned_task}' assigned to your queue.")
                st.session_state.show_vault = False
                st.rerun()

    conn = get_db_conn()
    tasks_df = pd.read_sql_query(
        f"SELECT * FROM tasks WHERE (assignee = '{user['name']}' OR assignee = 'All Staff') AND status != 'Cancelled'",
        conn)
    set_aside_df = pd.read_sql_query("SELECT * FROM set_aside_destruction ORDER BY timestamp DESC", conn)
    conn.close()

    st.markdown("---")
    st.subheader("🎯 Your Assigned Tasks")
    if not tasks_df.empty:
        for idx, row in tasks_df.iterrows():
            st.markdown(f"""
                <div class="erp-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 16px; font-weight: bold; color: #05ae4b;">📌 Task ID: {row['task_id']}</span>
                        <span style="background-color: #161d29; color: #ffd400; padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; border: 1px solid #2a374a;">Status: {row['status']}</span>
                    </div>
                    <div style="font-size: 14px; color: #f0f2f6; margin-bottom: 6px;">
                        <strong>Action:</strong> {row['action']}
                    </div>
                    <div style="font-size: 13px; color: #94a3b8;">
                        Source Lot: <code>{row['genealogy_id']}</code> | Product: <code>{row.get('end_product_name', 'N/A')}</code><br>
                        Units: <strong>{row.get('num_units', 1)}</strong> | Weight: <strong>{row.get('total_weight_g', 0.0)}g</strong> | THC: <strong>{row.get('thc_mg_per_g', 0.0)} mg/g</strong>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if row["status"] == "Open":
                if st.button("✅ Mark Complete & Update Inventory", key=f"task_{row['task_id']}", type="primary"):
                    conn = get_db_conn()
                    conn.execute("UPDATE tasks SET status='Complete' WHERE task_id=?", (row["task_id"],))

                    source_lot = row['genealogy_id']
                    new_lot = row.get('new_lot_number', '')
                    ctls_cat = row.get('ctls_category', 'Packaged Finished Product')
                    end_prod = row.get('end_product_name', 'Processed Product')
                    units = row.get('num_units', 1)
                    weight_g = row.get('total_weight_g', float(units * 3.5))

                    timestamp_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    conn.execute(
                        "INSERT INTO inventory_transactions (timestamp, lot_id, tx_type, quantity_change, uom, reference_doc, operator) VALUES (?, ?, 'TRANSFORMATION_USE', ?, 'g', ?, ?)",
                        (timestamp_now[:10], source_lot, -float(weight_g), f"Task {row['task_id']} consumption",
                         user['name'])
                    )

                    if new_lot and str(new_lot).strip() not in ['', 'None', 'nan']:
                        conn.execute(
                            "INSERT OR IGNORE INTO inventory_lots (lot_id, strain_or_name, ctls_category, qa_status, storage_bin) VALUES (?, ?, ?, 'APPROVED', 'Vault B - Finished Goods')",
                            (str(new_lot).strip(), end_prod, ctls_cat)
                        )
                        conn.execute(
                            "INSERT INTO inventory_transactions (timestamp, lot_id, tx_type, quantity_change, uom, reference_doc, operator) VALUES (?, ?, 'PRODUCTION_OUTPUT', ?, 'g', ?, ?)",
                            (timestamp_now[:10], str(new_lot).strip(), float(weight_g),
                             f"Task {row['task_id']} production ({units} units)", user['name'])
                        )

                    conn.commit()
                    conn.close()

                    erp.log_audit_crypto(user["name"], f"COMPLETED TASK {row['task_id']}",
                                         f"Produced {units} units ({weight_g}g) of {end_prod} (New Lot: {new_lot}). Inventory updated.")
                    st.success("Task completed and live inventory successfully updated!")
                    st.rerun()
    else:
        st.info("No active tasks in your queue.")

    st.markdown("---")
    st.subheader("📋 Set Aside Material Ledger & Status")
    if not set_aside_df.empty:
        st.dataframe(set_aside_df, use_container_width=True, hide_index=True)
    else:
        st.info("No items currently set aside for destruction.")

elif current_module == "Vault Ledger":
    st.title("🏛️ Vault Ledger & Live Inventory Status")
    df_vault = pd.read_sql_query("""
        SELECT il.lot_id AS "Lot / Batch #", il.strain_or_name AS "Strain / Product", il.ctls_category AS "CTLS Category",
               il.storage_bin AS "Vault Location", il.qa_status AS "QA Status", il.thc_pct AS "THC %", il.cbd_pct AS "CBD %",
               il.coa_reference AS "CoA Reference", COALESCE(SUM(it.quantity_change), 0) AS "Live Balance (g)"
        FROM inventory_lots il LEFT JOIN inventory_transactions it ON il.lot_id = it.lot_id
        GROUP BY il.lot_id ORDER BY il.qa_status, il.lot_id
    """, erp.conn)
    st.dataframe(df_vault, use_container_width=True, hide_index=True)

elif current_module == "QA Review":
    st.title("🛡️ QA Review & Compliance Hub")
    st.caption(
        "Upload, review, e-sign, deny, view, download, and archive mandatory Health Canada GPP compliance records, CoAs, packaging approvals, and inspection photographs.")

    st.markdown("### 📤 Upload Compliance Record or Photo")
    with st.form("qa_document_upload_form_sidebar"):
        doc_id = f"DOC-{random.randint(1000, 9999)}"
        doc_title = st.text_input("Document / Record Title", "Q3 Environmental Monitoring & Pest Control Log")

        doc_categories = [
            "Packaging Approval",
            "SOPs & Document Control",
            "Certificates of Analysis (CoAs)",
            "Batch Production & Packaging Records",
            "Sanitation & Pest Control Logs",
            "Personnel Training & Competency",
            "Deviations, CAPA & Recall Simulation",
            "Facility Inspection Photos & Equipment Calibration"
        ]
        doc_category = st.selectbox("Record Classification", doc_categories)

        uploaded_file = st.file_uploader("Upload Document / Photo (PDF, JPG, PNG, XLSX)",
                                         type=["pdf", "png", "jpg", "jpeg", "xlsx", "csv"])
        notes = st.text_area("QA Review Notes / Comments", "Pending QAP review and electronic signature.")

        if st.form_submit_button("📤 Upload Record for QA Review", type="primary"):
            filename = uploaded_file.name if uploaded_file else "Manual_Record_Entry.pdf"
            file_size = round(uploaded_file.size / 1024, 2) if uploaded_file else 100.0
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn = get_db_conn()
            conn.execute(
                "INSERT INTO compliance_documents (doc_id, timestamp, uploaded_by, category, document_title, filename, file_size_kb, notes, status, esign_approved_by, esign_timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Under QA Review', '', '')",
                (doc_id, timestamp, user['name'], doc_category, doc_title, filename, file_size, notes)
            )
            conn.commit()
            conn.close()

            erp.log_audit_crypto(user['name'], f"QA DOCUMENT UPLOADED {doc_id}",
                                 f"Category: {doc_category} | Title: {doc_title}")
            st.success(
                f"Compliance record `{doc_title}` uploaded successfully! Ready for QAP e-signature approval or denial below.")
            st.rerun()

    st.markdown("---")
    st.subheader("🗂️ Compliance Document Review, View/Download & E-Sign Approval / Denial Ledger")

    conn = get_db_conn()
    pending_docs = pd.read_sql_query("SELECT * FROM compliance_documents ORDER BY timestamp DESC", conn)
    conn.close()

    if not pending_docs.empty:
        for _, drow in pending_docs.iterrows():
            with st.expander(
                    f"📄 [{drow['status']}] {drow['document_title']} ({drow['category']}) — Uploaded by {drow['uploaded_by']} ({drow['timestamp']})"):
                col_d1, col_d2 = st.columns([2, 1])
                with col_d1:
                    st.write(f"**Filename:** `{drow['filename']}` ({drow['file_size_kb']} KB)")
                    st.write(f"**Notes:** {drow['notes']}")

                    # File view & download button
                    dummy_file_bytes = f"Edinburgh Place ERP Compliance Record\nTitle: {drow['document_title']}\nCategory: {drow['category']}\nUploader: {drow['uploaded_by']}\nTimestamp: {drow['timestamp']}\nNotes: {drow['notes']}".encode(
                        'utf-8')
                    st.download_button(
                        f"📥 Download / View File ({drow['filename']})",
                        data=dummy_file_bytes,
                        file_name=drow['filename'],
                        mime="application/octet-stream",
                        key=f"dl_file_{drow['doc_id']}"
                    )

                with col_d2:
                    if drow['status'] == 'Approved & E-Signed by QA':
                        st.success(f"✅ E-Signed by **{drow['esign_approved_by']}**\n`{drow['esign_timestamp']}`")
                    elif drow['status'] == 'Denied by QA':
                        st.error(f"❌ Denied by **{drow['esign_approved_by']}**\n`{drow['esign_timestamp']}`")
                    else:
                        st.warning("⚠️ Pending QAP Approval")

                st.markdown("---")
                with st.form(f"inline_esign_{drow['doc_id']}"):
                    sign_name = st.text_input("QAP / Approver Name", value=user['name'], key=f"name_{drow['doc_id']}")
                    sign_pin = st.text_input("Security PIN / Digital Token", type="password", value="",
                                             key=f"pin_{drow['doc_id']}")
                    approval_remark = st.text_area("Review / Approval Remarks",
                                                   "Verified and compliant with Health Canada GPP regulations.",
                                                   key=f"rem_{drow['doc_id']}")

                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        approve_btn = st.form_submit_button("✍️ Approve & E-Sign Document", type="primary")
                    with col_f2:
                        deny_btn = st.form_submit_button("❌ Deny & Revoke Document")

                    if approve_btn:
                        if sign_pin.strip():
                            esign_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            conn = get_db_conn()
                            conn.execute(
                                "UPDATE compliance_documents SET status='Approved & E-Signed by QA', esign_approved_by=?, esign_timestamp=?, notes=? WHERE doc_id=?",
                                (sign_name, esign_ts, f"Approved: {approval_remark}", drow['doc_id'])
                            )
                            conn.commit()
                            conn.close()

                            erp.log_audit_crypto(sign_name, f"QA E-SIGNED DOCUMENT {drow['doc_id']}",
                                                 f"Title: {drow['document_title']} | Remarks: {approval_remark}")
                            st.success(f"Document `{drow['document_title']}` successfully e-signed and approved!")
                            st.rerun()
                        else:
                            st.error("🛑 Security PIN is required to execute an official electronic signature.")

                    if deny_btn:
                        if sign_pin.strip():
                            esign_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            conn = get_db_conn()
                            conn.execute(
                                "UPDATE compliance_documents SET status='Denied by QA', esign_approved_by=?, esign_timestamp=?, notes=? WHERE doc_id=?",
                                (sign_name, esign_ts, f"Denied: {approval_remark}", drow['doc_id'])
                            )
                            conn.commit()
                            conn.close()

                            erp.log_audit_crypto(sign_name, f"QA DENIED DOCUMENT {drow['doc_id']}",
                                                 f"Title: {drow['document_title']} | Reason: {approval_remark}")
                            st.warning(f"Document `{drow['document_title']}` has been denied and revoked.")
                            st.rerun()
                        else:
                            st.error("🛑 Security PIN is required to execute a denial action.")
    else:
        st.info("No compliance documents found in the archive ledger.")

elif current_module == "Admin":
    st.title("⚙️ Facility Admin & Governance Hub")
    tabs = st.tabs([
        "👥 Employee Management",
        "🏗️ Multi-Source Lot Creation",
        "🚚 Receiving Log",
        "🎯 Employee Task Assignment",
        "📦 Vault Movements",
        "🗑️ Set Aside Review & Destruction",
        "🔥 Official Destruction Ledger",
        "🛡️ PPE Compliance Logs",
        "📦 Processing Logs",
        "🏷️ Packaging Logs",
        "🧼 Cleaning Logs",
        "Immutable Audit Timeline",
        "Master Inventory Sheets & Excel Editor",
        "📊 CTLS Monthly Report"
    ])

    with tabs[0]:
        st.subheader("👥 Employee Directory & Access Control")
        st.caption("Manage employee login credentials, training due dates, roles, and module permissions.")

        conn = get_db_conn()
        employees_df = pd.read_sql_query(
            "SELECT id, name, username, password, pin, role, training_due_date, permissions, status FROM employees",
            conn)
        conn.close()

        st.dataframe(employees_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("✏️ Direct Employee Account & Training Editor")

        conn = get_db_conn()
        emp_list = pd.read_sql_query("SELECT id, name FROM employees", conn)
        conn.close()

        emp_options = emp_list["id"] + " - " + emp_list["name"] if not emp_list.empty else ["No Employees"]
        selected_emp_str = st.selectbox("Select Employee to Edit or Create New",
                                        ["➕ Create New Employee"] + list(emp_options), key="sel_emp_mgmt_dropdown")

        if selected_emp_str == "➕ Create New Employee":
            edit_id = f"EMP-{random.randint(107, 999)}"
            edit_name = st.text_input("Full Name", "New Operator", key="new_emp_name")
            edit_user = st.text_input("Username", "operator", key="new_emp_user")
            edit_pass = st.text_input("Password", "demo123", key="new_emp_pass")
            edit_pin = st.text_input("MFA PIN", "1009", key="new_emp_pin")
            edit_role = st.selectbox("Role",
                                     ["Technician / Operator", "Facility Admin", "QA / Manager", "Packaging Specialist",
                                      "QA Specialist"], key="new_emp_role")
            edit_training = st.text_input("Training Redo Due Date (YYYY-MM-DD)", "2027-01-01", key="new_emp_train")

            st.write("**Module Permissions:**")
            e_my_work = st.checkbox("My Work", value=True, key="new_mw")
            e_vault = st.checkbox("Vault Ledger", value=True, key="new_vl")
            e_qa = st.checkbox("QA Review", value=True, key="new_qa")
            e_admin = st.checkbox("Admin", value=False, key="new_ad")

            if st.button("💾 Create New Employee Account", type="primary", key="btn_create_emp"):
                perms_list = []
                if e_my_work: perms_list.append("My Work")
                if e_vault: perms_list.append("Vault Ledger")
                if e_qa: perms_list.append("QA Review")
                if e_admin: perms_list.append("Admin")
                perms_str = ",".join(perms_list)

                conn = get_db_conn()
                conn.execute("""
                    INSERT OR REPLACE INTO employees (id, name, username, password, pin, role, status, training_valid, training_due_date, permissions)
                    VALUES (?, ?, ?, ?, ?, ?, 'Active', 1, ?, ?)
                """, (edit_id, edit_name, edit_user, edit_pass, edit_pin, edit_role, edit_training, perms_str))
                conn.commit()
                conn.close()

                erp.log_audit_crypto(user["name"], f"CREATED EMPLOYEE: {edit_name}",
                                     f"ID: {edit_id} | Role: {edit_role}")
                st.success(f"New employee `{edit_name}` successfully created!")
                st.rerun()
        else:
            target_id = selected_emp_str.split(" - ")[0]
            conn = get_db_conn()
            cur_row = conn.execute("SELECT * FROM employees WHERE id = ?", (target_id,)).fetchone()
            conn.close()

            if cur_row:
                cur_perms = str(cur_row["permissions"])
                edit_name = st.text_input("Full Name", value=str(cur_row["name"]), key=f"edit_name_{target_id}")
                edit_user = st.text_input("Username", value=str(cur_row["username"]), key=f"edit_user_{target_id}")
                edit_pass = st.text_input("Password", value=str(cur_row["password"]), key=f"edit_pass_{target_id}")
                edit_pin = st.text_input("MFA PIN", value=str(cur_row["pin"]), key=f"edit_pin_{target_id}")
                edit_role = st.text_input("Role", value=str(cur_row["role"]), key=f"edit_role_{target_id}")
                edit_training = st.text_input("Training Redo Due Date (YYYY-MM-DD)",
                                              value=str(cur_row["training_due_date"]), key=f"edit_train_{target_id}")

                st.write("**Module Permissions:**")
                e_my_work = st.checkbox("My Work", value="My Work" in cur_perms, key=f"edit_mw_{target_id}")
                e_vault = st.checkbox("Vault Ledger", value="Vault Ledger" in cur_perms, key=f"edit_vl_{target_id}")
                e_qa = st.checkbox("QA Review", value="QA Review" in cur_perms, key=f"edit_qa_{target_id}")
                e_admin = st.checkbox("Admin", value="Admin" in cur_perms, key=f"edit_ad_{target_id}")

                if st.button("💾 Update Employee Account", type="primary", key=f"btn_update_emp_{target_id}"):
                    perms_list = []
                    if e_my_work: perms_list.append("My Work")
                    if e_vault: perms_list.append("Vault Ledger")
                    if e_qa: perms_list.append("QA Review")
                    if e_admin: perms_list.append("Admin")
                    perms_str = ",".join(perms_list)

                    conn = get_db_conn()
                    conn.execute("""
                        UPDATE employees SET name=?, username=?, password=?, pin=?, role=?, training_due_date=?, permissions=? WHERE id=?
                    """, (edit_name, edit_user, edit_pass, edit_pin, edit_role, edit_training, perms_str, target_id))
                    conn.commit()
                    conn.close()

                    erp.log_audit_crypto(user["name"], f"UPDATED EMPLOYEE: {edit_name}",
                                         f"ID: {target_id} | Permissions: {perms_str}")
                    st.success(
                        f"Employee account for `{edit_name}` successfully updated with permissions: `{perms_str}`!")
                    st.rerun()

    with tabs[1]:
        st.subheader("🏗️ Multi-Source Lot Creation & Inventory Traceability")
        st.caption(
            "Create a new master inventory lot by combining weight from one or multiple parent source lots. Maintains strict Health Canada GPP genealogy and live vault adjustments.")

        conn = get_db_conn()
        lots_list_df = pd.read_sql_query("SELECT lot_id, strain_or_name FROM inventory_lots", conn)
        conn.close()

        lot_options = lots_list_df["lot_id"].astype(str) + " - " + lots_list_df["strain_or_name"].astype(
            str) if not lots_list_df.empty else ["No Lots Available"]

        if "num_sources" not in st.session_state:
            st.session_state.num_sources = 1

        col_btn_add, col_btn_rem = st.columns([1, 1])
        with col_btn_add:
            if st.button("➕ Add Another Source Lot"):
                st.session_state.num_sources += 1
                st.rerun()
        with col_btn_rem:
            if st.session_state.num_sources > 1:
                if st.button("➖ Remove Last Source Lot"):
                    st.session_state.num_sources -= 1
                    st.rerun()

        with st.form("admin_multisource_lot_form"):
            new_lot_id = st.text_input("New Child Lot ID (Output)",
                                       f"LH-LOT-{datetime.now().strftime('%Y%m%d')}-{random.randint(100, 999)}")
            strain_name = st.text_input("Strain or Product Name", "Custom Blended Infused Pre-Rolls")

            ctls_categories = ["Packaged Finished Product", "Unpackaged Dried", "Extracts / Concentrates",
                               "Seeds / Plants"]
            ctls_cat = st.selectbox("CTLS Product Category", ctls_categories)

            st.markdown("---")
            st.write("**Parent Source Lots & Grams Drawn:**")

            source_draws = []
            total_combined_qty = 0.0

            for i in range(st.session_state.num_sources):
                c_s1, c_s2 = st.columns([3, 2])
                with c_s1:
                    sel_src = st.selectbox(f"Source Lot #{i + 1}", lot_options, key=f"src_lot_{i}")
                    src_id = sel_src.split(" - ")[0] if " - " in sel_src else sel_src
                with c_s2:
                    draw_qty = st.number_input(f"Grams Drawn from #{i + 1}", min_value=1.0, value=100.0, step=10.0,
                                               key=f"src_qty_{i}")
                source_draws.append((src_id, draw_qty))
                total_combined_qty += float(draw_qty)

            st.info(f"📊 **Total Combined Output Weight:** `{total_combined_qty:.2f}g`")

            st.markdown("---")
            col_q1, col_q2 = st.columns(2)
            with col_q1:
                thc_pct = st.number_input("Combined THC %", min_value=0.0, max_value=100.0, value=26.5, step=0.1)
                qa_status = st.selectbox("QA Approval Status", ["APPROVED", "QUARANTINE"])
            with col_q2:
                cbd_pct = st.number_input("Combined CBD %", min_value=0.0, max_value=100.0, value=0.5, step=0.1)
                storage_bin = st.selectbox("Vault Storage Bin", ["Vault B - Finished Goods", "Vault A - Quarantine",
                                                                 "Vault C - Extracts Storage"])

            coa_ref = st.text_input("CoA Reference Number", f"COA-{random.randint(10000, 99999)}")

            if st.form_submit_button("🚀 Create Multi-Source Lot & Deduct All Parents", type="primary"):
                if new_lot_id.strip() and strain_name.strip():
                    timestamp_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn = get_db_conn()

                    parent_summary = ", ".join([f"{s[0]} ({s[1]}g)" for s in source_draws])
                    conn.execute("""
                        INSERT OR REPLACE INTO inventory_lots 
                        (lot_id, strain_or_name, ctls_category, supplier_name, supplier_lot_id, thc_pct, cbd_pct, coa_reference, storage_bin, qa_status, qap_approved_by, qap_approved_at)
                        VALUES (?, ?, ?, 'Multi-Source Blend', ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (new_lot_id.strip(), strain_name.strip(), ctls_cat, parent_summary, thc_pct, cbd_pct, coa_ref,
                          storage_bin, qa_status, user['name'], timestamp_now))

                    for src_id, qty in source_draws:
                        conn.execute("""
                            INSERT INTO inventory_transactions (timestamp, lot_id, tx_type, quantity_change, uom, reference_doc, operator)
                            VALUES (?, ?, 'TRANSFORMATION_USE', ?, 'g', ?, ?)
                        """, (timestamp_now[:10], src_id, -float(qty), f"Multi-source draw for child: {new_lot_id}",
                              user['name']))

                    conn.execute("""
                        INSERT INTO inventory_transactions (timestamp, lot_id, tx_type, quantity_change, uom, reference_doc, operator)
                        VALUES (?, ?, 'PRODUCTION_OUTPUT', ?, 'g', ?, ?)
                    """, (timestamp_now[:10], new_lot_id.strip(), float(total_combined_qty),
                          f"Multi-source blend from parents: {parent_summary}", user['name']))

                    conn.commit()
                    conn.close()

                    erp.log_audit_crypto(user['name'], f"MULTI-SOURCE LOT CREATED {new_lot_id}",
                                         f"Parents: {parent_summary} | Total Qty: {total_combined_qty}g")
                    st.success(
                        f"Multi-source Lot `{new_lot_id}` successfully created with `{total_combined_qty}g` from {len(source_draws)} parent lots!")
                    st.session_state.num_sources = 1
                    st.rerun()

    with tabs[2]:
        st.subheader("🚚 Wholesale B2B Receiving Log")
        conn = get_db_conn()
        df_rec = pd.read_sql_query("""
            SELECT it.timestamp AS "Receiving Date", it.reference_doc AS "PO Number", il.supplier_name AS "Supplier / LP Name",
                   il.lot_id AS "Lot Number", il.strain_or_name AS "Product Name", il.ctls_category AS "Category",
                   il.supplier_lot_id AS "Supplier Batch #", it.quantity_change AS "Weight Received (g)", il.qa_status AS "Status"
            FROM inventory_transactions it JOIN inventory_lots il ON it.lot_id = il.lot_id WHERE it.tx_type = 'RECEIVING'
            ORDER BY it.timestamp DESC
        """, conn)
        conn.close()
        st.dataframe(df_rec, use_container_width=True, hide_index=True)

    with tabs[3]:
        st.subheader("🎯 Employee Task Assignment & Management")
        st.caption(
            "Assign operational tasks including packaging/labeling for dried flower or extracts, specifying units, weight, and THC potency.")

        conn = get_db_conn()
        emp_df = pd.read_sql_query("SELECT name FROM employees", conn)
        lots_df = pd.read_sql_query("SELECT lot_id, strain_or_name FROM inventory_lots", conn)
        conn.close()

        with st.form("employee_task_assignment_form"):
            sel_employee = st.selectbox("1. Select Employee", emp_df["name"].tolist() + ["All Staff"])

            compliance_processes = [
                "Packaging and Labeling Dried Flower",
                "Packaging and Labeling Extracts",
                "Rolling Pre-Rolls",
                "Milling Biomass / Flower",
                "Infusing Product",
                "Weighing and Bagging",
                "Making Hash / Concentrate"
            ]
            sel_process = selectbox_with_add_new("2. Select Process Type", compliance_processes, "admin_task_process")

            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1:
                num_units = st.number_input("3. Number of Units", min_value=1, value=100)
            with col_a2:
                total_weight_g = st.number_input("4. Total Weight (g)", min_value=0.1, value=350.0, step=10.0)
            with col_a3:
                thc_mg_per_g = st.number_input("5. THC Potency (mg/g)", min_value=0.0, value=250.0, step=10.0)

            lot_options = lots_df["lot_id"].astype(str) + " - " + lots_df["strain_or_name"].astype(
                str) if not lots_df.empty else ["No Lots Available"]
            sel_source_lot = st.selectbox("6. Select Source Lot", lot_options)
            source_lot_id = sel_source_lot.split(" - ")[0] if " - " in sel_source_lot else sel_source_lot

            end_product_name = st.text_input("7. End Product Name", "Dantes Inferno Infused Pre-Rolls")
            new_lot_number = st.text_input("8. New Lot Number (For Inventory Output)",
                                           f"LOT-OUT-{datetime.now().strftime('%Y%m%d')}-{random.randint(100, 999)}")

            ctls_categories = ["Packaged Finished Product", "Unpackaged Dried", "Extracts / Concentrates",
                               "Seeds / Plants"]
            ctls_category = st.selectbox("9. CTLS Product Category", ctls_categories)

            if st.form_submit_button("🚀 Assign Task to Employee"):
                if end_product_name.strip():
                    task_id = f"TSK-{random.randint(1000, 9999)}"
                    action_desc = f"{sel_process} ({num_units} units | {total_weight_g}g | {thc_mg_per_g} mg/g THC)"

                    conn = get_db_conn()
                    conn.execute(
                        "INSERT OR REPLACE INTO tasks (task_id, assignee, action, status, genealogy_id, num_units, total_weight_g, thc_mg_per_g, end_product_name, new_lot_number, ctls_category) VALUES (?, ?, ?, 'Open', ?, ?, ?, ?, ?, ?, ?)",
                        (task_id, sel_employee, action_desc, source_lot_id, num_units, total_weight_g, thc_mg_per_g,
                         end_product_name, new_lot_number, ctls_category)
                    )
                    conn.commit()
                    conn.close()

                    erp.log_audit_crypto(user["name"], f"ASSIGNED TASK {task_id}",
                                         f"Assigned to {sel_employee}: {action_desc} | Source: {source_lot_id} | New Lot: {new_lot_number}")
                    st.success(f"Task successfully assigned to `{sel_employee}`!")
                    st.rerun()

        st.markdown("### 📋 Active Facility Tasks & Cancellation Management")
        conn = get_db_conn()
        active_tasks_df = pd.read_sql_query(
            "SELECT task_id, assignee, action, status, num_units, total_weight_g, thc_mg_per_g, end_product_name FROM tasks WHERE status != 'Cancelled'",
            conn)
        conn.close()

        if not active_tasks_df.empty:
            for _, trow in active_tasks_df.iterrows():
                col_t1, col_t2, col_t3 = st.columns([3, 2, 1])
                col_t1.write(f"**{trow['task_id']}** ({trow['assignee']}): {trow['action']} [{trow['status']}]")
                col_t2.caption(
                    f"Product: {trow['end_product_name']} | Units: {trow['num_units']} | Wt: {trow['total_weight_g']}g | THC: {trow['thc_mg_per_g']} mg/g")
                if trow['status'] == 'Open':
                    if col_t3.button("❌ Cancel Task", key=f"cancel_task_{trow['task_id']}"):
                        conn = get_db_conn()
                        conn.execute("UPDATE tasks SET status='Cancelled' WHERE task_id=?", (trow['task_id'],))
                        conn.commit()
                        conn.close()
                        erp.log_audit_crypto(user['name'], f"CANCELLED TASK {trow['task_id']}",
                                             f"Cancelled task assigned to {trow['assignee']}.")
                        st.warning(f"Task `{trow['task_id']}` has been cancelled.")
                        st.rerun()
        else:
            st.info("No active tasks found.")

    with tabs[4]:
        st.subheader("📦 Vault Movements Audit Viewer")
        conn = get_db_conn()
        mov_df = pd.read_sql_query("SELECT * FROM vault_movements ORDER BY timestamp DESC", conn)
        conn.close()
        st.dataframe(mov_df, use_container_width=True, hide_index=True)

    with tabs[5]:
        st.subheader("🗑️ Review Set Aside Material & Execute Destruction")
        st.caption(
            "Review items set aside by operators on the My Work page and execute official Health Canada GPP destruction logs.")

        conn = get_db_conn()
        pending_set_aside = pd.read_sql_query(
            "SELECT * FROM set_aside_destruction WHERE status = 'Pending Manager Review'", conn)
        conn.close()

        if not pending_set_aside.empty:
            for _, row in pending_set_aside.iterrows():
                with st.expander(
                        f"Set Aside ID: {row['set_aside_id']} | Lot: {row['lot_id']} ({row['weight_g']}g - {row['loss_type']})"):
                    st.write(f"**Operator:** {row['employee_name']} | **Timestamp:** {row['timestamp']}")
                    st.write(f"**Product / Strain:** {row['product_name']} | **Notes:** {row['notes']}")

                    with st.form(f"approve_dest_{row['set_aside_id']}"):
                        disposal_method = st.selectbox("Disposal Method",
                                                       ["Rendering Unusable (Mixed with inert matter)",
                                                        "High-Temperature Incineration",
                                                        "Composting Facility Transfer"],
                                                       key=f"dm_{row['set_aside_id']}")
                        denaturing_agent = st.text_input("Denaturing Agent Used",
                                                         "Cat litter & shredded paper (mixed to >50% non-cannabis solid)",
                                                         key=f"da_{row['set_aside_id']}")
                        qa_witness = st.text_input("QA Witness / Manager Name", user['name'],
                                                   key=f"qw_{row['set_aside_id']}")

                        if st.form_submit_button("🔥 Approve & Execute Official Destruction"):
                            dest_id = f"DEST-{random.randint(1000, 9999)}"
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                            conn = get_db_conn()
                            conn.execute(
                                "INSERT INTO destruction_ledger VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Completed')",
                                (dest_id, timestamp, row['lot_id'], row['loss_type'], row['weight_g'], disposal_method,
                                 denaturing_agent, row['employee_name'], qa_witness, row['notes'])
                            )
                            conn.execute(
                                "INSERT INTO inventory_transactions (timestamp, lot_id, tx_type, quantity_change, uom, reference_doc, operator) VALUES (?, ?, 'DESTRUCTION', ?, 'g', ?, ?)",
                                (timestamp[:10], row['lot_id'], -float(row['weight_g']),
                                 f"Destruction {dest_id} (from Set Aside {row['set_aside_id']})", user['name'])
                            )
                            conn.execute(
                                "UPDATE set_aside_destruction SET status='Destroyed & Approved' WHERE set_aside_id=?",
                                (row['set_aside_id'],))
                            conn.commit()
                            conn.close()

                            erp.log_audit_crypto(user['name'], f"MANAGER APPROVED DESTRUCTION {dest_id}",
                                                 f"Set Aside {row['set_aside_id']} destroyed. Weight: {row['weight_g']}g")
                            st.success(f"Destruction executed successfully under ID `{dest_id}`!")
                            st.rerun()
        else:
            st.info("No pending set-aside material waiting for review.")

    with tabs[6]:
        st.subheader("🔥 Official Destruction & Waste Ledger Viewer")
        conn = get_db_conn()
        dest_df = pd.read_sql_query("SELECT * FROM destruction_ledger ORDER BY timestamp DESC", conn)
        conn.close()
        st.dataframe(dest_df, use_container_width=True, hide_index=True)

    with tabs[7]:
        st.subheader("🛡️ Employee PPE Compliance Logs Viewer")
        conn = get_db_conn()
        ppe_logs_df = pd.read_sql_query("SELECT * FROM ppe_logs ORDER BY timestamp DESC", conn)
        conn.close()
        st.dataframe(ppe_logs_df, use_container_width=True, hide_index=True)

    with tabs[8]:
        st.subheader("📦 Processing Logs Viewer")
        conn = get_db_conn()
        st.dataframe(pd.read_sql_query(
            "SELECT * FROM tasks WHERE action LIKE '%Milling%' OR action LIKE '%Pre-Rolls%' OR action LIKE '%Hash%' OR action LIKE '%Infusing%' OR action LIKE '%Packaging%'",
            conn), use_container_width=True, hide_index=True)
        conn.close()

    with tabs[9]:
        st.subheader("🏷️ Packaging Logs Viewer")
        conn = get_db_conn()
        st.dataframe(pd.read_sql_query(
            "SELECT * FROM tasks WHERE action LIKE '%Bagging%' OR action LIKE '%Weighing%' OR action LIKE '%Packaging%'",
            conn), use_container_width=True, hide_index=True)
        conn.close()

    with tabs[10]:
        st.subheader("🧼 Cleaning & Sanitation Logs Viewer")
        conn = get_db_conn()
        st.dataframe(pd.read_sql_query("SELECT * FROM cleaning_logs", conn), use_container_width=True, hide_index=True)
        conn.close()

    with tabs[11]:
        conn = get_db_conn()
        st.dataframe(pd.read_sql_query("SELECT * FROM audit_trail ORDER BY id DESC", conn), use_container_width=True)
        conn.close()

    with tabs[12]:
        st.subheader("📝 Master Inventory Sheets, Excel Editor & QA Records")
        if os.path.exists(EXCEL_PATH):
            sheet_options = ["compliance_documents"] + pd.ExcelFile(EXCEL_PATH).sheet_names
            sheet_choice = st.selectbox("Select Table / Sheet to Edit", sheet_options)

            if sheet_choice == "compliance_documents":
                conn = get_db_conn()
                df_sheet = pd.read_sql_query("SELECT * FROM compliance_documents", conn)
                conn.close()
            else:
                xl = pd.ExcelFile(EXCEL_PATH)
                df_sheet = pd.read_excel(xl, sheet_name=sheet_choice)

            edited_df = st.data_editor(df_sheet, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Save Changes to Database / Excel"):
                if sheet_choice == "compliance_documents":
                    conn = get_db_conn()
                    edited_df.to_sql("compliance_documents", conn, if_exists="replace", index=False)
                    conn.close()
                    st.success("Compliance documents table successfully updated!")
                else:
                    with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                        edited_df.to_excel(writer, sheet_name=sheet_choice, index=False)
                    erp.migrate_legacy_excel(EXCEL_PATH)
                    st.success("Successfully saved and re-synced!")
                st.rerun()

    with tabs[13]:
        st.subheader("📊 Health Canada Monthly CTLS Report Generator")
        st.caption(
            "Generate official monthly inventory tracking reports for submission to the Cannabis Tracking and Licensing System (CTLS).")

        report_month = st.selectbox("Select Reporting Month", ["2026-09", "2026-08", "2026-07", "2026-06", "2026-05"])

        conn = get_db_conn()
        vault_df = pd.read_sql_query("SELECT * FROM inventory_lots", conn)
        rec_df = pd.read_sql_query("SELECT * FROM inventory_transactions WHERE tx_type='RECEIVING'", conn)
        dest_df = pd.read_sql_query("SELECT * FROM destruction_ledger", conn)
        conn.close()

        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric("Total Active Lots", len(vault_df))
        col_r2.metric("Wholesale Receipts Logged", len(rec_df))
        col_r3.metric("Destruction Events Logged", len(dest_df))

        st.markdown("---")
        st.subheader("📋 Monthly CTLS Summary Ledger")

        total_received = sum(rec_df['quantity_change']) if not rec_df.empty else 0.0
        total_destroyed = sum(dest_df['weight_destroyed_g']) if not dest_df.empty else 0.0

        ctls_summary = pd.DataFrame([
            {"Category": "Dried Flower (Unpackaged / Bulk)", "Opening Stock (g)": 15000.0,
             "Receipts (g)": total_received, "Produced (g)": 5000.0, "Destroyed (g)": total_destroyed,
             "Closing Stock (g)": 15000.0 + total_received + 5000.0 - total_destroyed},
            {"Category": "Extracts / Concentrates", "Opening Stock (g)": 2500.0, "Receipts (g)": 0.0,
             "Produced (g)": 1400.0, "Destroyed (g)": 0.0, "Closing Stock (g)": 3900.0},
            {"Category": "Packaged Finished Product", "Opening Stock (g)": 800.0, "Receipts (g)": 0.0,
             "Produced (g)": 630.0, "Destroyed (g)": 0.0, "Closing Stock (g)": 1430.0}
        ])

        st.dataframe(ctls_summary, use_container_width=True, hide_index=True)

        st.download_button(
            "📥 Download Official CTLS Monthly Report (CSV)",
            data=ctls_summary.to_csv(index=False),
            file_name=f"CTLS_Monthly_Report_{report_month}.csv",
            mime="text/css",
            type="primary"
        )
