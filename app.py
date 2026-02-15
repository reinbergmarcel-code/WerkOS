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

if st.session_state.page != "🏠 Home":
    if st.button("⬅️ MENÜ"):
        st.session_state.page = "🏠 Home"
        st.session_state.edit_id = None
        st.rerun()

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

# --- SEITE: BOARD ---
elif st.session_state.page == "📋 Board":
    with st.expander("➕ NEUER EINTRAG / FOTO"):
        with st.form("new_e"):
            t = st.text_input("Titel")
            k = st.selectbox("Kat", ["Aufgabe", "Notiz", "Wichtig"])
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
            with st.form(f"edit_{e['id']}"):
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

# --- SEITE: LAGER ---
elif st.session_state.page == "📦 Lager":
    st.markdown("### 📦 Lager")
    with st.expander("➕ NEUES MATERIAL ANLEGEN"):
        with st.form("m_add"):
            n = st.text_input("Name")
            p = st.number_input("Preis")
            s = st.number_input("Bestand")
            if st.form_submit_button("Anlegen"):
                supabase.table("materials").insert({"name":n, "price_per_unit":p, "stock_quantity":s, "min_stock":5}).execute()
                st.rerun()
    m_res = supabase.table("materials").select("*").execute()
    if m_res.data:
        for m in m_res.data: st.write(f"📦 {m['name']}: {m['stock_quantity']}")
        with st.form("m_book"):
            sel = st.selectbox("Material:", [i['name'] for i in m_res.data])
            q = st.number_input("Menge", min_value=1.0)
            if st.form_submit_button("Verbuchen"):
                info = next(i for i in m_res.data if i['name'] == sel)
                supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":info['price_per_unit']*q, "is_completed":False}).execute()
                supabase.table("materials").update({"stock_quantity": float(info['stock_quantity'])-q}).eq("id", info['id']).execute()
                st.rerun()

# --- SEITE: ZEITEN ---
elif st.session_state.page == "⏱️ Zeiten":
    st.markdown("### ⏱️ Zeiten")
    with st.expander("👤 NEUER MITARBEITER"):
        with st.form("s_add"):
            sn = st.text_input("Name")
            sr = st.number_input("Satz €", value=45.0)
            if st.form_submit_button("Speichern"):
                supabase.table("staff").insert({"name":sn, "hourly_rate":sr}).execute()
                st.rerun()
    s_res = supabase.table("staff").select("*").execute()
    if s_res.data:
        with st.form("s_book"):
            sel_s = st.selectbox("Wer?", [i['name'] for i in s_res.data])
            h = st.number_input("Stunden", min_value=0.5, step=0.5)
            if st.form_submit_button("Buchen"):
                s = next(i for i in s_res.data if i['name'] == sel_s)
                supabase.table("notes").insert({"content":f"{sel_s}: {h}h", "category":"Aufgabe", "project_name":curr_p, "cost_amount":s['hourly_rate']*h, "is_completed":False}).execute()
                st.rerun()
