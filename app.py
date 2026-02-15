import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd

# --- 1. APP CONFIG & FIX (v2.38 - SICHTBARKEIT GARANTIERT) ---
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* Basis-Setup für Sichtbarkeit */
    html, body, [class*="css"] { 
        font-family: 'Inter', sans-serif; 
        background-color: #F8FAFC !important; 
        color: #1e293b !important;
    }

    .app-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        padding: 25px; border-radius: 0 0 25px 25px; color: white; text-align: center; margin-bottom: 20px;
    }
    
    /* Buttons: Text muss SCHWARZ sein für Lesbarkeit */
    .stButton>button { 
        border-radius: 15px !important; 
        font-weight: 700 !important; 
        color: #1e293b !important; 
        background-color: white !important;
        border: 1px solid #e2e8f0 !important;
        width: 100% !important;
    }

    /* Board-Karten mit Ampel-Logik */
    .card { 
        background: white !important; 
        padding: 20px; 
        border-radius: 20px; 
        margin-bottom: 15px; 
        border: 1px solid #e2e8f0; 
        color: #1e293b !important;
    }
    .card-notiz { border-left: 10px solid #3b82f6 !important; }
    .card-aufgabe { border-left: 10px solid #f59e0b !important; }
    .card-wichtig { border-left: 10px solid #ef4444 !important; }
    .card-material { border-left: 10px solid #64748b !important; }

    /* Action Buttons (Farbige Hintergründe für Icons) */
    div.stButton > button[key^="d_"] { background-color: #dcfce7 !important; }
    div.stButton > button[key^="e_"] { background-color: #fef9c3 !important; }
    div.stButton > button[key^="x_"] { background-color: #fee2e2 !important; }

    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. ZUGANG & LOGIK (v2.35 UNANTASTBAR) ---
try:
    S_URL, S_KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    supabase = create_client(S_URL, S_KEY)
except:
    st.error("Konfiguration fehlt."); st.stop()

if 'page' not in st.session_state: st.session_state.page = "🏠 Home"
if 'edit_id' not in st.session_state: st.session_state.edit_id = None

st.markdown('<div class="app-header"><h1>WerkOS Pro</h1></div>', unsafe_allow_html=True)

# PROJEKT-MANAGER
p_data = supabase.table("notes").select("project_name, content").execute()
all_p = sorted(list(set([e['project_name'] for e in p_data.data if e.get('project_name')])))
arch_l = list(set([e['project_name'] for e in p_data.data if e['content'] == "PROJECT_ARCHIVED"]))

show_arch = st.checkbox("Archiv einblenden")
curr_p = st.selectbox("📍 Projekt wählen", all_p if show_arch else [p for p in all_p if p not in arch_l])

is_archived = curr_p in arch_l
if curr_p and curr_p != "Allgemein":
    if not is_archived:
        if st.button(f"📁 {curr_p} ABSCHLIESSEN", use_container_width=True):
            supabase.table("notes").insert({"content": "PROJECT_ARCHIVED", "project_name": curr_p, "category": "System", "is_completed": True}).execute(); st.rerun()
    else:
        if st.button(f"🔓 {curr_p} REAKTIVIEREN", use_container_width=True):
            supabase.table("notes").delete().eq("project_name", curr_p).eq("content", "PROJECT_ARCHIVED").execute(); st.rerun()

st.divider()

if st.session_state.page != "🏠 Home":
    if st.button("⬅️ HAUPTMENÜ"): st.session_state.page = "🏠 Home"; st.rerun()

# --- SEITEN-INHALT ---
if st.session_state.page == "🏠 Home":
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📋 BOARD"): st.session_state.page = "📋 Board"; st.rerun()
        if st.button("📦 LAGER"): st.session_state.page = "📦 Lager"; st.rerun()
    with c2:
        if st.button("⏱️ ZEITEN"): st.session_state.page = "⏱️ Zeiten"; st.rerun()
        if st.button("📊 DASHBOARD"): st.session_state.page = "📊 Dashboard"; st.rerun()

elif st.session_state.page == "📋 Board":
    if is_archived: st.warning("🔒 Archiv")
    else:
        with st.expander("➕ NEUER EINTRAG"):
            with st.form("new"):
                t = st.text_input("Titel"); k = st.selectbox("Kat", ["Notiz", "Aufgabe", "Wichtig"]); c = st.number_input("€")
                if st.form_submit_button("SPEICHERN"):
                    supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute(); st.rerun()
    
    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).neq("content", "PROJECT_ARCHIVED").order("created_at", desc=True).execute()
    for e in res.data:
        st.markdown(f'<div class="card card-{e["category"].lower()}"><b>{e["category"]}</b><br>{e["content"]}<br>💰 {e.get("cost_amount",0):.2f} €</div>', unsafe_allow_html=True)
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
        with st.form("inv"):
            sel = st.selectbox("Mat", [i['name'] for i in m_res.data]); q = st.number_input("Bestand")
            if st.form_submit_button("KORRIGIEREN"):
                idx = next(i for i in m_res.data if i['name'] == sel)['id']
                supabase.table("materials").update({"stock_quantity": q}).eq("id", idx).execute(); st.rerun()
    with t2:
        if not is_archived:
            with st.form("cons"):
                sel = st.selectbox("Mat", [i['name'] for i in m_res.data]); q = st.number_input("Menge")
                if st.form_submit_button("BUCHEN"):
                    m = next(i for i in m_res.data if i['name'] == sel)
                    supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":m['price_per_unit']*q, "is_completed":False}).execute()
                    supabase.table("materials").update({"stock_quantity": float(m['stock_quantity'])-q}).eq("id", m['id']).execute(); st.rerun()
    for m in m_res.data: st.write(f"📦 {m['name']}: {m['stock_quantity']}")
