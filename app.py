import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import pandas as pd
import uuid

# 1. DATENBANK VERBINDUNG
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Verbindung zu Supabase fehlgeschlagen: {e}")
    st.stop()

# 2. SEITEN-SETUP & AUTH-LOGIK
st.set_page_config(page_title="WerkOS Pro", layout="wide")

if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state: 
    st.session_state.page = "🏠 Dashboard"

# Login-Funktion
def login():
    st.title("🔐 WerkOS Pro Login")
    with st.form("login_form"):
        email = st.text_input("E-Mail")
        password = st.text_input("Passwort", type="password")
        if st.form_submit_button("Anmelden", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.success("Erfolgreich eingeloggt!")
                st.rerun()
            except Exception as e:
                st.error("Login fehlgeschlagen. Bitte Daten prüfen.")

# Auth-Check
if st.session_state.user is None:
    login()
    st.stop()

# --- AB HIER: EINGELOGGTER BEREICH ---

# 3. SIDEBAR NAVIGATION
with st.sidebar:
    st.title("WerkOS Pro")
    st.write(f"👤 {st.session_state.user.email}")
    st.divider()
    if st.button("🏠 Dashboard", use_container_width=True): st.session_state.page = "🏠 Dashboard"
    if st.button("🏗️ Projekte", use_container_width=True): st.session_state.page = "🏗️ Projekte"
    if st.button("📋 Board / Doku", use_container_width=True): st.session_state.page = "📋 Board"
    if st.button("⏱️ Erfassung", use_container_width=True): st.session_state.page = "⏱️ Erfassung"
    if st.button("📊 Stats", use_container_width=True): st.session_state.page = "📊 Stats"
    
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

# --- SEITE: DASHBOARD ---
if st.session_state.page == "🏠 Dashboard":
    st.header("Willkommen bei WerkOS Pro")
    st.info("Nutze die Sidebar, um Projekte zu verwalten oder Zeiten zu erfassen.")
    
# --- SEITE: PROJEKTE ---
elif st.session_state.page == "🏗️ Projekte":
    st.header("🏗️ Projekt-Verwaltung")
    with st.expander("➕ Neue Baustelle anlegen", expanded=True):
        with st.form("new_project_form", clear_on_submit=True):
            p_name = st.text_input("Projekt Name")
            p_client = st.text_input("Kunde")
            p_address = st.text_input("Adresse")
            if st.form_submit_button("Projekt anlegen"):
                if p_name:
                    supabase.table("projects").insert({
                        "project_name": p_name, "client_name": p_client, 
                        "address": p_address, "user_id": st.session_state.user.id
                    }).execute()
                    st.success(f"Projekt '{p_name}' erstellt!")
                    st.rerun()

    st.divider()
    res = supabase.table("projects").select("*").order("created_at", desc=True).execute()
    for p in (res.data if res.data else []):
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(p['project_name'])
                st.caption(f"📍 {p['address']} | Kunde: {p['client_name']}")
            with col2:
                if st.button("🗑️", key=f"del_p_{p['id']}"):
                    supabase.table("projects").delete().eq("id", p['id']).execute()
                    st.rerun()

# --- SEITE: BOARD ---
elif st.session_state.page == "📋 Board":
    st.header("📋 Baustellen-Doku")
    res_n = supabase.table("notes").select("*").execute()
    all_notes = res_n.data if res_n.data else []
    
    projects = sorted(list(set([n['project_name'] for n in all_notes]))) if all_notes else []
    selected_p = st.selectbox("📍 Filter nach Projekt", ["Alle"] + projects)

    with st.expander("📸 Foto-Notiz aufnehmen", expanded=False):
        img_file = st.camera_input("Foto")
        with st.form("board_form", clear_on_submit=True):
            m_content = st.text_input("Notiz")
            m_project = st.selectbox("Projekt", options=projects if projects else ["Allgemein"])
            if st.form_submit_button("Speichern"):
                file_url = None
                if img_file:
                    # Diese Zeilen MÜSSEN eingerückt sein (4 Leerzeichen/1 Tab)
                    file_name = f"{uuid.uuid4()}.jpg"
                    supabase.storage.from_("werkos_media").upload(file_name, img_file.getvalue())
                    file_url = supabase.storage.from_("werkos_media").get_public_url(file_name)
                
                # Dieser Teil muss wieder auf der Ebene des 'if img_file' stehen
                supabase.table("notes").insert({
                    "content": m_content, 
                    "project_name": m_project,
                    "image_url": file_url, 
                    "user_id": st.session_state.user.id, 
                    "category": "Notiz"
                }).execute()
                st.rerun()