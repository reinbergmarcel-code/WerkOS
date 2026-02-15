import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd

# --- 1. APP CONFIG & APP-STYLE (v2.36 - PURE DESIGN UPDATE) ---
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* App-Hintergrund und Basis-Schrift */
    html, body, [class*="css"] { 
        font-family: 'Inter', sans-serif; 
        background-color: #F1F5F9 !important; 
    }

    /* Der Header als kompakte App-Bar */
    .app-header {
        background: #1e3a8a;
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
        padding: 1.5rem;
        border-radius: 0 0 30px 30px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }

    /* Hauptmenü Kacheln (Grid-Optik) */
    .stButton>button {
        border: none !important;
        border-radius: 20px !important;
        background: white !important;
        color: #1e3a8a !important;
        font-weight: 700 !important;
        height: 120px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        transition: transform 0.2s ease !important;
    }
    
    .stButton>button:active { transform: scale(0.96); }

    /* Die Karten im Board */
    .card {
        background: white !important;
        padding: 24px;
        border-radius: 24px;
        margin-bottom: 16px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.03);
        border: 1px solid rgba(226, 232, 240, 0.8);
        color: #1e293b !important;
    }
    
    /* Ampel-Balken (v2.35 Standard) */
    .card-notiz { border-left: 10px solid #3b82f6 !important; }
    .card-aufgabe { border-left: 10px solid #eab308 !important; }
    .card-wichtig { border-left: 10px solid #ef4444 !important; }
    .card-material { border-left: 10px solid #64748b !important; }

    /* Action Buttons in den Karten (Dezentere Pillen-Form) */
    div.stButton > button[key^="d_"], 
    div.stButton > button[key^="e_"], 
    div.stButton > button[key^="x_"] { 
        height: 40px !important; 
        border-radius: 12px !important; 
        font-size: 0.9rem !important;
    }

    /* Archiv-Button (Präsent aber clean) */
    div.stButton > button[key="GLOBAL_ARCHIVE"] { background: #fee2e2 !important; color: #b91c1c !important; height: 50px !important; border: 1px solid #fecaca !important; }
    div.stButton > button[key="GLOBAL_REACTIVATE"] { background: #dcfce7 !important; color: #15803d !important; height: 50px !important; border: 1px solid #bbf7d0 !important; }

    /* UI Elemente ausblenden */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stMetricValue"] { font-weight: 700; color: #1e3a8a; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIK-KERN (IDENTISCH ZU v2.35) ---
try:
    S_URL, S_KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    supabase = create_client(S_URL, S_KEY)
except:
    st.error("Konfiguration fehlt."); st.stop()

if 'page' not in st.session_state: st.session_state.page = "🏠 Home"
if 'edit_id' not in st.session_state: st.session_state.edit_id = None

st.markdown('<div class="app-header"><h1>WerkOS Pro</h1></div>', unsafe_allow_html=True)

# PROJEKTSTEUERUNG
p_data = supabase.table("notes").select("project_name, content").execute()
all_p = sorted(list(set([e['project_name'] for e in p_data.data if e.get('project_name')])))
archived_list = list(set([e['project_name'] for e in p_data.data if e['content'] == "PROJECT_ARCHIVED"]))

col_sel, col_arch = st.columns([2, 1])
with col_sel:
    show_archived = st.checkbox("Archiv anzeigen", value=False)
    active_p = [p for p in all_p if p not in archived_list]
    curr_p = st.selectbox("📌 Projekt", all_p if show_archived else active_p, label_visibility="collapsed")

is_archived = curr_p in archived_list
if curr_p and curr_p != "Allgemein":
    if not is_archived:
        if st.button(f"📁 {curr_p} ABSCHLIESSEN", key="GLOBAL_ARCHIVE", use_container_width=True):
            supabase.table("notes").insert({"content": "PROJECT_ARCHIVED", "project_name": curr_p, "category": "System", "is_completed": True}).execute(); st.rerun()
    else:
        if st.button(f"🔓 {curr_p} REAKTIVIEREN", key="GLOBAL_REACTIVATE", use_container_width=True):
            supabase.table("notes").delete().eq("project_name", curr_p).eq("content", "PROJECT_ARCHIVED").execute(); st.rerun()

with st.popover("➕ NEUES PROJEKT"):
    np = st.text_input("Name des Projekts:")
    if st.button("PROJEKT ANLEGEN", use_container_width=True):
        if np: supabase.table("notes").insert({"content": "Start", "project_name": np, "category": "Notiz", "is_completed": False}).execute(); st.rerun()

st.divider()

if st.session_state.page != "🏠 Home":
    if st.button("⬅️ ZURÜCK ZUM MENÜ", key="back_to_menu", use_container_width=True):
        st.session_state.page = "🏠 Home"; st.rerun()

# --- SEITEN (LOGIK AUS v2.35 UNVERÄNDERT) ---
if st.session_state.page == "🏠 Home":
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📋\nBOARD", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
        if st.button("📦\nLAGER", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    with c2:
        if st.button("⏱️\nZEITEN", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()
        if st.button("📊\nDASHBOARD", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()

elif st.session_state.page == "📋 Board":
    if is_archived: st.warning("🔒 PROJEKT ARCHIVIERT")
    else:
        with st.expander("➕ NEUER EINTRAG"):
            with st.form("f_new"):
                t = st.text_input("Was ist zu tun?"); k = st.selectbox("Priorität", ["Notiz", "Aufgabe", "Wichtig"]); c = st.number_input("Kosten €", step=1.0)
                if st.form_submit_button("EINTRAG SPEICHERN", use_container_width=True):
                    supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute(); st.rerun()

    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).neq("content", "PROJECT_ARCHIVED").order("created_at", desc=True).execute()
    for e in res.data:
        if st.session_state.edit_id == e['id']:
            with st.form(f"ed_{e['id']}"):
                nt = st.text_input("Text ändern", value=e['content'])
                if st.form_submit_button("ÄNDERUNG SICHERN"):
                    supabase.table("notes").update({"content": nt}).eq("id", e['id']).execute(); st.session_state.edit_id = None; st.rerun()
        else:
            st.markdown(f'<div class="card card-{e["category"].lower()}"><strong>{e["category"]}</strong><div style="font-size:1.15rem; font-weight:600; margin-top:8px;">{e["content"]}</div><div style="color:#64748b; margin-top:8px;">💰 {e.get("cost_amount",0):.2f} €</div></div>', unsafe_allow_html=True)
            if not is_archived:
                c1, c2, c3 = st.columns(3)
                if c1.button("✅", key=f"d_{e['id']}"): supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute(); st.rerun()
                if c2.button("✏️", key=f"e_{e['id']}"): st.session_state.edit_id = e['id']; st.rerun()
                if c3.button("🗑️", key=f"x_{e['id']}"): supabase.table("notes").delete().eq("id", e['id']).execute(); st.rerun()

elif st.session_state.page == "📦 Lager":
    st.subheader("📦 Lager-Zentrale")
    m_res = supabase.table("materials").select("*").execute()
    t1, t2 = st.tabs(["📥 Inventur", "📤 Verbrauch"])
    with t1:
        with st.form("m1_f"):
            sel = st.selectbox("Material", [i['name'] for i in m_res.data]); q = st.number_input("Aktueller Bestand")
            if st.form_submit_button("BESTAND ÜBERSCHREIBEN", use_container_width=True):
                idx = next(i for i in m_res.data if i['name'] == sel)['id']
                supabase.table("materials").update({"stock_quantity": q}).eq("id", idx).execute(); st.rerun()
    with t2:
        if not is_archived:
            with st.form("m2_f"):
                sel = st.selectbox("Was wurde verbraucht?", [i['name'] for i in m_res.data]); q = st.number_input("Menge")
                if st.form_submit_button("MENGE ABBUCHEN", use_container_width=True):
                    m = next(i for i in m_res.data if i['name'] == sel)
                    supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":m['price_per_unit']*q, "is_completed":False}).execute()
                    supabase.table("materials").update({"stock_quantity": float(m['stock_quantity'])-q}).eq("id", m['id']).execute(); st.rerun()
    st.markdown("---")
    for m in m_res.data:
        st.write(f"📦 **{m['name']}**: {m['stock_quantity']} verfügbar")

elif st.session_state.page == "📊 Dashboard":
    st.subheader(f"📊 Auswertung: {curr_p}")
    res = supabase.table("notes").select("*").eq("project_name", curr_p).neq("content", "PROJECT_ARCHIVED").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Gesamte Projektkosten", f"{df['cost_amount'].sum():.2f} €")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())
