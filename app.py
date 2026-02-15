import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
from fpdf import FPDF

# --- 1. SICHERE ZUGANGSDATEN ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.sidebar.warning("🔑 Keys über Sidebar aktiv (oder secrets.toml nutzen)")
    SUPABASE_URL = st.sidebar.text_input("Supabase URL", value="https://sjviyysbjozculvslrdy.supabase.co")
    SUPABASE_KEY = st.sidebar.text_input("Supabase Key", type="password")

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        st.error("Verbindung zu Supabase fehlgeschlagen. Keys prüfen.")
        st.stop()
else:
    st.info("Bitte Supabase Keys eingeben, um zu starten.")
    st.stop()

# --- 2. HILFSFUNKTIONEN ---
def speech_to_text(audio_bytes):
    t = datetime.datetime.now().strftime('%H:%M')
    return f"Sprachaufnahme vom {t}"

def create_pdf(data, project_name, total_cost):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"Projektbericht: {project_name}", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(190, 10, f"Gesamtkosten: {total_cost:.2f} EUR", ln=True, align="C")
    pdf.ln(10)
    for entry in data:
        pdf.set_font("Arial", "B", 11)
        cat = entry.get('category', 'Notiz')
        status = entry.get('status', 'Ok')
        date = entry.get('created_at', '')[:10]
        header = f"{cat} | {status} ({date})"
        pdf.cell(190, 8, header.encode('latin-1', 'replace').decode('latin-1'), ln=True)
        pdf.set_font("Arial", "", 11)
        content = f"{entry.get('content')} - Kosten: {entry.get('cost_amount', 0)} EUR"
        pdf.multi_cell(190, 7, content.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(5)
    return bytes(pdf.output())

st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")
st.title("🏗️ WerkOS Pro")

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.header("🚀 Hauptmenü")
page = st.sidebar.radio("Gehe zu:", ["📋 Baustellen-Board", "📦 Material & Lager", "⏱️ Zeiterfassung"])

# Projektwahl (Laden aller Projekte aus der 'notes' Tabelle)
try:
    all_p = supabase.table("notes").select("project_name").execute()
    p_list = sorted(list(set([e['project_name'] for e in all_p.data if e.get('project_name')])))
except: 
    p_list = ["Allgemein"]

if not p_list: p_list = ["Allgemein"]
current_project = st.sidebar.selectbox("Baustelle wählen:", p_list)
new_p = st.sidebar.text_input("✨ Neue Baustelle anlegen:")
if new_p: current_project = new_p

# Budget-Anzeige in der Sidebar
res_costs = supabase.table("notes").select("cost_amount").eq("project_name", current_project).execute()
total_budget = sum([float(e['cost_amount']) for e in res_costs.data if e.get('cost_amount')])
st.sidebar.metric("Projekt-Ausgaben", f"{total_budget:.2f} €")

# --- SEITE 1: BOARD ---
if page == "📋 Baustellen-Board":
    st.subheader(f"Board: {current_project}")
    tab1, tab2 = st.tabs(["📋 Notizen & Fotos", "📅 Zeitplan"])
    
    with tab1:
        c_in, c_med = st.columns([2, 1])
        with c_in:
            with st.form("entry_form", clear_on_submit=True):
                txt = st.text_input("Titel / Beschreibung")
                c1, c2, c3 = st.columns(3)
                kat = c1.selectbox("Kat:", ["Notiz", "Aufgabe", "Material", "Wichtig"])
                prio = c2.selectbox("Status:", ["🟢 Ok", "🟡 In Arbeit", "🔴 Dringend"], index=1)
                cost = c3.number_input("Kosten €:", min_value=0.0)
                if st.form_submit_button("Speichern") and txt:
                    supabase.table("notes").insert({"content": txt, "category": kat, "status": prio, "project_name": current_project, "cost_amount": cost, "is_completed": False}).execute()
                    st.rerun()

        with c_med:
            img = st.camera_input("Foto", key="cam")
            if img:
                if st.session_state.get("last_img") != img.size:
                    with st.spinner("Upload..."):
                        fn = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"