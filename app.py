import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import json
from fpdf import FPDF

# --- 1. ZUGANGSDATEN ---
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

st.set_page_config(page_title="WerkOS v1.5", page_icon="🏗️", layout="wide")
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
    # --- EINGABE-BEREICH ---
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
        img_file = st.camera_input("Foto", key="cam")
        if img_file:
            fn = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            supabase.storage.from_("werkos_fotos").upload(fn, img_file.getvalue())
            url = supabase.storage.from_("werkos_fotos").get_public_url(fn)
            supabase.table("notes").insert({"content": "Foto-Notiz", "category": "Notiz", "status": "🟡 In Arbeit", "project_name": current_project, "image_url": url, "is_completed": False}).execute()
            st.rerun()
        
        audio = audio_recorder(text="", icon_size="2x", key="aud")
        if audio:
            supabase.table("notes").insert({"content": speech_to_text(audio), "category": "Notiz", "status": "🟡 In Arbeit", "project_name": current_project, "is_completed": False}).execute()
            st.rerun()

    st.divider()

    # --- DATEN ANZEIGEN ---
    st_filt = True if show_archived else False
    res = supabase.table("notes").select("*").eq("is_completed", st_filt).eq("project_name", current_project).in_("category", filter_kat).order("created_at", desc=True).execute()
    
    for entry in res.data:
        eid = entry['id']
        with st.container():
            col_text, col_btns = st.columns([0.8, 0.2])
            with col_text:
                st.markdown(f"### {entry.get('status')} | {entry.get('category')} ({entry.get('cost_amount', 0)} €)")
                st.write(f"**{entry['content']}**")
            
            if entry.get("image_url"): st.image(entry["image_url"], width=250)
            
            # Buttons unter dem Eintrag
            b1, b2, b3, _ = st.columns([0.1, 0.1, 0.1, 0.7])
            if b1.button("✅" if not st_filt else "↩️", key=f"t_{eid}"):
                supabase.table("notes").update({"is_completed": not st_filt}).eq("id", eid).execute()
                st.rerun()
            if b2.button("📝", key=f"e_{eid}"):
                st.session_state[f"ed_{eid}"] = not st.session_state.get(f"ed_{eid}", False)
            if b3.button("🗑️", key=f"d_{eid}"):
                supabase.table("notes").delete().eq("id", eid).execute()
                st.rerun()

            # Bearbeitungs-Modus
            if st.session_state.get(f"ed_{eid}", False):
                new_s = st.radio("Status ändern:", ["🟢 Ok", "🟡 In Arbeit", "🔴 Dringend"], key=f"r_{eid}", horizontal=True)
                new_c = st.number_input("Kosten korrigieren:", value=float(entry.get('cost_amount', 0)), key=f"cost_{eid}")
                if st.button("Update Speichern", key=f"s_{eid}"):
                    supabase.table("notes").update({"status": new_s, "cost_amount": new_c}).eq("id", eid).execute()
                    st.session_state[f"ed_{eid}"] = False
                    st.rerun()
            st.divider()

with tab_cal:
    st.subheader("📅 Chronologischer Zeitplan")
    # Nur wichtige Dinge für den Kalender
    cal_res = supabase.table("notes").select("*").eq("project_name", current_project).neq("category", "Notiz").order("created_at", desc=False).execute()
    if cal_res.data:
        for e in cal_res.data:
            done_mark = "✅" if e['is_completed'] else "⏳"
            st.write(f"**{e['created_at'][:10]}** | {done_mark} {e['category']}: {e['content']}")
    else:
        st.write("Noch keine geplanten Aufgaben hinterlegt.")

# --- PDF EXPORT (SIDEBAR) ---
if res.data:
    pdf_bytes = create_pdf(res.data, current_project, total_budget)
    st.sidebar.download_button(label=f"📄 Bericht {current_project}", data=pdf_bytes, file_name=f"WerkOS_{current_project}.pdf", mime="application/pdf")