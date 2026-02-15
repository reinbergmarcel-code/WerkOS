import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
from fpdf import FPDF
import pandas as pd

# --- 1. APP CONFIG & ULTIMATE MOBILE STYLING ---
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
    
    /* DIE RETTUNG: Echte Flexbox-Navigation */
    .nav-container {
        display: flex;
        justify-content: space-between;
        background: white;
        padding: 10px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .nav-item {
        flex: 1;
        text-align: center;
        font-size: 24px;
        cursor: pointer;
        padding: 10px;
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

# --- NAVIGATION (ROBUSTE VARIANTE) ---
# Wir nutzen Streamlit Buttons in einer fest definierten Spaltenbreite OHNE Umbruch-Erlaubnis
n_cols = st.columns([1,1,1,1,1])
with n_cols[0]:
    if st.button("🏠", key="n_h"): st.session_state.page = "🏠 Home"; st.rerun()
with n_cols[1]:
    if st.button("📊", key="n_d"): st.session_state.page = "📊 Dashboard"; st.rerun()
with n_cols[2]:
    if st.button("📋", key="n_b"): st.session_state.page = "📋 Board"; st.rerun()
with n_cols[3]:
    if st.button("📦", key="n_l"): st.session_state.page = "📦 Lager"; st.rerun()
with n_cols[4]:
    if st.button("⏱️", key="n_z"): st.session_state.page = "⏱️ Zeiten"; st.rerun()

st.divider()

# Projektwahl
p_res = supabase.table("notes").select("project_name").execute()
p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))

c_p1, c_p2 = st.columns([4,1])
with c_p1:
    curr_p = st.selectbox("📍 Projekt:", p_list if p_list else ["Allgemein"], key="p_sel_fix")
with c_p2:
    with st.popover("➕"):
        new_p = st.text_input("Name:")
        if st.button("Anlegen", key="btn_new_p"):
            if new_p:
                supabase.table("notes").insert({"content": "Start", "project_name": new_p, "category": "Notiz", "is_completed": False}).execute()
                st.rerun()

# --- SEITE: HOME ---
if st.session_state.page == "🏠 Home":
    st.markdown("### Hauptmenü")
    if st.button("📊 DASHBOARD", use_container_width=True, key="main_d"): st.session_state.page = "📊 Dashboard"; st.rerun()
    if st.button("📋 BOARD", use_container_width=True, key="main_b"): st.session_state.page = "📋 Board"; st.rerun()
    if st.button("📦 LAGER", use_container_width=True, key="main_l"): st.session_state.page = "📦 Lager"; st.rerun()
    if st.button("⏱️ ZEITEN", use_container_width=True, key="main_z"): st.session_state.page = "⏱️ Zeiten"; st.rerun()

# --- SEITE: DASHBOARD ---
elif st.session_state.page == "📊 Dashboard":
    st.markdown(f"### 📊 Statistik: {curr_p}")
    res = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Gesamtkosten", f"{df['cost_amount'].sum():.2f} €")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())

# --- SEITE: BOARD (Bearbeiten, Löschen, Erledigen voll erhalten) ---
elif st.session_state.page == "📋 Board":
    with st.expander("➕ NEUER EINTRAG"):
        with st.form("f_new"):
            t = st.text_input("Titel")
            k = st.selectbox("Typ", ["Aufgabe", "Notiz", "Wichtig"])
            c = st.number_input("Kosten €", min_value=0.0)
            if st.form_submit_button("SPEICHERN"):
                supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute()
                st.rerun()
        img = st.camera_input("Kamera")
        if img:
            fn = f"{datetime.datetime.now().strftime('%H%M%S')}.jpg"
            supabase.storage.from_("werkos_fotos").upload(fn, img.getvalue())
            url = supabase.storage.from_("werkos_fotos").get_public_url(fn)
            supabase.table("notes").insert({"content":"Foto", "category":"Notiz", "project_name":curr_p, "image_url":url, "is_completed":False}).execute()
            st.rerun()

    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).order("created_at", desc=True).execute()
    for e in res.data:
        if st.session_state.edit_id == e['id']:
            with st.form(f"edit_f_{e['id']}"):
                nt = st.text_input("Inhalt", value=e['content'])
                nc = st.number_input("Kosten", value=float(e.get('cost_amount', 0)))
                if st.form_submit_button("Speichern"):
                    supabase.table("notes").update({"content": nt, "cost_amount": nc}).eq("id", e['id']).execute()
                    st.session_state.edit_id = None
                    st.rerun()
        else:
            st.markdown(f"""<div class="card"><strong>{e['category']}</strong><br>{e['content']}<br><small>{e.get('cost_amount',0)} €</small></div>""", unsafe_allow_html=True)
            if e.get("image_url"): st.image(e["image_url"])
            c1, c2, c3 = st.columns(3)
            if c1.button("✅", key=f"d_{e['id']}"):
                supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute()
                st.rerun()
            if c2.button("✏️", key=f"e_{e['id']}"):
                st.session_state.edit_id = e['id']
                st.rerun()
            if c3.button("🗑️", key=f"x_{e['id']}"):
                supabase.table("notes").delete().eq("id", e['id']).execute()
                st.rerun()

# --- SEITE: LAGER (Voll erhalten) ---
elif st.session_state.page == "📦 Lager":
    st.subheader("📦 Lagerverwaltung")
    with st.expander("➕ MATERIAL ANLEGEN"):
        with st.form("m_add_v"):
            n = st.text_input("Name")
            p = st.number_input("Preis")
            s = st.number_input("Bestand")
            if st.form_submit_button("Hinzufügen"):
                supabase.table("materials").insert({"name":n, "price_per_
