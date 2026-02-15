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
    /* Hintergrund & Schrift */
    [data-testid="stAppViewContainer"] { background-color: #f8f9fa; }
    .stMarkdown h1, h2, h3 { color: #1e3a8a; font-family: 'Segoe UI', sans-serif; }
    
    /* Kachel-Design für Navigation */
    .nav-card {
        background: white;
        padding: 20px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
        margin-bottom: 10px;
        cursor: pointer;
    }
    
    /* Board-Einträge als moderne Karten */
    .entry-card {
        background: white;
        padding: 15px;
        border-radius: 15px;
        border-left: 6px solid #1e3a8a;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
    
    /* Fixer Button-Look */
    .stButton>button {
        border-radius: 12px !important;
        height: 3.5rem !important;
        font-weight: 600 !important;
        background-color: #1e3a8a !important;
        color: white !important;
        border: none !important;
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

# --- 3. LOGIK FÜR PROJEKTWAHL ---
# Wir nutzen session_state, um die Seite und das Projekt zu speichern
if 'page' not in st.session_state: st.session_state.page = "🏠 Home"

p_res = supabase.table("notes").select("project_name").execute()
p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))

# --- HEADER & PROJEKTWAHL ---
st.markdown("<h1 style='text-align: center;'>🏗️ WerkOS Pro</h1>", unsafe_allow_html=True)

c1, c2 = st.columns([2,1])
with c1:
    curr_p = st.selectbox("📍 Aktuelles Projekt:", p_list if p_list else ["Allgemein"])
with c2:
    with st.popover("✨ Neu"):
        new_p = st.text_input("Projektname:")
        if st.button("Anlegen"):
            if new_p:
                supabase.table("notes").insert({"content": "Projektstart", "project_name": new_p, "category": "Notiz", "is_completed": False}).execute()
                st.rerun()

# --- 4. NAVIGATION (KACHELN ODER BACK-BUTTON) ---
if st.session_state.page != "🏠 Home":
    if st.button("⬅️ Zurück zum Menü"):
        st.session_state.page = "🏠 Home"
        st.rerun()

# --- SEITE: HOME (KACHEL-MENÜ) ---
if st.session_state.page == "🏠 Home":
    st.markdown("### Hauptmenü")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊\nDashboard"): st.session_state.page = "📊 Dashboard"; st.rerun()
        if st.button("📦\nLager"): st.session_state.page = "📦 Lager"; st.rerun()
    with col2:
        if st.button("📋\nBoard"): st.session_state.page = "📋 Board"; st.rerun()
        if st.button("⏱️\nZeiten"): st.session_state.page = "⏱️ Zeiten"; st.rerun()

# --- SEITE: DASHBOARD ---
elif st.session_state.page == "📊 Dashboard":
    st.subheader(f"Dashboard: {curr_p}")
    res = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Projektkosten", f"{df['cost_amount'].sum():.2f} €")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())
    
    m_check = supabase.table("materials").select("*").execute()
    low = [m for m in m_check.data if float(m.get('stock_quantity',0)) <= float(m.get('min_stock',5))]
    for l in low: st.error(f"⚠️ Nachbestellen: {l['name']} ({l['stock_quantity']} rest)")

# --- SEITE: BOARD ---
elif st.session_state.page == "📋 Board":
    st.subheader(f"Board: {curr_p}")
    with st.expander("➕ Neuer Eintrag", expanded=False):
        with st.form("entry"):
            t = st.text_input("Was gibt's?")
            kat = st.selectbox("Typ", ["Notiz", "Aufgabe", "Wichtig"])
            cost = st.number_input("Kosten €", min_value=0.0)
            if st.form_submit_button("Speichern"):
                supabase.table("notes").insert({"content":t, "category":kat, "project_name":curr_p, "cost_amount":cost, "is_completed":False}).execute()
                st.rerun()
        img = st.camera_input("Foto")
        if img:
            fn = f"{datetime.datetime.now().strftime('%H%M%S')}.jpg"
            supabase.storage.from_("werkos_fotos").upload(fn, img.getvalue())
            url = supabase.storage.from_("werkos_fotos").get_public_url(fn)
            supabase.table("notes").insert({"content":"Foto", "category":"Notiz", "project_name":curr_p, "image_url":url, "is_completed":False}).execute()
            st.rerun()

    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).order("created_at", desc=True).execute()
    for e in res.data:
        st.markdown(f"""<div class="entry-card"><strong>{e['category']}</strong><br>{e['content']}<br><small>{e.get('cost_amount',0)} €</small></div>""", unsafe_allow_html=True)
        if e.get("image_url"): st.image(e["image_url"])
        if st.button("✅ Erledigt", key=e['id']):
            supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute()
            st.rerun()

# --- SEITE: LAGER ---
elif st.session_state.page == "📦 Lager":
    st.subheader("Lagerverwaltung")
    m_res = supabase.table("materials").select("*").execute()
    if m_res.data:
        for m in m_res.data:
            st.markdown(f"**{m['name']}**: {m['stock_quantity']} Einheiten")
        
        with st.form("book_l"):
            sel = st.selectbox("Material:", [m['name'] for m in m_res.data])
            q = st.number_input("Menge", min_value=1.0)
            if st.form_submit_button("Verbuchen"):
                info = next(i for i in m_res.data if i['name'] == sel)
                supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":info['price_per_unit']*q, "is_completed":False}).execute()
                supabase.table("materials").update({"stock_quantity": float(info['stock_quantity'])-q}).eq("id", info['id']).execute()
                st.rerun()

# --- SEITE: ZEIT ---
elif st.session_state.page == "⏱️ Zeiten":
    st.subheader("Zeiterfassung")
    s_res = supabase.table("staff").select("*").execute()
    if s_res.data:
        with st.form("time_l"):
            sel_s = st.selectbox("Wer?", [i['name'] for i in s_res.data])
            h = st.number_input("Stunden", min_value=0.5, step=0.5)
            if st.form_submit_button("Buchen"):
                s = next(i for i in s_res.data if i['name'] == sel_s)
                supabase.table("notes").insert({"content":f"{sel_s}: {h}h", "category":"Aufgabe", "project_name":curr_p, "cost_amount":s['hourly_rate']*h, "is_completed":False}).execute()
                st.rerun()

st.sidebar.button("📄 PDF Export", on_click=lambda: st.sidebar.write("PDF bereit!"))
