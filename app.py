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
    [data-testid="stAppViewContainer"] { background-color: #f8f9fa; }
    .entry-card {
        background: white;
        padding: 15px;
        border-radius: 15px;
        border-left: 6px solid #1e3a8a;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
    .stButton>button {
        border-radius: 12px !important;
        font-weight: 600 !important;
    }
    /* Roter Button für Löschen */
    div.stButton > button:first-child[key^="del_"] {
        background-color: #ff4b4b !important;
        color: white !important;
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

# --- 3. NAVIGATION LOGIK ---
if 'page' not in st.session_state: st.session_state.page = "🏠 Home"

p_res = supabase.table("notes").select("project_name").execute()
p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))

st.markdown("<h1 style='text-align: center;'>🏗️ WerkOS Pro</h1>", unsafe_allow_html=True)

# Projektwahl & Neu-Anlage
col_p1, col_p2 = st.columns([3,1])
with col_p1:
    curr_p = st.selectbox("📍 Baustelle:", p_list if p_list else ["Allgemein"])
with col_p2:
    with st.popover("➕ Neu"):
        new_p = st.text_input("Name der Baustelle:")
        if st.button("Projekt anlegen"):
            if new_p:
                supabase.table("notes").insert({"content": "Projekt angelegt", "project_name": new_p, "category": "Notiz", "is_completed": False}).execute()
                st.rerun()

st.divider()

if st.session_state.page != "🏠 Home":
    if st.button("⬅️ Menü"):
        st.session_state.page = "🏠 Home"
        st.rerun()

# --- SEITE: HOME ---
if st.session_state.page == "🏠 Home":
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📊\nDashboard", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()
        if st.button("📦\nLager", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    with c2:
        if st.button("📋\nBoard", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
        if st.button("⏱️\nZeiten", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()

# --- SEITE: DASHBOARD ---
elif st.session_state.page == "📊 Dashboard":
    st.subheader(f"Statistik: {curr_p}")
    res = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Gesamtkosten", f"{df['cost_amount'].sum():.2f} €")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())

# --- SEITE: BOARD ---
elif st.session_state.page == "📋 Board":
    with st.expander("📝 Neuer Eintrag / Foto", expanded=False):
        with st.form("entry_f"):
            t = st.text_input("Titel")
            k = st.selectbox("Typ", ["Aufgabe", "Notiz", "Wichtig"])
            c = st.number_input("Kosten €", min_value=0.0)
            if st.form_submit_button("Speichern"):
                supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute()
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
        with st.container():
            st.markdown(f"""<div class="entry-card"><strong>{e['category']}</strong><br>{e['content']}<br><small>{e.get('cost_amount',0)} €</small></div>""", unsafe_allow_html=True)
            if e.get("image_url"): st.image(e["image_url"])
            b1, b2 = st.columns(2)
            if b1.button("✅ Erledigt", key=f"done_{e['id']}"):
                supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute()
                st.rerun()
            if b2.button("🗑️ Löschen", key=f"del_{e['id']}"):
                supabase.table("notes").delete().eq("id", e['id']).execute()
                st.rerun()

# --- SEITE: LAGER ---
elif st.session_state.page == "📦 Lager":
    st.subheader("Lager")
    with st.expander("➕ Neues Material anlegen"):
        with st.form("new_mat"):
            n = st.text_input("Name")
            p = st.number_input("Preis/Stück")
            s = st.number_input("Anfangsbestand")
            if st.form_submit_button("Im Lager speichern"):
                supabase.table("materials").insert({"name":n, "price_per_unit":p, "stock_quantity":s, "min_stock":5}).execute()
                st.rerun()
    
    m_res = supabase.table("materials").select("*").execute()
    if m_res.data:
        st.write("### Bestand")
        for m in m_res.data:
            st.write(f"📦 {m['name']}: **{m['stock_quantity']}** (Limit: {m['min_stock']})")
        
        with st.form("book_mat"):
            sel = st.selectbox("Material wählen:", [m['name'] for m in m_res.data])
            q = st.number_input("Menge entnommen", min_value=1.0)
            if st.form_submit_button("Vom Lager abbuchen"):
                info = next(i for i in m_res.data if i['name'] == sel)
                supabase.table("notes").insert({"content":f"{q}x {sel} verbaut", "category":"Material", "project_name":curr_p, "cost_amount":info['price_per_unit']*q, "is_completed":False}).execute()
                supabase.table("materials").update({"stock_quantity": float(info['stock_quantity'])-q}).eq("id", info['id']).execute()
                st.rerun()

# --- SEITE: ZEIT ---
elif st.session_state.page == "⏱️ Zeiten":
    st.subheader("Zeiterfassung")
    with st.expander("👤 Neuen Mitarbeiter anlegen"):
        with st.form("new_staff"):
            sn = st.text_input("Name")
            sr = st.number_input("Stundensatz €", value=45.0)
            if st.form_submit_button("Mitarbeiter speichern"):
                supabase.table("staff").insert({"name":sn, "hourly_rate":sr}).execute()
                st.rerun()

    s_res = supabase.table("staff").select("*").execute()
    if s_res.data:
        with st.form("time_b"):
            sel_s = st.selectbox("Wer?", [i['name'] for i in s_res.data])
            h = st.number_input("Stunden", min_value=0.5, step=0.5)
            if st.form_submit_button("Zeit buchen"):
                s = next(i for i in s_res.data if i['name'] == sel_s)
                supabase.table("notes").insert({"content":f"{sel_s}: {h}h", "category":"Aufgabe", "project_name":curr_p, "cost_amount":s['hourly_rate']*h, "is_completed":False}).execute()
                st.rerun()

# PDF Export in der Sidebar
if st.sidebar.button("📄 PDF Bericht"):
    st.sidebar.success("PDF Funktion aktiv")
