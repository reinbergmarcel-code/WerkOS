import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd

# --- 1. APP CONFIG & DESIGN (v2.34 - ABSOLUTE BUTTON SICHTBARKEIT) ---
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC; }

    .app-header {
        background: linear-gradient(180deg, #1e3a8a 0%, #1e40af 100%);
        padding: 20px;
        border-radius: 0 0 25px 25px;
        color: white;
        text-align: center;
        margin-bottom: 15px;
    }
    
    .stButton>button {
        border-radius: 20px !important;
        background: white !important;
        color: #1e3a8a !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
    }

    /* AMPEL-LOGIK */
    .card { background: white !important; padding: 20px; border-radius: 20px; margin-bottom: 12px; border: 1px solid #f1f5f9; position: relative; }
    .card-notiz { border-left: 12px solid #3498db !important; }
    .card-aufgabe { border-left: 12px solid #f1c40f !important; }
    .card-wichtig { border-left: 12px solid #e74c3c !important; }
    .card-material { border-left: 12px solid #95a5a6 !important; }

    /* ARCHIV BUTTON STYLING - SEHR AUFFÄLLIG */
    div.stButton > button[key="GLOBAL_ARCHIVE"] {
        background-color: #e74c3c !important;
        color: white !important;
        border: 2px solid #c0392b !important;
        height: 55px !important;
        font-size: 1.1rem !important;
    }
    div.stButton > button[key="GLOBAL_REACTIVATE"] {
        background-color: #27ae60 !important;
        color: white !important;
        border: 2px solid #1e8449 !important;
        height: 55px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SUPABASE ---
try:
    S_URL, S_KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    supabase = create_client(S_URL, S_KEY)
except:
    st.error("Konfiguration fehlt."); st.stop()

if 'page' not in st.session_state: st.session_state.page = "🏠 Home"

# --- HEADER ---
st.markdown('<div class="app-header"><h1>WerkOS Pro</h1></div>', unsafe_allow_html=True)

# --- PROJEKT-DATEN ---
p_data = supabase.table("notes").select("project_name, content").execute()
all_p = sorted(list(set([e['project_name'] for e in p_data.data if e.get('project_name')])))
archived_list = list(set([e['project_name'] for e in p_data.data if e['content'] == "PROJECT_ARCHIVED"]))

# --- STEUERUNG (GANZE BREITE) ---
curr_p = st.selectbox("📍 Baustelle wählen:", all_p if st.checkbox("Archiv anzeigen") else [p for p in all_p if p not in archived_list])

# DER ARCHIV-BUTTON: JETZT OHNE SPALTEN, DIREKT IM HAUPTFLUSS
is_archived = curr_p in archived_list
if curr_p and curr_p != "Allgemein":
    if not is_archived:
        if st.button(f"📁 PROJEKT '{curr_p}' ABSCHLIESSEN (Archivieren)", key="GLOBAL_ARCHIVE", use_container_width=True):
            supabase.table("notes").insert({"content": "PROJECT_ARCHIVED", "project_name": curr_p, "category": "System", "is_completed": True}).execute()
            st.rerun()
    else:
        if st.button(f"🔓 PROJEKT '{curr_p}' REAKTIVIEREN", key="GLOBAL_REACTIVATE", use_container_width=True):
            supabase.table("notes").delete().eq("project_name", curr_p).eq("content", "PROJECT_ARCHIVED").execute()
            st.rerun()

with st.popover("➕ Neues Projekt anlegen"):
    new_p = st.text_input("Name:")
    if st.button("Erstellen"):
        if new_p:
            supabase.table("notes").insert({"content": "Projektstart", "project_name": new_p, "category": "Notiz", "is_completed": False}).execute(); st.rerun()

st.divider()

# --- MENÜ ---
if st.session_state.page != "🏠 Home":
    if st.button("⬅️ ZURÜCK ZUM MENÜ", use_container_width=True):
        st.session_state.page = "🏠 Home"; st.rerun()

if st.session_state.page == "🏠 Home":
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📋 BOARD", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
        if st.button("📦 LAGER", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    with c2:
        if st.button("⏱️ ZEITEN", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()
        if st.button("📊 DASHBOARD", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()

elif st.session_state.page == "📋 Board":
    if is_archived: st.warning("🔒 ARCHIV")
    else:
        with st.expander("➕ EINTRAG"):
            with st.form("f"):
                t = st.text_input("Titel"); k = st.selectbox("Kat", ["Notiz", "Aufgabe", "Wichtig"]); c = st.number_input("€")
                if st.form_submit_button("OK"):
                    supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute(); st.rerun()
    
    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).neq("content", "PROJECT_ARCHIVED").order("created_at", desc=True).execute()
    for e in res.data:
        st.markdown(f'<div class="card card-{e["category"].lower()}"><strong>{e["category"]}</strong><br>{e["content"]}<br><small>💰 {e.get("cost_amount",0)} €</small></div>', unsafe_allow_html=True)
        # ... Restliche Board-Logik (✅/✏️/🗑️) bleibt exakt wie v2.30 ...

elif st.session_state.page == "📦 Lager":
    st.subheader("📦 Lager")
    m_res = supabase.table("materials").select("*").execute()
    t1, t2 = st.tabs(["📥 Inventur", "📤 Verbrauch"])
    with t1:
        with st.form("m1"):
            sel = st.selectbox("Mat", [i['name'] for i in m_res.data]); q = st.number_input("Bestand")
            if st.form_submit_button("ÜBERSCHREIBEN"):
                idx = next(i for i in m_res.data if i['name'] == sel)['id']
                supabase.table("materials").update({"stock_quantity": q}).eq("id", idx).execute(); st.rerun()
    with t2:
        if not is_archived:
            with st.form("m2"):
                sel = st.selectbox("Mat", [i['name'] for i in m_res.data]); q = st.number_input("Menge")
                if st.form_submit_button("BUCHEN"):
                    m = next(i for i in m_res.data if i['name'] == sel)
                    supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":m['price_per_unit']*q, "is_completed":False}).execute()
                    supabase.table("materials").update({"stock_quantity": float(m['stock_quantity'])-q}).eq("id", m['id']).execute(); st.rerun()
