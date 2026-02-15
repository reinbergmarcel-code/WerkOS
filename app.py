import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd

# --- 1. APP CONFIG & RADICAL APP REDESIGN (v2.31) ---
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    :root {
        --primary: #1e3a8a;
        --accent: #3b82f6;
        --bg: #F8FAFC;
        --card-bg: #ffffff;
    }

    html, body, [class*="css"] { 
        font-family: 'Inter', sans-serif; 
        background-color: var(--bg); 
    }

    /* Modern App Header */
    .app-header {
        background: var(--primary);
        background: linear-gradient(180deg, #1e3a8a 0%, #1e40af 100%);
        padding: 30px 20px;
        border-radius: 0 0 30px 30px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* Tiles for Home Screen */
    .stButton>button {
        border: none !important;
        border-radius: 24px !important;
        background: white !important;
        color: var(--primary) !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        height: 120px !important;
        box-shadow: 0 8px 20px rgba(0,0,0,0.04) !important;
        transition: all 0.3s ease !important;
        border: 1px solid #edf2f7 !important;
    }
    
    .stButton>button:active {
        transform: scale(0.95);
        background: #f1f5f9 !important;
    }

    /* Back Button Styling */
    div.stButton > button[key="back_to_menu"] { 
        background-color: transparent !important;
        border: 1px solid white !important;
        color: white !important;
        height: 45px !important;
        margin-bottom: 15px !important;
        font-size: 0.9rem !important;
        border-radius: 12px !important;
    }

    /* Modern Board Cards */
    .card {
        background: var(--card-bg);
        padding: 22px;
        border-radius: 24px;
        margin-bottom: 18px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.03);
        border: 1px solid #f1f5f9;
        position: relative;
        overflow: hidden;
    }
    
    .card::before {
        content: "";
        position: absolute;
        left: 0; top: 0; bottom: 0;
        width: 8px;
    }
    
    .card-notiz::before { background: #3b82f6; }
    .card-aufgabe::before { background: #f59e0b; }
    .card-wichtig::before { background: #ef4444; }
    .card-material::before { background: #64748b; }

    .status-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    /* UI Fixes */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stSelectbox label, .stCheckbox label { font-weight: 600; color: #475569; }
    
    /* Action Buttons (Icons) */
    div.stButton > button[key^="d_"] { background-color: #dcfce7 !important; color: #166534 !important; height: 50px !important; border-radius: 15px !important; }
    div.stButton > button[key^="e_"] { background-color: #fef9c3 !important; color: #854d0e !important; height: 50px !important; border-radius: 15px !important; }
    div.stButton > button[key^="x_"] { background-color: #fee2e2 !important; color: #991b1b !important; height: 50px !important; border-radius: 15px !important; }

    </style>
    """, unsafe_allow_html=True)

# --- 2. ZUGANG & LOGIK ---
try:
    S_URL, S_KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    supabase = create_client(S_URL, S_KEY)
except:
    st.error("Konfiguration fehlt.")
    st.stop()

if 'page' not in st.session_state: st.session_state.page = "🏠 Home"
if 'edit_id' not in st.session_state: st.session_state.edit_id = None

# --- HEADER & NAVIGATION ---
st.markdown("""<div class="app-header"><h1>WerkOS Pro</h1><p>Digital Foreman</p></div>""", unsafe_allow_html=True)

if st.session_state.page != "🏠 Home":
    if st.button("⬅️ ZURÜCK", key="back_to_menu", use_container_width=True):
        st.session_state.page = "🏠 Home"
        st.rerun()

# --- PROJECT SYNC ---
p_data = supabase.table("notes").select("project_name, content").execute()
all_projects = sorted(list(set([e['project_name'] for e in p_data.data if e.get('project_name')])))
archived_list = list(set([e['project_name'] for e in p_data.data if e['content'] == "PROJECT_ARCHIVED"]))

col_p, col_o = st.columns([4, 1])
with col_p:
    show_archived = st.checkbox("Archiv einblenden")
    display_list = all_projects if show_archived else [p for p in all_projects if p not in archived_list]
    curr_p = st.selectbox("📍 Baustelle", display_list if display_list else ["Allgemein"], label_visibility="collapsed")

with col_o:
    with st.popover("⚙️"):
        new_p = st.text_input("Name:")
        if st.button("Projekt anlegen", use_container_width=True):
            if new_p:
                supabase.table("notes").insert({"content": "Projektstart", "project_name": new_p, "category": "Notiz", "is_completed": False}).execute()
                st.rerun()
        if curr_p and curr_p != "Allgemein":
            st.divider()
            if curr_p not in archived_list:
                if st.button(f"📁 Archivieren", use_container_width=True):
                    supabase.table("notes").insert({"content": "PROJECT_ARCHIVED", "project_name": curr_p, "category": "System", "is_completed": True}).execute()
                    st.rerun()
            else:
                if st.button(f"🔓 Reaktivieren", use_container_width=True):
                    supabase.table("notes").delete().eq("project_name", curr_p).eq("content", "PROJECT_ARCHIVED").execute()
                    st.rerun()

st.divider()
is_archived = curr_p in archived_list

# --- PAGES ---
if st.session_state.page == "🏠 Home":
    st.markdown("<div style='margin-bottom:10px; font-weight:700; color:#1e293b;'>MENÜ</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📋\nBOARD", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
        if st.button("📦\nLAGER", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    with c2:
        if st.button("⏱️\nZEITEN", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()
        if st.button("📊\nSTATISTIK", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()

elif st.session_state.page == "📊 Dashboard":
    st.subheader(f"Statistik: {curr_p}")
    res = supabase.table("notes").select("*").eq("project_name", curr_p).neq("content", "PROJECT_ARCHIVED").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Gesamtkosten", f"{df['cost_amount'].sum():.2f} €")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())

elif st.session_state.page == "📋 Board":
    if is_archived:
        st.warning("Projekt archiviert.")
    else:
        with st.expander("➕ NEUER EINTRAG"):
            with st.form("new_e", clear_on_submit=True):
                t = st.text_input("Was gibt es zu tun?")
                k = st.select_slider("Wichtigkeit", options=["Notiz", "Aufgabe", "Wichtig"])
                c = st.number_input("Kosten €", min_value=0.0, step=10.0)
                if st.form_submit_button("SPEICHERN", use_container_width=True):
                    supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute()
                    st.rerun()
            
            st.write("📷 Foto")
            img = st.camera_input("Kamera", label_visibility="collapsed")
            if img:
                fn = f"{datetime.datetime.now().strftime('%H%M%S')}.jpg"
                supabase.storage.from_("werkos_fotos").upload(fn, img.getvalue())
                url = supabase.storage.from_("werkos_fotos").get_public_url(fn)
                supabase.table("notes").insert({"content":"Foto", "category":"Notiz", "project_name":curr_p, "image_url":url, "is_completed":False}).execute()
                st.rerun()

            st.write("🎤 Audio")
            audio_data = audio_recorder(text="", icon_size="2x", key="audio_v31")
            if audio_data and st.button("💾 SPEICHERN"):
                afn = f"rec_{datetime.datetime.now().strftime('%H%M%S')}.mp3"
                supabase.storage.from_("werkos_fotos").upload(afn, audio_data)
                a_url = supabase.storage.from_("werkos_fotos").get_public_url(afn)
                supabase.table("notes").insert({"content": "Sprachnotiz", "category": "Notiz", "project_name": curr_p, "audio_url": a_url, "is_completed": False}).execute()
                st.rerun()

    # Cards Rendering
    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).neq("content", "PROJECT_ARCHIVED").order("created_at", desc=True).execute()
    for e in res.data:
        cat_class = f"card-{e['category'].lower()}"
        if st.session_state.edit_id == e['id']:
            with st.form(f"edit_{e['id']}"):
                nt = st.text_input("Inhalt", value=e['content'])
                nc = st.number_input("Kosten", value=float(e.get('cost_amount', 0)))
                if st.form_submit_button("Speichern"):
                    supabase.table("notes").update({"content": nt, "cost_amount": nc}).eq("id", e['id']).execute()
                    st.session_state.edit_id = None
                    st.rerun()
        else:
            st.markdown(f"""
                <div class="card {cat_class}">
                    <div class="status-pill card-{e['category'].lower()}">{e['category']}</div>
                    <div style="font-size: 1.1rem; font-weight: 600; color: #1e293b;">{e['content']}</div>
                    <div style="margin-top: 10px; color: #64748b; font-size: 0.9rem;">
                        <span>💰 {e.get('cost_amount',0):.2f} €</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if e.get("image_url"): st.image(e["image_url"], use_container_width=True)
            if e.get("audio_url"): st.audio(e["audio_url"])
            if not is_archived:
                c1, c2, c3 = st.columns(3)
                if c1.button("✅", key=f"d_{e['id']}"):
                    supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute(); st.rerun()
                if c2.button("✏️", key=f"e_{e['id']}"):
                    st.session_state.edit_id = e['id']; st.rerun()
                if c3.button("🗑️", key=f"x_{e['id']}"):
                    supabase.table("notes").delete().eq("id", e['id']).execute(); st.rerun()

elif st.session_state.page == "📦 Lager":
    st.subheader("Lager")
    m_res = supabase.table("materials").select("*").execute()
    # Design-technisch sind hier Tabs oft schöner als Expander
    tab_inv, tab_use = st.tabs(["📥 Inventur", "📤 Verbrauch"])
    with tab_inv:
        with st.form("m_update"):
            sel_m = st.selectbox("Material", [i['name'] for i in m_res.data])
            new_q = st.number_input("Bestand anpassen", min_value=0.0)
            if st.form_submit_button("AKTUALISIEREN", use_container_width=True):
                info = next(i for i in m_res.data if i['name'] == sel_m)
                supabase.table("materials").update({"stock_quantity": new_q}).eq("id", info['id']).execute()
                st.rerun()
    with tab_use:
        if is_archived: st.error("Archiviert.")
        else:
            with st.form("m_book"):
                sel = st.selectbox("Material wählen", [i['name'] for i in m_res.data])
                q = st.number_input("Verbrauchte Menge", min_value=1.0)
                if st.form_submit_button("AUF PROJEKT BUCHEN", use_container_width=True):
                    info = next(i for i in m_res.data if i['name'] == sel)
                    supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":info['price_per_unit']*q, "is_completed":False}).execute()
                    supabase.table("materials").update({"stock_quantity": float(info['stock_quantity'])-q}).eq("id", info['id']).execute()
                    st.rerun()
    st.divider()
    for m in m_res.data:
        st.write(f"**{m['name']}**: {m['stock_quantity']} Einheiten")

elif st.session_state.page == "⏱️ Zeiten":
    st.subheader("Arbeitszeit buchen")
    if is_archived: st.error("Archiviert.")
    else:
        s_res = supabase.table("staff").select("*").execute()
        if s_res.data:
            with st.form("s_book"):
                sel_s = st.selectbox("Mitarbeiter", [i['name'] for i in s_res.data])
                h = st.number_input("Stunden (h)", min_value=0.5, step=0.5)
                if st.form_submit_button("ZEIT BUCHEN", use_container_width=True):
                    s = next(i for i in s_res.data if i['name'] == sel_s)
                    supabase.table("notes").insert({"content":f"{sel_s}: {h}h", "category":"Aufgabe", "project_name":curr_p, "cost_amount":s['hourly_rate']*h, "is_completed":False}).execute()
                    st.rerun()
