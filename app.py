import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
from fpdf import FPDF
import pandas as pd

# --- 1. APP CONFIG & STYLE ---
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; background-color: #F4F7FB; }
    
    .app-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 15px;
        border-radius: 0 0 20px 20px;
        color: white;
        text-align: center;
        margin-bottom: 15px;
    }
    
    /* Zwingt Spalten nebeneinander, egal wie schmal das Handy ist */
    [data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0px !important;
    }

    .card {
        background: white;
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.03);
        border-left: 5px solid #3b82f6;
    }
    
    .stButton>button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        width: 100% !important;
        padding: 0.5rem 0px !important;
    }

    header {visibility: hidden;}
    footer {visibility: hidden;}

    div.stButton > button[key^="d_"] { background-color: #2ecc71 !important; color: white !important; }
    div.stButton > button[key^="e_"] { background-color: #f1c40f !important; color: black !important; }
    div.stButton > button[key^="x_"] { background-color: #e74c3c !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ZUGANG ---
try:
    S_URL, S_KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
except:
    S_URL = st.sidebar.text_input("URL", value="https://sjviyysbjozculvslrdy.supabase.co")
    S_KEY = st.sidebar.text_input("Key", type="password")

if S_URL and S_KEY:
    supabase = create_client(S_URL, S_KEY)
else:
    st.stop()

# --- 3. SESSION STATE ---
if 'page' not in st.session_state: st.session_state.page = "🏠 Home"
if 'edit_id' not in st.session_state: st.session_state.edit_id = None

# --- HEADER ---
st.markdown("""<div class="app-header"><h1>🏗️ WerkOS Pro</h1></div>""", unsafe_allow_html=True)

# --- NAVIGATION (ROBUSTE REIHE) ---
nav = st.columns(5)
with nav[0]: 
    if st.button("🏠", key="n1"): st.session_state.page = "🏠 Home"; st.rerun()
with nav[1]: 
    if st.button("📊", key="n2"): st.session_state.page = "📊 Dashboard"; st.rerun()
with nav[2]: 
    if st.button("📋", key="n3"): st.session_state.page = "📋 Board"; st.rerun()
with nav[3]: 
    if st.button("📦", key="n4"): st.session_state.page = "📦 Lager"; st.rerun()
with nav[4]: 
    if st.button("⏱️", key="n5"): st.session_state.page = "⏱️ Zeiten"; st.rerun()

st.divider()

# Projektwahl & Plus-Button
p_res = supabase.table("notes").select("project_name").execute()
p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))

cp1, cp2 = st.columns([4,1])
with cp1:
    curr_p = st.selectbox("📍 Projekt:", p_list if p_list else ["Allgemein"], key="p_fix")
with cp2:
    with st.popover("➕"):
        new_p = st.text_input("Projektname:")
        if st.button("OK"):
            if new_p:
                supabase.table("notes").insert({"content": "Start", "project_name": new_p, "category": "Notiz", "is_completed": False}).execute()
                st.rerun()

# --- SEITEN LOGIK ---
if st.session_state.page == "🏠 Home":
    st.markdown("### Hauptmenü")
    if st.button("📊 DASHBOARD", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()
    if st.button("📋 BOARD", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
    if st.button("📦 LAGER", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    if st.button("⏱️ ZEITEN", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()

elif st.session_state.page == "📊 Dashboard":
    st.markdown(f"### Dashboard: {curr_p}")
    res = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Kosten", f"{df['cost_amount'].sum():.2f} €")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())

elif st.session_state.page == "📋 Board":
    with st.expander("➕ NEUER EINTRAG"):
        with st.form("new_b"):
            t = st.text_input("Titel")
            k = st.selectbox("Kat", ["Aufgabe", "Notiz", "Wichtig"])
            c = st.number_input("Kosten €", min_value=0.0)
            if st.form_submit_button("SPEICHERN"):
                supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute()
                st.rerun()
    
    res = supabase.table("notes").select("*").
