import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import pandas as pd
import uuid

# 1. DATENBANK VERBINDUNG (Direkt via Secrets)
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Verbindung zu Supabase fehlgeschlagen: {e}")
    st.stop()

# 2. SEITEN-SETUP
st.set_page_config(page_title="WerkOS Pro", layout="wide")

if 'page' not in st.session_state: 
    st.session_state.page = "🏠 Home"

# 3. SIDEBAR NAVIGATION (Ohne Login-Zwang)
with st.sidebar:
    st.title("8Count Athletics / WerkOS")
    st.divider()
    if st.button("🏠 Home", use_container_width=True): st.session_state.page = "🏠 Home"
    if st.button("🏗️ Projekte", use_container_width=True): st.session_state.page = "🏗️ Projekte"
    if st.button("📋 Board / Doku", use_container_width=True): st.session_state.page = "📋 Board"
    if st.button("⏱️ Erfassung", use_container_width=True): st.session_state.page = "⏱️ Erfassung"
    if st.button("📊 Stats", use_container_width=True): st.session_state.page = "📊 Stats"
    st.divider()
    st.caption("v2.22 Reference Standard (Restored)")

# --- SEITE: HOME ---
if st.session_state.page == "🏠 Home":
    st.header("🏠 Willkommen bei WerkOS Pro")
    st.write("Wähle eine Funktion in der Sidebar aus.")

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
                        "project_name": p_name, 
                        "client_name": p_client, 
                        "address": p_address
                    }).execute()
                    st.success(f"Projekt '{p_name}' erstellt!")
                    st.rerun()

    st.divider()
    res = supabase.table("projects").select("*").order("created_at", desc=True).execute()
    projs = res.data if res.data else []
    for p in projs:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.subheader(p['project_name'])
                st.write(f"📍 {p['address']} | Kunde: {p['client_name']}")
            with col2:
                if st.button("🗑️", key=f"del_p_{p['id']}"):
                    supabase.table("projects").delete().eq("id", p['id']).execute()
                    st.rerun()

# --- SEITE: BOARD (Inkl. AUDIO & FOTO) ---
elif st.session_state.page == "📋 Board":
    st.header("📋 Baustellen-Dokumentation")
    
    # 1. Audio Aufnahme
    st.subheader("🎤 Sprachnotiz")
    audio_bytes = audio_recorder(text="Klicken zum Aufnehmen", icon_size="2x")
    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")
        if st.button("Audio-Notiz speichern"):
            file_name = f"audio_{uuid.uuid4()}.wav"
            supabase.storage.from_("werkos_media").upload(file_name, audio_bytes)
            audio_url = supabase.storage.from_("werkos_media").get_public_url(file_name)
            supabase.table("notes").insert({
                "content": "Sprachnotiz", "image_url": audio_url, "category": "Audio"
            }).execute()
            st.success("Audio gespeichert!")

    st.divider()

    # 2. Foto & Text
    with st.expander("📸 Neues Foto / Notiz"):
        img_file = st.camera_input("Foto")
        with st.form("note_form", clear_on_submit=True):
            m_content = st.text_input("Notiz-Text")
            res_p = supabase.table("projects").select("project_name").execute()
            p_list = [p['project_name'] for p in res_p.data] if res_p.data else ["Allgemein"]
            m_project = st.selectbox("Projekt", options=p_list)
            
            if st.form_submit_button("Speichern"):
                file_url = None
                if img_file:
                    f_name = f"{uuid.uuid4()}.jpg"
                    supabase.storage.from_("werkos_media").upload(f_name, img_file.getvalue())
                    file_url = supabase.storage.from_("werkos_media").get_public_url(f_name)
                supabase.table("notes").insert({
                    "content": m_content, "project_name": m_project,
                    "image_url": file_url, "category": "Notiz"
                }).execute()
                st.rerun()

    # Anzeige
    res_n = supabase.table("notes").select("*").order("created_at", desc=True).execute()
    for n in (res_n.data if res_n.data else []):
        with st.container(border=True):
            st.write(f"**{n.get('project_name', 'Allgemein')}** - {n['created_at'][:10]}")
            st.write(n['content'])
            if n.get('image_url'):
                if ".wav" in n['image_url']: st.audio(n['image_url'])
                else: st.image(n['image_url'], width=300)

# --- SEITE: ERFASSUNG ---
elif st.session_state.page == "⏱️ Erfassung":
    st.header("⏱️ Zeit & Material")
    res_p = supabase.table("projects").select("id, project_name").execute()
    projs = res_p.data if res_p.data else []
    
    if not projs:
        st.warning("Bitte erst ein Projekt anlegen.")
    else:
        p_options = {p['project_name']: p['id'] for p in projs}
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🕒 Zeit")
            with st.form("time_f"):
                p_sel = st.selectbox("Projekt", options=list(p_options.keys()))
                worker = st.text_input("Mitarbeiter")
                hrs = st.number_input("Stunden", min_value=0.0, step=0.5)
                if st.form_submit_button("Buchen"):
                    supabase.table("work_hours").insert({
                        "project_id": p_options[p_sel], "worker_name": worker, "hours": hrs
                    }).execute()
                    st.success("Zeit gebucht!")
        with col2:
            st.subheader("🧱 Material")
            with st.form("mat_f"):
                p_sel_m = st.selectbox("Projekt", options=list(p_options.keys()))
                item = st.text_input("Material")
                cost = st.number_input("Kosten (€)", min_value=0.0)
                if st.form_submit_button("Erfassen"):
                    supabase.table("notes").insert({
                        "content": f"Material: {item}", "project_name": p_sel_m,
                        "cost_amount": cost, "category": "Material"
                    }).execute()
                    st.success("Material erfasst!")

# --- SEITE: STATS ---
elif st.session_state.page == "📊 Stats":
    st.header("📊 Auswertung")
    res_n = supabase.table("notes").select("cost_amount").execute()
    if res_n.data:
        df = pd.DataFrame(res_n.data)
        st.metric("Materialkosten Gesamt", f"{df['cost_amount'].sum():,.2f} €")
    else:
        st.write("Keine Kostendaten vorhanden.")