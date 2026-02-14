import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import json
from fpdf import FPDF

# --- 1. ZUGANGSDATEN ---
# Tipp: Nutze st.secrets für maximale Sicherheit auf GitHub!
SUPABASE_URL = "https://sjviyysbjozculvslrdy.supabase.co"
SUPABASE_KEY = "sb_publishable_Mlm0V-_soOU-G78EYcOWaw_-0we6oZw"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def speech_to_text(audio_bytes):
    return "Sprachaufnahme vom " + datetime.datetime.now().strftime('%H:%M')

# --- 2. PDF EXPORT FUNKTION ---
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
        cost = f" | {entry.get('cost_amount', 0)} EUR" if entry.get('cost_amount') else ""
        header = f"{entry.get('status')} | {entry.get('category')}{cost} ({entry.get('created_at', '')[:10]})"
        pdf.cell(190, 8, header.encode('latin-1', 'replace').decode('latin-1'), ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(190, 7, entry.get('content', '').encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(5)
    return bytes(pdf.output())

st.set_page_config(page_title="WerkOS v1.5.2", page_icon="🏗️", layout="wide")
st.title("🏗️ WerkOS")

# --- 3. SIDEBAR: PROJEKT & BUDGET ---
st.sidebar.header("📁 Projekt-Verwaltung")
try:
    all_p = supabase.table("notes").select("project_name").execute()
    existing_projects = sorted(list(set([e['project_name'] for e in all_p.data if e.get('project_name')])))
except: existing_projects = ["Allgemein"]

current_project = st.sidebar.selectbox("Baustelle wählen:", existing_projects)
new_p = st.sidebar.text_input("✨ Neue Baustelle anlegen:")
if new_p: current_project = new_p

# Kosten berechnen für Sidebar
res_costs = supabase.table("notes").select("cost_amount").eq("project_name", current_project).execute()
total_budget = sum([float(e['cost_amount']) for e in res_costs.data if e.get('cost_amount')])
st.sidebar.metric("Projekt-Ausgaben", f"{total_budget:.2f} €")

st.sidebar.divider()
filter_kat = st.sidebar.multiselect("Filter:", ["Notiz", "Aufgabe", "Material", "Wichtig"], default=["Notiz", "Aufgabe", "Material", "Wichtig"])
show_archived = st.sidebar.checkbox("Archiv anzeigen")

# --- 4. TABS: DASHBOARD vs. KALENDER ---
tab_main, tab_cal = st.tabs(["📋 Board", "📅 Termin-Planer"])

with tab_main:
    st.info(f"📍 Aktuelles Projekt: **{current_project}**")
    col_input, col_media = st.columns([2, 1])

    with col_input:
        with st.form("entry_form", clear_on_submit=True):
            manual_text = st.text_input("Titel / Beschreibung")
            c1, c2, c3 = st.columns(3)
            form_kat = c1.selectbox("Kategorie:", ["Notiz", "Aufgabe", "Material", "Wichtig"])
            form_prio = c2.selectbox("Dringlichkeit:", ["🟢 Ok", "🟡 In Arbeit", "🔴 Dringend"], index=1)
            form_cost = c3.number_input("Kosten (€):", min_value=0.0, step=1.0)
            
            material_items = st.text_area("Checkliste (nur Material, mit Komma trennen)") if form_kat == "Material" else ""
            
            if st.form_submit_button("Speichern") and manual_text:
                checklist_data = {i.strip(): False for i in material_items.split(",") if i.strip()} if material_items else None
                supabase.table("notes").insert({
                    "content": manual_text, "category": form_kat, "status": form_prio,
                    "project_name": current_project, "cost_amount": form_cost,
                    "checklist": json.dumps(checklist_data) if checklist_data else None, "is_completed": False
                }).execute()
                st.rerun()

    with col_media:
        st.write("### 📸 Foto / 🎤 Audio")
        img_file = st.camera_input("Foto aufnehmen", key="cam")
        
        if img_file:
            img_hash = f"img_{img_file.size}" 
            if st.session_state.get("last_uploaded_img") != img_hash:
                with st.spinner("Foto wird gespeichert..."):
                    try:
                        fn = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        supabase.storage.from_("werkos_fotos").upload(fn, img_file.getvalue())
                        url = supabase.storage.from_("werkos_fotos").get_public_url(fn)
                        supabase.table("notes").insert({
                            "content": "Foto-Notiz", "category": "Notiz", "status": "🟡 In Arbeit", 
                            "project_name": current_project, "image_url": url, "is_completed": False
                        }).execute()
                        st.session_state["last_uploaded_img"] = img_hash
                        st.success("Foto gespeichert!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Upload-Fehler: {e}")
        
        audio = audio_recorder(text="", icon_size="2x", key="aud")
        if audio:
            with st.spinner("Sprachnotiz wird gespeichert..."):
                supabase.table("notes").insert({
                    "content": speech_to_text(audio), "category": "Notiz", 
                    "status": "🟡 In Arbeit", "project_name": current_project, "is_completed": False
                }).execute()