import streamlit as st
import gspread
from gspread.utils import rowcol_to_a1   # batch update ke liye
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import traceback
import io
import json
import base64

# -----------------------------
# 1. CONFIGURATION
# -----------------------------
st.set_page_config(page_title="Cambridge Portal", page_icon="🏫", layout="wide")

# =====================================================================
# NAVY BLUE GLASSMORPHISM THEME (तुम्हारी पसंद)
# =====================================================================
st.markdown("""
<style>
/* ---------- Glass Cards ---------- */
div[data-testid="stVerticalBlock"] > div {
    background: rgba(30, 41, 59, 0.65);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

/* ---------- Buttons ---------- */
.stButton > button {
    border-radius: 12px;
    background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
    border: none;
    color: white;
    font-weight: 600;
    letter-spacing: 0.5px;
    transition: all 0.3s ease;
    padding: 10px 24px;
}
.stButton > button:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 24px rgba(0,0,0,0.4);
    background: linear-gradient(135deg, #2d5a87 0%, #1e3a5f 100%);
}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background-color: #0f172a;
    border-right: 1px solid #1e293b;
    transition: width 0.3s ease;
}
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
    color: #e2e8f0;
}
section[data-testid="stSidebar"] .stSelectbox label {
    color: #e2e8f0 !important;
}

/* ---------- Input Fields ---------- */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background-color: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
    color: white !important;
}

/* ---------- Tables ---------- */
.stTable tbody tr:nth-child(even) {
    background-color: rgba(30, 41, 59, 0.5);
}
.stTable tbody tr:hover, [data-testid="stTable"] tbody tr:hover {
    background-color: rgba(30, 64, 95, 0.3) !important;
    transition: background-color 0.2s ease;
}

/* ---------- Metric Cards ---------- */
[data-testid="metric-container"] {
    background: linear-gradient(145deg, #1e293b, #0f172a);
    border-radius: 20px;
    border: 1px solid #334155;
    padding: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}
[data-testid="metric-container"] label {
    color: #94a3b8 !important;
    font-size: 13px;
    font-weight: 500;
}
[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    font-size: 34px !important;
    font-weight: 800;
    color: #fbbf24 !important;
}

/* ---------- Fade-in Animation ---------- */
.main > div:first-child {
    animation: fadeIn 0.6s ease;
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

/* ---------- Receipt Card ---------- */
.receipt-card {
    background: #1e2a3a;
    border: 1px dashed #f0c45a;
    border-radius: 12px;
    padding: 20px;
    margin: 20px 0;
}
.receipt-card h3 { color: #f0c45a; text-align: center; margin-bottom: 15px; }
.receipt-card p { font-size: 16px; margin: 5px 0; color: #e0e7f2; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 2. LOGIN
# -----------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["role"] = None

if not st.session_state["authenticated"]:
    st.markdown("""
    <style>
    .login-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 24px;
        padding: 40px;
        max-width: 400px;
        margin: 80px auto;
        box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        text-align: center;
    }
    .login-card h2 { color: #fbbf24; margin-bottom: 30px; }
    </style>
    <div class="login-card">
    """, unsafe_allow_html=True)

    try:
        st.image("School_logo.png", width=180)
    except:
        pass
    st.markdown("<h2>Cambridge International School</h2>", unsafe_allow_html=True)
    role = st.selectbox("Select Role", ["Teacher", "Clerk", "Principal"])
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        valid = False
        if role == "Teacher" and pwd == "TCH2024": valid = True
        elif role == "Clerk" and pwd == "CLK2024": valid = True
        elif role == "Principal" and pwd == "PRN2024": valid = True
        if valid:
            st.session_state["authenticated"] = True
            st.session_state["role"] = role
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# -----------------------------
# 3. DATABASE CONNECTION
# -----------------------------
SHEET_ID = "1n6SvSamatNUX8AEZpFXE5IvERZ8a4eDWgQkW6uj-WDc"

@st.cache_resource
def get_workbook():
    try:
        if "gcp_creds" not in st.secrets:
            st.error("❌ Streamlit Secrets missing 'gcp_creds'.")
            return None
        creds_dict = json.loads(st.secrets["gcp_creds"])
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID)
    except Exception as e:
        st.error(f"❌ Connection failed: {e}")
        return None

wb = get_workbook()
if wb is None: st.stop()

# -----------------------------
# 4. CACHING FUNCTIONS (TTL 1800)
# -----------------------------
@st.cache_data(ttl=1800)
def get_sheet_names():
    return [ws.title.strip() for ws in wb.worksheets()]

def find_sheet(name):
    names = get_sheet_names()
    name_clean = name.strip().lower()
    for n in names:
        if n.lower() == name_clean: return wb.worksheet(n)
    for n in names:
        if name_clean in n.lower(): return wb.worksheet(n)
    return None

def get_available_classes():
    sheets = get_sheet_names()
    classes = []
    for s in sheets:
        if s.upper().startswith("MASTER_"):
            class_name = s.split("_", 1)[1].strip()
            if class_name: classes.append(class_name)
    return sorted(classes) if classes else ["LKG"]

@st.cache_data(ttl=1800)
def load_master_data(class_name):
    sheet = find_sheet(f"MASTER_{class_name}")
    if not sheet: return pd.DataFrame(), []
    raw = sheet.get_all_values()
    if len(raw) < 2: return pd.DataFrame(), []
    headers = [h.strip() for h in raw[0]]
    df = pd.DataFrame(raw[1:], columns=headers)
    id_col = next((c for c in df.columns if c.upper() in ['ID', 'STUDENT ID']), None)
    name_col = next((c for c in df.columns if c.upper() in ['NAME', 'STUDENT NAME']), None)
    student_list = []
    if id_col and name_col:
        student_list = [f"{row[id_col]} - {row[name_col]}" for _, row in df.iterrows()]
    return df, student_list

@st.cache_data(ttl=1800)
def load_attendance_data(class_name):
    sheet = find_sheet(f"ATTENDANCE_{class_name}")
    return sheet.get_all_values() if sheet else []

@st.cache_data(ttl=1800)
def load_fees_data(class_name):
    sheet = find_sheet(f"FEES_{class_name}")
    return sheet.get_all_values() if sheet else []

@st.cache_data(ttl=1800)
def load_fee_structure():
    sheet = find_sheet("FEES_STRUCTURE")
    if not sheet: return {}
    data = sheet.get_all_values()
    fee_map = {}
    if len(data) >= 2:
        for row in data[1:]:
            if len(row) >= 2:
                cls, fee = row[0].strip(), row[1].strip()
                if cls and fee.isdigit(): fee_map[cls] = int(fee)
    return fee_map

# -----------------------------
# 5. SIDEBAR
# -----------------------------
with st.sidebar:
    st.header("Administration")
    st.markdown(f"**{st.session_state['role']}**")
    available_classes = get_available_classes()
    selected_class = st.selectbox("Class", available_classes)

    role = st.session_state["role"]
    if role == "Teacher":
        menu_options = ["Student Attendance","Attendance Report","Student Records","Edit Student Details","Add New Student"]
    elif role == "Clerk":
        menu_options = ["Fee Collection","Daily Cash Report","Add New Student","Student Records","Edit Student Details"]
    else:
        menu_options = ["Executive Dashboard","Student Attendance","Attendance Report","Fee Collection","Daily Cash Report","Student Records","Edit Student Details","Add New Student"]

    menu = st.radio("Navigation", menu_options, label_visibility="collapsed")

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# -----------------------------
# 6. LOAD DATA
# -----------------------------
df_master, student_list = load_master_data(selected_class)
id_col = next((c for c in df_master.columns if c.upper() in ['ID','STUDENT ID']), None) if not df_master.empty else None
name_col = next((c for c in df_master.columns if c.upper() in ['NAME','STUDENT NAME']), None) if not df_master.empty else None

attendance_data = load_attendance_data(selected_class)
fees_data = load_fees_data(selected_class)
monthly_fee_map = load_fee_structure()
default_fee = monthly_fee_map.get(selected_class, 500)

master_sheet = find_sheet(f"MASTER_{selected_class}")
attendance_sheet = find_sheet(f"ATTENDANCE_{selected_class}")
fees_sheet = find_sheet(f"FEES_{selected_class}")
if not all([master_sheet, attendance_sheet, fees_sheet]):
    st.error("Required sheets missing.")
    st.stop()

def ensure_column(sheet, col_name):
    headers = sheet.row_values(1)
    if col_name not in headers:
        sheet.update_cell(1, len(headers)+1, col_name)
        st.cache_data.clear()

ensure_column(master_sheet, "ANNUAL_FEE")
ensure_column(master_sheet, "ADMISSION_FEE")

def compute_paid_total(sid, all_fees):
    total = 0
    if all_fees and len(all_fees)>1:
        for row in all_fees[1:]:
            if row[0].strip().upper() == sid.upper() and row[1].isdigit():
                total += int(row[1])
    return total

# -----------------------------
# 7. BRANDING
# -----------------------------
try:
    st.image("School_logo.png", width=180)
except:
    pass
st.markdown("<h2 style='text-align:center; color:#fbbf24;'>CAMBRIDGE INTERNATIONAL SCHOOL</h2>", unsafe_allow_html=True)
st.divider()

# =============================
# 8. EXECUTIVE DASHBOARD
# =============================
if menu == "Executive Dashboard" and role == "Principal":
    st.subheader(f"Dashboard – {selected_class}")
    if df_master.empty:
        st.warning("No student data.")
    else:
        total_students = len(df_master)
        today_str = datetime.now().strftime("%d-%m-%Y")
        att_headers = attendance_data[0] if attendance_data else []
        today_col_1based = att_headers.index(today_str)+1 if today_str in att_headers else None
        present = 0
        if today_col_1based and len(attendance_data)>1:
            # Convert to 0-based index for row list
            today_idx = today_col_1based - 1
            for row in attendance_data[1:]:
                if today_idx < len(row) and row[today_idx].strip().upper() == 'P':
                    present += 1
        att_pct = (present/total_students*100) if total_students else 0

        today_fees = 0
        if fees_data and len(fees_data)>1:
            for r in fees_data[1:]:
                if len(r)>=4 and r[3].split(' ')[0] == today_str and r[1].isdigit():
                    today_fees += int(r[1])

        current_month = datetime.now().month
        current_year = datetime.now().year
        month_col = 0
        if fees_data and len(fees_data)>1:
            for r in fees_data[1:]:
                if len(r)>=4:
                    ds = r[3].split(' ')[0]
                    try:
                        d = datetime.strptime(ds, "%d-%m-%Y")
                        if d.month == current_month and d.year == current_year and r[1].isdigit():
                            month_col += int(r[1])
                    except: pass

        monthly_fee = monthly_fee_map.get(selected_class, 500)
        expected_monthly = total_students * monthly_fee
        col_pct = (month_col/expected_monthly*100) if expected_monthly else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Students", total_students)
        col2.metric("Today Att.", f"{att_pct:.0f}% ({present}/{total_students})")
        col3.metric("Today Fees", f"₹{today_fees}")
        col4.metric("Month Fees", f"₹{month_col} ({col_pct:.0f}%)")

        if not df_master.empty:
            outstanding_list = []
            for _, student in df_master.iterrows():
                sid = str(student[id_col])
                name = student[name_col] if name_col else ""
                if current_month >= 4: months = current_month - 4 + 1
                else: months = current_month + 9
                expected = months * monthly_fee
                ann = int(student.get('ANNUAL_FEE', 0)) if str(student.get('ANNUAL_FEE',0)).isdigit() else 0
                adm = int(student.get('ADMISSION_FEE', 0)) if str(student.get('ADMISSION_FEE',0)).isdigit() else 0
                expected += ann + adm
                paid = compute_paid_total(sid, fees_data)
                outstanding = max(0, expected - paid)
                outstanding_list.append((name, outstanding))
            df_out = pd.DataFrame(outstanding_list, columns=["Name", "Outstanding"])
            top5 = df_out.nlargest(5, "Outstanding")
        else:
            top5 = pd.DataFrame()
        st.write("**Top 5 Outstanding**")
        if not top5.empty: st.dataframe(top5)
        else: st.write("None")

# =============================
# 9. STUDENT ATTENDANCE (BATCH UPDATES)
# =============================
elif menu == "Student Attendance":
    st.subheader(f"Daily Attendance – {selected_class}")
    if not student_list: st.warning("No students.")
    else:
        sel = st.selectbox("Select Student", ["-- Select --"] + student_list)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Mark Present"):
                if sel != "-- Select --":
                    sid = sel.split(" - ")[0]
                    try:
                        today = datetime.now().strftime("%d-%m-%Y")
                        hdrs = attendance_sheet.row_values(1)
                        ci = hdrs.index(today)+1 if today in hdrs else len(hdrs)+1
                        if today not in hdrs: attendance_sheet.update_cell(1, ci, today)
                        cell = attendance_sheet.find(sid)
                        attendance_sheet.update_cell(cell.row, ci, "P")
                        st.success(f"Marked {sel}")
                        st.cache_data.clear()
                    except Exception as e: st.error(f"Error: {e}")
        with c2:
            if st.button("Mark All Present"):
                try:
                    today = datetime.now().strftime("%d-%m-%Y")
                    hdrs = attendance_sheet.row_values(1)
                    ci = hdrs.index(today)+1 if today in hdrs else len(hdrs)+1
                    if today not in hdrs: attendance_sheet.update_cell(1, ci, today)
                    ids = [f"{row[id_col]}" for _, row in df_master.iterrows()]
                    cells_to_update = []
                    for sid in ids:
                        try:
                            cell = attendance_sheet.find(sid)
                            cells_to_update.append({
                                'range': rowcol_to_a1(cell.row, ci),
                                'values': [['P']]
                            })
                        except: pass
                    if cells_to_update:
                        attendance_sheet.batch_update(cells_to_update)
                    st.success(f"All {len(cells_to_update)} marked Present")
                    st.cache_data.clear()
                except Exception as e: st.error(f"Error: {e}")
        with c3:
            if st.button("Mark Absent for Unmarked"):
                try:
                    today = datetime.now().strftime("%d-%m-%Y")
                    hdrs = attendance_sheet.row_values(1)
                    if today not in hdrs:
                        st.warning("Column not created.")
                    else:
                        ci = hdrs.index(today)+1
                        ids = [f"{row[id_col]}" for _, row in df_master.iterrows()]
                        cells_to_update = []
                        for sid in ids:
                            try:
                                cell = attendance_sheet.find(sid)
                                val = attendance_sheet.cell(cell.row, ci).value
                                if not val or val.strip()=="":
                                    cells_to_update.append({
                                        'range': rowcol_to_a1(cell.row, ci),
                                        'values': [['A']]
                                    })
                            except: pass
                        if cells_to_update:
                            attendance_sheet.batch_update(cells_to_update)
                        st.success(f"Marked {len(cells_to_update)} students as Absent")
                        st.cache_data.clear()
                except Exception as e: st.error(f"Error: {e}")

# =============================
# 10. ATTENDANCE REPORT
# =============================
elif menu == "Attendance Report":
    st.subheader(f"Monthly Attendance Report – {selected_class}")
    months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    sel_month = st.selectbox("Month", months, index=datetime.now().month-1)
    sel_year = st.number_input("Year", min_value=2020, max_value=2030, value=datetime.now().year)
    month_num = months.index(sel_month) + 1
    month_str = f"{month_num:02d}"

    with st.spinner("Generating attendance report..."):
        if len(attendance_data) < 2:
            st.warning("No attendance data.")
        else:
            att_headers = attendance_data[0]
            date_cols = []
            col_indices = []
            for idx, h in enumerate(att_headers):
                if idx == 0: continue
                parts = h.split('-')
                if len(parts) == 3 and parts[1] == month_str and parts[2] == str(sel_year):
                    date_cols.append(h)
                    col_indices.append(idx)
            if not date_cols:
                st.warning(f"No records for {sel_month} {sel_year}")
            else:
                total_days = len(date_cols)
                records = []
                for row in attendance_data[1:]:
                    sid = row[0]
                    name = "N/A"
                    if not df_master.empty:
                        mask = df_master[id_col].astype(str) == sid
                        if mask.any():
                            name = df_master.loc[mask, name_col].values[0]
                    present = sum(1 for ci in col_indices if ci < len(row) and row[ci].strip().upper() == 'P')
                    percent = (present / total_days * 100) if total_days else 0
                    records.append({
                        "Student ID": sid,
                        "Name": name,
                        "Working Days": total_days,
                        "Present": present,
                        "Attendance %": round(percent, 1)
                    })
                df_rep = pd.DataFrame(records)
                def highlight_l