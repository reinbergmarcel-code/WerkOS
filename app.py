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
def create_pdf(data, project_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"WerkOS Bericht: {project_name}", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 10, f"Erstellt am: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)

    for entry in data:
        pdf.set_font("Arial", "B", 11)
        header = f"{entry.get('status')} | {entry.get('category')} ({entry.get('created_at', '')[:10]})"
        pdf.cell(190, 8, header.encode('latin-1', 'replace').decode('latin-1'), ln=True)
        pdf.set_font("Arial", "", 11)
        content = entry.get('content', '')
        pdf.multi_cell(190, 7, content.encode('latin-1', 'replace').decode('latin-1'))
        if entry.get("checklist"):
            try:
                items = json.loads(entry["checklist"])
                for item, checked in items.items():
                    mark = "[X]" if checked else "[ ]"
                    pdf.cell(190, 6, f"  {mark} {item}".encode('latin-1', 'replace').decode('latin-1'), ln=True)
            except: pass
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
    return bytes(pdf.output())

st.set_page_config(page_title="WerkOS", page_icon="🏗️", layout="wide")
st.title("🏗️ WerkOS")

# --- 3. SIDEBAR: PROJEKT-MANAGEMENT ---
st.sidebar.header("📁 Projekt-Verwaltung")

# Bestehende Projekte laden
try:
    all_p = supabase.table("notes").select("project_name").execute()
    existing_projects = sorted(list(set([e['project_name'] for e in all_p.data if e.get('project_name')])))
except:
    existing_projects = []

if not existing_projects: existing_projects = ["Allgemein"]

current_project = st.sidebar.selectbox("Baustelle auswählen:", existing_projects)
new_p = st.sidebar.text_input("✨ Neue Baustelle anlegen:")
if new_p:
    current_project = new_p

st.sidebar.divider()
filter_kat = st.sidebar.multiselect("Filter Kategorien:", options=["Notiz", "Aufgabe", "Material", "Wichtig"], default=["Notiz", "Aufgabe", "Material", "Wichtig"])
show_archived = st.sidebar.checkbox("Archiv anzeigen")

# --- 4. EINGABE BEREICH ---
st.info(f"📍 Aktuelles Projekt: **{current_project}**")
with st.container():
    col_input, col_media = st.columns([2, 1])
    
    with col_input:
        with st.form("entry_form", clear_on_submit=True):
            st.write("### ⌨️ Neuer Eintrag")
            manual_text = st.text_input("Titel / Beschreibung")
            c1, c2 = st.columns(2)
            form_kat = c1.selectbox("Kategorie:", ["Notiz", "Aufgabe", "Material", "Wichtig"])
            form_prio = c2.selectbox("Dringlichkeit:", ["🟢 Ok", "🟡 In Arbeit", "🔴 Dringend"], index=1)
            material_items = st.text_area("Checkliste (Komma-getrennt)") if form_kat == "Material" else ""
            
            if st.form_submit_button("Speichern") and manual_text:
                checklist_data = {i.strip(): False for i in material_items.split(",") if i.strip()} if material_items else None
                supabase.table("notes").insert({
                    "content": manual_text, "category": form_kat, "status": form_prio,
                    "project_name": current_project,
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
            supabase.table("notes").insert({"content": "Foto", "category": "Notiz", "status": "🟡 In Arbeit", "project_name": current_project, "image_url": url, "is_completed": False}).execute()
            st.rerun()
        audio = audio_recorder(text="", icon_size="2x", key="aud")
        if audio:
            supabase.table("notes").insert({"content": speech_to_text(audio), "category": "Notiz", "status": "🟡 In Arbeit", "project_name": current_project, "is_completed": False}).execute()
            st.rerun()

st.divider()

# --- 5. DATEN ABRUFEN ---
st_filt = True if show_archived else False
query = supabase.table("notes").select("*").eq("is_completed", st_filt).eq("project_name", current_project).in_("category", filter_kat).order("created_at", desc=True)
res = query.execute()

def sort_priority(e):
    p_map = {"🔴 Dringend": 0, "🟡 In Arbeit": 1, "🟢 Ok": 2}
    return p_map.get(e.get('status'), 1)

sorted_data = sorted(res.data, key=sort_priority) if res.data else []

# PDF Download in Sidebar
if sorted_data:
    pdf_bytes = create_pdf(sorted_data, current_project)
    st.sidebar.download_button(label=f"📄 Bericht {current_project}", data=pdf_bytes, file_name=f"WerkOS_{current_project}.pdf", mime="application/pdf")

# --- 6. DARSTELLUNG ---
for entry in sorted_data:
    eid = entry['id']
    with st.container():
        st.markdown(f"### {entry.get('status')} | {entry.get('category')}")
        st.write(f"**{entry['content']}**")
        if entry.get("checklist"):
            try:
                items = json.loads(entry["checklist"])
                for item, checked in items.items():
                    if st.checkbox(item, value=checked, key=f"c_{eid}_{item}"):
                        items[item] = not checked
                        supabase.table("notes").update({"checklist": json.dumps(items)}).eq("id", eid).execute()
                        st.rerun()
            except: pass
        if entry.get("image_url"): st.image(entry["image_url"], width=300)
        st.caption(f"📅 {entry.get('created_at', '')[:16]}")
        
        b1, b2, b3, _ = st.columns([0.1, 0.1, 0.1, 0.7])
        if b1.button("✅", key=f"t_{eid}"):
            supabase.table("notes").update({"is_completed": not st_filt}).eq("id", eid).execute()
            st.rerun()
        if b2.button("📝", key=f"e_{eid}"):
            st.session_state[f"ed_{eid}"] = not st.session_state.get(f"ed_{eid}", False)
        if b3.button("🗑️", key=f"d_{eid}"):
            supabase.table("notes").delete().eq("id", eid).execute()
            st.rerun()

        if st.session_state.get(f"ed_{eid}", False):
            new_s = st.radio("Status:", ["🟢 Ok", "🟡 In Arbeit", "🔴 Dringend"], index=sort_priority(entry), horizontal=True, key=f"r_{eid}")
            if st.button("Speichern", key=f"s_{eid}"):
                supabase.table("notes").update({"status": new_s}).eq("id", eid).execute()
                st.session_state[f"ed_{eid}"] = False
                st.rerun()
        st.divider()