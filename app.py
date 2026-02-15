import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd

# --- 1. APP CONFIG & RADIKALES APP-DESIGN (v2.37) ---
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] { 
        font-family: 'Inter', sans-serif; 
        background-color: #F8FAFC !important; 
    }

    /* App-Header: Modern & Kompakt */
    .app-header {
        background: #1e3a8a;
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        padding: 30px 20px;
        border-radius: 0 0 40px 40px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 15px 30px rgba(0,0,0,0.15);
    }
    
    /* Buttons als echte App-Kacheln */
    .stButton>button {
        border: none !important;
        border-radius: 28px !important;
        background: white !important;
        color: #1e3a8a !important;
        font-weight: 700 !important;
        padding: 20px !important;
        box-shadow: 0 10px 20px rgba(0,0,0,0.05) !important;
        border: 1px solid rgba(0,0,0,0.02) !important;
    }
    
    .stButton>button:hover {
        background: #f1f5f9 !important;
        transform: translateY(-2px);
    }

    /* Board-Karten: "Glassmorphism" Style */
    .card {
        background: white !important;
        padding: 25px;
        border-radius: 30px;
        margin-bottom: 20px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.04);
        border: 1px solid #f1f5f9;
        position: relative;
    }
    
    /* Status-Ampel integriert als moderner Indikator */
    .card-notiz { border-top: 8px solid #3b82f6 !important; }
    .card-aufgabe { border-top: 8px solid #f59e0b !important; }
    .card-wichtig { border-top: 8px solid #ef4444 !important; }
    .card-material { border-top: 8px solid #64748b !important; }

    /* Eingabefelder App-Style */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 20px !important;
        border: 1px solid #e2e8f0 !important;
        background: white !important;
        padding: 10px 15px !important;
    }

    /* Spezielle Buttons */
    div.stButton > button[key="GLOBAL_ARCHIVE"] { background: #fee2e2 !important; color: #dc2626 !important; border: none !important; }
    div.stButton > button[key="GLOBAL_REACTIVATE"] { background: #dcfce7 !important; color: #16a34a !important; border: none !important; }
    
    header {visibility: hidden;}
    footer {visibility: hidden;}
    hr { border: none !important; height: 1px !important; background: transparent !important; margin: 20px 0 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. UNANTASTBARE LOGIK (v2.35 REFERENZ) ---
try:
    S_URL, S_KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    supabase = create_client(S_URL, S_KEY)
except:
    st.error("Konfiguration fehlt."); st.stop()

if 'page' not in st.session_state: st.session_state.page = "🏠 Home"
if 'edit_id' not in st.session_state: st.session_state.edit_id = None

st.markdown('<div class="app-header"><h1>WerkOS Pro</h1><p style="opacity:0.7; font-size:0.9rem;">Building Success</p></div>', unsafe_allow_html=True)

# PROJEKTSTEUERUNG
p_data = supabase.table("notes").select("project_name, content").execute()
all_p = sorted(list(set([e['project_name'] for e in p_data.data if e.get('project_name')])))
archived_list = list(set([e['project_name'] for e in p_data.data if e['content'] == "PROJECT_ARCHIVED"]))

show_archived = st.checkbox("Archiv anzeigen")
curr_p = st.selectbox("📍 Projekt", all_p if show_archived else [p for p in all_p if p not in archived_list], label_visibility="collapsed")

is_archived = curr_p in archived_list
if curr_p and curr_p != "Allgemein":
    if not is_archived:
        if st.button(f"PROJEKT ABSCHLIESSEN", key="GLOBAL_ARCHIVE", use_container_width=True):
            supabase.table("notes").insert({"content": "PROJECT_ARCHIVED", "project_name": curr_p, "category": "System", "is_completed": True}).execute(); st.rerun()
    else:
        if st.button(f"PROJEKT REAKTIVIEREN", key="GLOBAL_REACTIVATE", use_container_width=True):
            supabase.table("notes").delete().eq("project_name", curr_p).eq("content", "PROJECT_ARCHIVED").execute(); st.rerun()

with st.popover("➕ NEU"):
    np = st.text_input("Projektname:")
    if st.button("Anlegen"):
        if np: supabase.table("notes").insert({"content": "Start", "project_name": np, "category": "Notiz", "is_completed": False}).execute(); st.rerun()

st.write("") # Abstandhalter statt Divider

if st.session_state.page != "🏠 Home":
    if st.button("⬅️ HAUPTMENÜ", use_container_width=True):
        st.session_state.page = "🏠 Home"; st.rerun()

# --- SEITEN (LOGIK VOLLSTÄNDIG) ---
if st.session_state.page == "🏠 Home":
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📋\nBOARD", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
        if st.button("📦\nLAGER", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    with c2:
        if st.button("⏱️\nZEITEN", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()
        if st.button("📊\nSTATS", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()

elif st.session_state.page == "📋 Board":
    if is_archived: st.warning("🔒 Archiv")
    else:
        with st.expander("➕ NEUER EINTRAG"):
            with st.form("f"):
                t = st.text_input("Titel"); k = st.selectbox("Typ", ["Notiz", "Aufgabe", "Wichtig"]); c = st.number_input("€", step=1.0)
                if st.form_submit_button("SPEICHERN", use_container_width=True):
                    supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute(); st.rerun()

    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).neq("content", "PROJECT_ARCHIVED").order("created_at", desc=True).execute()
    for e in res.data:
        st.markdown(f'<div class="card card-{e["category"].lower()}"><b>{e["category"]}</b><div style="font-size:1.2rem; font-weight:700; color:#0f172a; margin: 10px 0;">{e["content"]}</div><div style="color:#64748b; font-size:0.9rem;">💰 {e.get("cost_amount",0):.2f} €</div></div>', unsafe_allow_html=True)
        if not is_archived:
            c1, c2, c3 = st.columns(3)
            if c1.button("✅", key=f"d_{e['id']}"): supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute(); st.rerun()
            if c2.button("✏️", key=f"e_{e['id']}"): st.session_state.edit_id = e['id']; st.rerun()
            if c3.button("🗑️", key=f"x_{e['id']}"): supabase.table("notes").delete().eq("id", e['id']).execute(); st.rerun()

elif st.session_state.page == "📦 Lager":
    st.subheader("📦 Lager")
    m_res = supabase.table("materials").select("*").execute()
    t1, t2 = st.tabs(["📥 Inventur", "📤 Verbrauch"])
    with t1:
        with st.form("m1"):
            sel = st.selectbox("Produkt", [i['name'] for i in m_res.data]); q = st.number_input("Bestand")
            if st.form_submit_button("AKTUALISIEREN"):
                idx = next(i for i in m_res.data if i['name'] == sel)['id']
                supabase.table("materials").update({"stock_quantity": q}).eq("id", idx).execute(); st.rerun()
    with t2:
        if not is_archived:
            with st.form("m2"):
                sel = st.selectbox("Was wurde genutzt?", [i['name'] for i in m_res.data]); q = st.number_input("Menge")
                if st.form_submit_button("VERBRAUCH BUCHEN"):
                    m = next(i for i in m_res.data if i['name'] == sel)
                    supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":m['price_per_unit']*q, "is_completed":False}).execute()
                    supabase.table("materials").update({"stock_quantity": float(m['stock_quantity'])-q}).eq("id", m['id']).execute(); st.rerun()
    for m in m_res.data: st.info(f"{m['name']}: {m['stock_quantity']} Stk.")
