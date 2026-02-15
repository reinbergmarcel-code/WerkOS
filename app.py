import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd  # <-- HIER WAR DER FEHLER: KORRIGIERT AUF 'import pandas as pd'

# =========================================================
# I. BACKEND - DIE UNANTASTBARE LOGIK (v2.30 Standard)
# =========================================================
try:
    S_URL, S_KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    supabase = create_client(S_URL, S_KEY)
except:
    st.error("Supabase Verbindung fehlgeschlagen."); st.stop()

def db_get_all_data():
    return supabase.table("notes").select("*").execute()

def db_insert_note(content, category, project, cost=0.0):
    supabase.table("notes").insert({
        "content": content, "category": category, 
        "project_name": project, "cost_amount": cost, "is_completed": False
    }).execute()

def db_archive_project(project_name):
    supabase.table("notes").insert({
        "content": "PROJECT_ARCHIVED", "project_name": project_name, 
        "category": "System", "is_completed": True
    }).execute()

def db_reactivate_project(project_name):
    supabase.table("notes").delete().eq("project_name", project_name).eq("content", "PROJECT_ARCHIVED").execute()

# =========================================================
# II. FRONTEND - DAS DESIGN (v2.42 - REPARIERT)
# =========================================================
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC; color: #1e293b; }
    
    .app-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        padding: 20px; border-radius: 0 0 25px 25px; color: white; text-align: center; margin-bottom: 20px;
    }
    
    .stButton>button { 
        border-radius: 15px !important; font-weight: 700 !important; color: #1e293b !important; 
        background-color: white !important; border: 1px solid #cbd5e1 !important; height: 50px !important;
    }

    .card { background: white !important; padding: 20px; border-radius: 20px; margin-bottom: 15px; border: 1px solid #e2e8f0; }
    .card-notiz { border-left: 10px solid #3b82f6; }
    .card-aufgabe { border-left: 10px solid #f59e0b; }
    .card-wichtig { border-left: 10px solid #ef4444; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = "🏠 Home"

st.markdown('<div class="app-header"><h1>WerkOS Pro</h1></div>', unsafe_allow_html=True)

# 1. PROJEKT-WAHL & NEUANLAGE
data_res = db_get_all_data()
all_data = data_res.data if data_res.data else []
all_p = sorted(list(set([e['project_name'] for e in all_data if e.get('project_name')])))
arch_p = list(set([e['project_name'] for e in all_data if e['content'] == "PROJECT_ARCHIVED"]))

col1, col2 = st.columns([4, 1])
with col1:
    curr_p = st.selectbox("📍 Baustelle", [p for p in all_p if p not in arch_p] if not st.checkbox("Archiv") else all_p, label_visibility="collapsed")
with col2:
    with st.popover("➕"):
        new_p = st.text_input("Name:")
        if st.button("ANLEGEN"):
            if new_p: db_insert_note("Start", "Notiz", new_p); st.rerun()

is_archived = curr_p in arch_p
if curr_p and curr_p != "Allgemein":
    if not is_archived:
        if st.button(f"📁 {curr_p} ABSCHLIESSEN", use_container_width=True): db_archive_project(curr_p); st.rerun()
    else:
        if st.button(f"🔓 {curr_p} REAKTIVIEREN", use_container_width=True): db_reactivate_project(curr_p); st.rerun()

st.divider()

# 3. NAVIGATION & SEITEN
if st.session_state.page == "🏠 Home":
    c1, c2 = st.columns(2)
    if c1.button("📋 BOARD", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
    if c1.button("📦 LAGER", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    if c2.button("⏱️ ZEITEN", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()
    if c2.button("📊 STATS", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()

elif st.session_state.page == "📋 Board":
    if st.button("⬅️ ZURÜCK"): st.session_state.page = "🏠 Home"; st.rerun()
    if not is_archived:
        with st.expander("➕ NEUER EINTRAG"):
            with st.form("f"):
                t = st.text_input("Was?"); k = st.selectbox("Typ", ["Notiz", "Aufgabe", "Wichtig"]); c = st.number_input("€")
                if st.form_submit_button("SPEICHERN"): db_insert_note(t, k, curr_p, c); st.rerun()
    
    res = [e for e in all_data if e['project_name'] == curr_p and not e['is_completed'] and e['content'] != "PROJECT_ARCHIVED"]
    for e in res:
        st.markdown(f'<div class="card card-{e["category"].lower()}"><b>{e["category"]}</b><br>{e["content"]}<br>💰 {e.get("cost_amount",0):.2f} €</div>', unsafe_allow_html=True)
        if not is_archived:
            b1, b2, b3 = st.columns(3)
            if b1.button("✅", key=f"d_{e['id']}"): supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute(); st.rerun()
            if b3.button("🗑️", key=f"x_{e['id']}"): supabase.table("notes").delete().eq("id", e['id']).execute(); st.rerun()

elif st.session_state.page == "📦 Lager":
    if st.button("⬅️ ZURÜCK"): st.session_state.page = "🏠 Home"; st.rerun()
    m_res = supabase.table("materials").select("*").execute().data
    tab1, tab2 = st.tabs(["📥 Inventur", "📤 Verbrauch"])
    with tab1:
        with st.form("i"):
            sel = st.selectbox("Mat", [i['name'] for i in m_res]); q = st.number_input("Bestand")
            if st.form_submit_button("OK"):
                idx = next(i for i in m_res if i['name'] == sel)['id']
                supabase.table("materials").update({"stock_quantity": q}).eq("id", idx).execute(); st.rerun()
    with tab2:
        if not is_archived:
            with st.form("v"):
                sel = st.selectbox("Mat", [i['name'] for i in m_res]); q = st.number_input("Menge")
                if st.form_submit_button("BUCHEN"):
                    m = next(i for i in m_res if i['name'] == sel)
                    db_insert_note(f"{q}x {sel}", "Material", curr_p, m['price_per_unit']*q)
                    supabase.table("materials").update({"stock_quantity": float(m['stock_quantity'])-q}).eq("id", m['id']).execute(); st.rerun()
    for m in m_res: st.write(f"📦 {m['name']}: {m['stock_quantity']}")
