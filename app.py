import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
from fpdf import FPDF
import pandas as pd

# --- 1. APP CONFIG & ULTIMATE STYLING ---
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; background-color: #F4F7FB; }
    
    .app-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 20px;
        border-radius: 0 0 25px 25px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .stButton>button {
        border-radius: 18px !important;
        height: 4rem !important;
        font-size: 1rem !important;
        background: white !important;
        color: #1e3a8a !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
    }

    .card {
        background: white;
        padding: 20px;
        border-radius: 20px;
        margin-bottom: 15px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.03);
        border-left: 6px solid #3b82f6;
    }
    
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Spezifische Button-Farben */
    div.stButton > button[key^="d_"] { background-color: #2ecc71 !important; color: white !important; height: 3rem !important; }
    div.stButton > button[key^="e_"] { background-color: #f1c40f !important; color: black !important; height: 3rem !important; }
    div.stButton > button[key^="x_"] { background-color: #e74c3c !important; color: white !important; height: 3rem !important; }

    /* NEU: Fixierte Bottom Navigation */
    .nav-bar {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: white;
        display: flex;
        justify-content: space-around;
        padding: 10px 0;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
        z-index: 1000;
    }
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
st.markdown("""<div class="app-header"><h1>🏗️ WerkOS Pro</h1><p>Digitales Baustellenmanagement</p></div>""", unsafe_allow_html=True)

p_res = supabase.table("notes").select("project_name").execute()
p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))

c_top1, c_top2 = st.columns([3,1])
with c_top1:
    curr_p = st.selectbox("📍 Baustelle:", p_list if p_list else ["Allgemein"])
with c_top2:
    with st.popover("➕ Projekt"):
        new_p = st.text_input("Name:")
        if st.button("Anlegen"):
            if new_p:
                supabase.table("notes").insert({"content": "Start", "project_name": new_p, "category": "Notiz", "is_completed": False}).execute()
                st.rerun()

st.divider()

# --- SEITE: HOME ---
if st.session_state.page == "🏠 Home":
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊\nDASHBOARD", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()
        if st.button("📦\nLAGER", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    with col2:
        if st.button("📋\nBOARD", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
        if st.button("⏱️\nZEITEN", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()

# --- SEITE: DASHBOARD ---
elif st.session_state.page == "📊 Dashboard":
    st.markdown(f"### 📊 Dashboard: {curr_p}")
    res = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Gesamtkosten", f"{df['cost_amount'].sum():.2f} €")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())
