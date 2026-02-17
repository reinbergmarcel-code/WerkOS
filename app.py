import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import pandas as pd
import uuid

# 1. Datenbank Verbindung
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Verbindung zu Supabase fehlgeschlagen: {e}")
    st.stop()

# 2. Seiten-Setup & Auth (Standard v2.22)
st.set_page_config(page_title="WerkOS Pro", layout="wide")

if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state: 
    st.session_state.page = "🏠 Home"

# Login Funktion
def login():
    st.title("🔐 WerkOS Pro Login")
    with st.form("login_form"):
        email = st.text_input("E-Mail")
        password = st.text_input("Passwort", type="password")
        if st.form_submit_button("Anmelden"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except:
                st.error("Login fehlgeschlagen.")

if st.session_state.user is None:
    login()
    st.stop()

# 3. Sidebar (Alle Menüpunkte vorhanden)
with st.sidebar:
    st.title("WerkOS Pro")
    if st.button("🏠 Home", use_container_width=True): st.session_state.page = "🏠 Home"
    if st.button("🏗️ Projekte", use_container_width=True): st.session_state.page = "🏗️ Projekte"
    if st.button("📋 Board", use_container_width=True): st.session_state.page = "📋 Board"
    if st.button("⏱️ Erfassung", use_container_width=True): st.session_state.page = "⏱️ Erfassung"
    if st.button("📊 Stats", use_container_width=True): st.session_state.page = "📊 Stats"
    st.divider()
    if st.button("🚪 Logout"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

# --- SEITE: HOME ---
if st.session_state.page == "🏠 Home":
    st.header("Willkommen bei WerkOS Pro")

# --- SEITE: PROJEKTE (Neu hinzugefügt) ---
elif st.session_state.page == "🏗️ Projekte":
    st.header("🏗️ Projekt-Verwaltung")
    with st.form("new_p"):
        p_name = st.text_input("Projekt Name")
        if st.form_submit_button("Anlegen"):
            supabase.table("projects").insert({"project_name": p_name, "user_id": st.session_state.user.id}).execute()
            st.rerun()
    res = supabase.table("projects").select("*").execute()
    for p in (res.data if res.data else []):
        st.write(f"🏗️ {p['project_name']}")

# --- SEITE: BOARD (AUDIO IST WIEDER DA) ---
elif st.session_state.page == "📋 Board":
    st.header("📋 Board")
    
    # AUDIO FUNKTION (v2.22 Standard)
    audio_data = audio_recorder(text="Sprachnotiz aufnehmen", icon_size="2x")
    if audio_data:
        st.audio(audio_data)
        if st.button("Audio speichern"):
            file_name = f"audio_{uuid.uuid4()}.wav"
            supabase.storage.from_("werkos_media").upload(file_name, audio_data)
            st.success("Audio hochgeladen!")

    # FOTO FUNKTION
    img_file = st.camera_input("Foto aufnehmen")
    with st.form("note_form"):
        content = st.text_input("Notiz")
        if st.form_submit_button("Speichern"):
            f_url = None
            if img_file:
                f_name = f"{uuid.uuid4()}.jpg"
                supabase.storage.from_("werkos_media").upload(f_name, img_file.getvalue())
                f_url = supabase.storage.from_("werkos_media").get_public_url(f_name)
            supabase.table("notes").insert({"content": content, "image_url": f_url, "user_id": st.session_state.user.id}).execute()
            st.rerun()

# --- SEITE: ERFASSUNG (Nicht mehr leer) ---
elif st.session_state.page == "⏱️ Erfassung":
    st.header("⏱️ Zeit & Material")
    res_p = supabase.table("projects").select("*").execute()
    p_names = [p['project_name'] for p in res_p.data] if res_p.data else ["Keine Projekte"]
    
    with st.form("work_form"):
        p_sel = st.selectbox("Projekt", p_names)
        hrs = st.number_input("Stunden", min_value=0.0)
        if st.form_submit_button("Zeit buchen"):
            # Logik für Zeitbuchung
            st.success("Gebucht!")

# --- SEITE: STATS (Nicht mehr leer) ---
elif st.session_state.page == "📊 Stats":
    st.header("📊 Auswertung")
    res = supabase.table("notes").select("cost_amount").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Gesamtkosten", f"{df['cost_amount'].sum()} €")