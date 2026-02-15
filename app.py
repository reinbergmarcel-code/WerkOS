import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd

# =========================================================
# I. BACKEND - DIE UNANTASTBARE LOGIK-ZENTRALE
# =========================================================
class WerkOS_Backend:
    def __init__(self):
        try:
            self.db = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        except:
            st.error("Datenbank-Fehler")

    def get_data(self):
        return self.db.table("notes").select("*").execute().data

    def create_project(self, name):
        self.db.table("notes").insert({"content": "Start", "project_name": name, "category": "Notiz", "is_completed": False}).execute()

    def archive_project(self, name):
        self.db.table("notes").insert({"content": "PROJECT_ARCHIVED", "project_name": name, "category": "System", "is_completed": True}).execute()

    def delete_archive_marker(self, name):
        self.db.table("notes").delete().eq("project_name", name).eq("content", "PROJECT_ARCHIVED").execute()

    def update_note(self, note_id, new_content):
        self.db.table("notes").update({"content": new_content}).eq("id", note_id).execute()

    def complete_note(self, note_id):
        self.db.table("notes").update({"is_completed": True}).eq("id", note_id).execute()

    def delete_note(self, note_id):
        self.db.table("notes").delete().eq("id", note_id).execute()

backend = WerkOS_Backend()

# =========================================================
# II. FRONTEND - DAS REPARIERTE APP-INTERFACE (v2.45)
# =========================================================
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

# Minimales CSS NUR für die Karten-Farben, um nichts zu "zerschießen"
st.markdown("""
    <style>
    .card { padding: 15px; border-radius: 15px; margin-bottom: 10px; border: 1px solid #ddd; background: white; color: black; }
    .notiz { border-left: 10px solid #3498db; }
    .aufgabe { border-left: 10px solid #f1c40f; }
    .wichtig { border-left: 10px solid #e74c3c; }
    .material { border-left: 10px solid #95a5a6; }
    </style>
""", unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = "🏠 Home"
if 'edit_id' not in st.session_state: st.session_state.edit_id = None

st.title("WerkOS Pro")

# 1. PROJEKT-VERWALTUNG
all_data = backend.get_data()
all_projects = sorted(list(set([e['project_name'] for e in all_data if e.get('project_name')])))
archived_projects = list(set([e['project_name'] for e in all_data if e['content'] == "PROJECT_ARCHIVED"]))

c_sel, c_add = st.columns([3, 1])
with c_sel:
    show_arch = st.checkbox("Archiv anzeigen")
    curr_p = st.selectbox("📌 Projekt", [p for p in all_projects if p not in archived_projects] if not show_arch else all_projects)
with c_add:
    with st.popover("➕ Neu"):
        np = st.text_input("Name:")
        if st.button("Anlegen"):
            if np: backend.create_project(np); st.rerun()

is_archived = curr_p in archived_projects

# ARCHIV-LOGIK BUTTONS
if curr_p and curr_p != "Allgemein":
    if not is_archived:
        if st.button(f"📁 '{curr_p}' ARCHIVIEREN", use_container_width=True):
            backend.archive_project(curr_p); st.rerun()
    else:
        if st.button(f"🔓 '{curr_p}' REAKTIVIEREN", use_container_width=True):
            backend.delete_archive_marker(curr_p); st.rerun()

st.divider()

# 2. SEITEN-NAVIGATION
if st.session_state.page == "🏠 Home":
    col1, col2 = st.columns(2)
    if col1.button("📋 BOARD", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
    if col1.button("📦 LAGER", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    if col2.button("⏱️ ZEITEN", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()
    if col2.button("📊 STATS", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()

elif st.session_state.page == "📋 Board":
    if st.button("⬅️ ZURÜCK"): st.session_state.page = "🏠 Home"; st.rerun()
    
    if not is_archived:
        with st.expander("➕ NEUER EINTRAG"):
            audio_recorder(text="Sprachnotiz")
            st.camera_input("Foto")
            with st.form("new"):
                t = st.text_input("Inhalt")
                k = st.selectbox("Typ", ["Notiz", "Aufgabe", "Wichtig"])
                c = st.number_input("Kosten €", step=0.5)
                if st.form_submit_button("SPEICHERN"):
                    backend.db.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute(); st.rerun()

    # Board Anzeige
    items = [e for e in all_data if e['project_name'] == curr_p and not e['is_completed'] and e['content'] != "PROJECT_ARCHIVED"]
    for e in items:
        if st.session_state.edit_id == e['id']:
            with st.form(f"edit_{e['id']}"):
                nt = st.text_input("Ändern", value=e['content'])
                if st.form_submit_button("Sichern"):
                    backend.update_note(e['id'], nt); st.session_state.edit_id = None; st.rerun()
        else:
            st.markdown(f'<div class="card {e["category"].lower()}"><b>{e["category"]}</b><br>{e["content"]}<br><small>💰 {e.get("cost_amount",0)}€</small></div>', unsafe_allow_html=True)
            if not is_archived:
                b1, b2, b3 = st.columns(3)
                if b1.button("✅", key=f"d_{e['id']}"): backend.complete_note(e['id']); st.rerun()
                if b2.button("✏️", key=f"e_{e['id']}"): st.session_state.edit_id = e['id']; st.rerun()
                if b3.button("🗑️", key=f"x_{e['id']}"): backend.delete_note(e['id']); st.rerun()

elif st.session_state.page == "📦 Lager":
    if st.button("⬅️ ZURÜCK"): st.session_state.page = "🏠 Home"; st.rerun()
    m_data = backend.db.table("materials").select("*").execute().data
    t1, t2 = st.tabs(["📥 Inventur", "📤 Verbrauch"])
    with t1:
        with st.form("inv"):
            sel = st.selectbox("Material", [i['name'] for i in m_data])
            q = st.number_input("Bestand")
            if st.form_submit_button("Korrektur"):
                mid = next(i for i in m_data if i['name'] == sel)['id']
                backend.db.table("materials").update({"stock_quantity": q}).eq("id", mid).execute(); st.rerun()
    with t2:
        if not is_archived:
            with st.form("cons"):
                sel = st.selectbox("Material ", [i['name'] for i in m_data])
                q = st.number_input("Menge")
                if st.form_submit_button("Buchen"):
                    m = next(i for i in m_res if i['name'] == sel)
                    backend.db.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":m['price_per_unit']*q, "is_completed":False}).execute()
                    backend.db.table("materials").update({"stock_quantity": float(m['stock_quantity'])-q}).eq("id", m['id']).execute(); st.rerun()
    for m in m_data: st.write(f"📦 {m['name']}: {m['stock_quantity']}")
