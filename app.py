import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd

# --- 1. APP CONFIG & STYLE (v2.35 - VOLLSTÄNDIGE WIEDERHERSTELLUNG) ---
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC; }

    .app-header {
        background: linear-gradient(180deg, #1e3a8a 0%, #1e40af 100%);
        padding: 20px; border-radius: 0 0 25px 25px; color: white; text-align: center; margin-bottom: 15px;
    }
    
    .stButton>button { border-radius: 20px !important; font-weight: 700 !important; }

    /* AMPEL-LOGIK & KARTEN */
    .card { background: white !important; padding: 20px; border-radius: 20px; margin-bottom: 12px; border: 1px solid #f1f5f9; position: relative; color: #1e293b !important; }
    .card-notiz { border-left: 12px solid #3498db !important; }
    .card-aufgabe { border-left: 12px solid #f1c40f !important; }
    .card-wichtig { border-left: 12px solid #e74c3c !important; }
    .card-material { border-left: 12px solid #95a5a6 !important; }

    /* ACTION BUTTONS */
    div.stButton > button[key^="d_"] { background-color: #dcfce7 !important; color: #166534 !important; height: 45px !important; }
    div.stButton > button[key^="e_"] { background-color: #fef9c3 !important; color: #854d0e !important; height: 45px !important; }
    div.stButton > button[key^="x_"] { background-color: #fee2e2 !important; color: #991b1b !important; height: 45px !important; }
    
    /* ARCHIV BUTTON */
    div.stButton > button[key="GLOBAL_ARCHIVE"] { background-color: #e74c3c !important; color: white !important; height: 55px !important; }
    div.stButton > button[key="GLOBAL_REACTIVATE"] { background-color: #27ae60 !important; color: white !important; height: 55px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ZUGANG ---
try:
    S_URL, S_KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    supabase = create_client(S_URL, S_KEY)
except:
    st.error("Konfiguration fehlt."); st.stop()

if 'page' not in st.session_state: st.session_state.page = "🏠 Home"
if 'edit_id' not in st.session_state: st.session_state.edit_id = None

st.markdown('<div class="app-header"><h1>WerkOS Pro</h1></div>', unsafe_allow_html=True)

# --- DATEN & PROJEKTWAHL ---
p_data = supabase.table("notes").select("project_name, content").execute()
all_p = sorted(list(set([e['project_name'] for e in p_data.data if e.get('project_name')])))
archived_list = list(set([e['project_name'] for e in p_data.data if e['content'] == "PROJECT_ARCHIVED"]))

show_archived = st.checkbox("Archivierte Projekte anzeigen")
curr_p = st.selectbox("📍 Baustelle:", all_p if show_archived else [p for p in all_p if p not in archived_list])

is_archived = curr_p in archived_list
if curr_p and curr_p != "Allgemein":
    if not is_archived:
        if st.button(f"📁 PROJEKT '{curr_p}' ABSCHLIESSEN", key="GLOBAL_ARCHIVE", use_container_width=True):
            supabase.table("notes").insert({"content": "PROJECT_ARCHIVED", "project_name": curr_p, "category": "System", "is_completed": True}).execute(); st.rerun()
    else:
        if st.button(f"🔓 PROJEKT '{curr_p}' REAKTIVIEREN", key="GLOBAL_REACTIVATE", use_container_width=True):
            supabase.table("notes").delete().eq("project_name", curr_p).eq("content", "PROJECT_ARCHIVED").execute(); st.rerun()

with st.popover("➕ Neues Projekt"):
    np = st.text_input("Name:")
    if st.button("Anlegen"):
        supabase.table("notes").insert({"content": "Start", "project_name": np, "category": "Notiz", "is_completed": False}).execute(); st.rerun()

st.divider()

if st.session_state.page != "🏠 Home":
    if st.button("⬅️ HAUPTMENÜ", use_container_width=True): st.session_state.page = "🏠 Home"; st.rerun()

# --- SEITEN ---
if st.session_state.page == "🏠 Home":
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📋 BOARD", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
        if st.button("📦 LAGER", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    with c2:
        if st.button("⏱️ ZEITEN", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()
        if st.button("📊 DASHBOARD", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()

elif st.session_state.page == "📋 Board":
    if is_archived: st.warning("🔒 ARCHIVIERT")
    else:
        with st.expander("➕ NEUER EINTRAG"):
            with st.form("f"):
                t = st.text_input("Titel"); k = st.selectbox("Kat", ["Notiz", "Aufgabe", "Wichtig"]); c = st.number_input("Kosten €")
                if st.form_submit_button("SPEICHERN"):
                    supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute(); st.rerun()
    
    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).neq("content", "PROJECT_ARCHIVED").order("created_at", desc=True).execute()
    for e in res.data:
        if st.session_state.edit_id == e['id']:
            with st.form(f"ed_{e['id']}"):
                nt = st.text_input("Inhalt", value=e['content'])
                if st.form_submit_button("Sichern"):
                    supabase.table("notes").update({"content": nt}).eq("id", e['id']).execute(); st.session_state.edit_id = None; st.rerun()
        else:
            st.markdown(f'<div class="card card-{e["category"].lower()}"><strong>{e["category"]}</strong><br>{e["content"]}<br><small>💰 {e.get("cost_amount",0)} €</small></div>', unsafe_allow_html=True)
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
            sel = st.selectbox("Mat", [i['name'] for i in m_res.data]); q = st.number_input("Bestand")
            if st.form_submit_button("KORRIGIEREN"):
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
    for m in m_res.data: st.write(f"📦 **{m['name']}**: {m['stock_quantity']}")

elif st.session_state.page == "📊 Dashboard":
    st.subheader(f"Dashboard: {curr_p}")
    res = supabase.table("notes").select("*").eq("project_name", curr_p).neq("content", "PROJECT_ARCHIVED").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Gesamtkosten", f"{df['cost_amount'].sum():.2f} €")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())
