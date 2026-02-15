import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd

# --- 1. APP CONFIG & APP DESIGN (v2.32 - STRIKTE FUNKTIONS-TREUE) ---
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    :root {
        --primary: #1e3a8a;
        --bg: #F8FAFC;
    }

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: var(--bg); }

    .app-header {
        background: linear-gradient(180deg, #1e3a8a 0%, #1e40af 100%);
        padding: 25px 20px;
        border-radius: 0 0 30px 30px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .stButton>button {
        border-radius: 24px !important;
        background: white !important;
        color: #1e3a8a !important;
        font-weight: 700 !important;
        height: 110px !important;
        box-shadow: 0 8px 20px rgba(0,0,0,0.04) !important;
        border: 1px solid #edf2f7 !important;
    }

    /* STATUS-AMPEL FIX (EXAKT WIE IN v2.26/v2.30) */
    .card {
        background: white !important;
        padding: 20px;
        border-radius: 24px;
        margin-bottom: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.03);
        border: 1px solid #f1f5f9;
        position: relative;
    }
    
    .card-notiz { border-left: 12px solid #3498db !important; }
    .card-aufgabe { border-left: 12px solid #f1c40f !important; }
    .card-wichtig { border-left: 12px solid #e74c3c !important; }
    .card-material { border-left: 12px solid #95a5a6 !important; }

    div.stButton > button[key^="d_"] { background-color: #dcfce7 !important; color: #166534 !important; height: 45px !important; border-radius: 12px !important; }
    div.stButton > button[key^="e_"] { background-color: #fef9c3 !important; color: #854d0e !important; height: 45px !important; border-radius: 12px !important; }
    div.stButton > button[key^="x_"] { background-color: #fee2e2 !important; color: #991b1b !important; height: 45px !important; border-radius: 12px !important; }
    
    div.stButton > button[key="back_to_menu"] { 
        background-color: transparent !important; border: 1px solid white !important; color: white !important; height: 40px !important;
    }

    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. ZUGANG ---
try:
    S_URL, S_KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    supabase = create_client(S_URL, S_KEY)
except:
    st.error("Konfiguration fehlt.")
    st.stop()

if 'page' not in st.session_state: st.session_state.page = "🏠 Home"
if 'edit_id' not in st.session_state: st.session_state.edit_id = None

# --- HEADER ---
st.markdown("""<div class="app-header"><h1>WerkOS Pro</h1><p>Digital Foreman</p></div>""", unsafe_allow_html=True)

if st.session_state.page != "🏠 Home":
    if st.button("⬅️ MENÜ", key="back_to_menu", use_container_width=True):
        st.session_state.page = "🏠 Home"
        st.rerun()

# --- DATEN & ARCHIV LOGIK ---
p_data = supabase.table("notes").select("project_name, content").execute()
all_projects = sorted(list(set([e['project_name'] for e in p_data.data if e.get('project_name')])))
archived_list = list(set([e['project_name'] for e in p_data.data if e['content'] == "PROJECT_ARCHIVED"]))

show_archived = st.checkbox("Archivierte Projekte einblenden")
active_projects = [p for p in all_projects if p not in archived_list]
display_list = all_projects if show_archived else active_projects

col_p, col_o = st.columns([4, 1])
with col_p:
    curr_p = st.selectbox("📍 Projekt wählen:", display_list if display_list else ["Allgemein"], label_visibility="collapsed")
with col_o:
    with st.popover("⚙️"):
        new_p = st.text_input("Name:")
        if st.button("Projekt anlegen", use_container_width=True):
            if new_p:
                supabase.table("notes").insert({"content": "Projektstart", "project_name": new_p, "category": "Notiz", "is_completed": False}).execute(); st.rerun()
        if curr_p and curr_p != "Allgemein":
            st.divider()
            if curr_p not in archived_list:
                if st.button("📁 Archivieren", use_container_width=True):
                    supabase.table("notes").insert({"content": "PROJECT_ARCHIVED", "project_name": curr_p, "category": "System", "is_completed": True}).execute(); st.rerun()
            else:
                if st.button("🔓 Reaktivieren", use_container_width=True):
                    supabase.table("notes").delete().eq("project_name", curr_p).eq("content", "PROJECT_ARCHIVED").execute(); st.rerun()

is_archived = curr_p in archived_list
st.divider()

# --- SEITEN LOGIK ---
if st.session_state.page == "🏠 Home":
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📋\nBOARD", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
        if st.button("📦\nLAGER", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    with c2:
        if st.button("⏱️\nZEITEN", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()
        if st.button("📊\nDASHBOARD", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()

elif st.session_state.page == "📊 Dashboard":
    st.subheader(f"Dashboard: {curr_p}")
    res = supabase.table("notes").select("*").eq("project_name", curr_p).neq("content", "PROJECT_ARCHIVED").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Gesamtkosten", f"{df['cost_amount'].sum():.2f} €")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())

elif st.session_state.page == "📋 Board":
    if is_archived:
        st.warning("🔒 Archiviert - Keine Bearbeitung möglich.")
    else:
        with st.expander("➕ NEUER EINTRAG"):
            with st.form("new_e"):
                t = st.text_input("Titel")
                k = st.selectbox("Kategorie", ["Notiz", "Aufgabe", "Wichtig"])
                c = st.number_input("Kosten €", min_value=0.0)
                if st.form_submit_button("SPEICHERN"):
                    supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute(); st.rerun()
            
            img = st.camera_input("Foto")
            if img:
                fn = f"{datetime.datetime.now().strftime('%H%M%S')}.jpg"
                supabase.storage.from_("werkos_fotos").upload(fn, img.getvalue())
                url = supabase.storage.from_("werkos_fotos").get_public_url(fn)
                supabase.table("notes").insert({"content":"Foto", "category":"Notiz", "project_name":curr_p, "image_url":url, "is_completed":False}).execute(); st.rerun()
            
            st.write("🎤 Audio:")
            audio_data = audio_recorder(text="", icon_size="2x", key="audio_v32")
            if audio_data and st.button("💾 SPEICHERN"):
                afn = f"rec_{datetime.datetime.now().strftime('%H%M%S')}.mp3"
                supabase.storage.from_("werkos_fotos").upload(afn, audio_data)
                a_url = supabase.storage.from_("werkos_fotos").get_public_url(afn)
                supabase.table("notes").insert({"content": "Sprachnotiz", "category": "Notiz", "project_name": curr_p, "audio_url": a_url, "is_completed": False}).execute(); st.rerun()

    # Board Liste
    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).neq("content", "PROJECT_ARCHIVED").order("created_at", desc=True).execute()
    for e in res.data:
        cat_class = f"card-{e['category'].lower()}"
        if st.session_state.edit_id == e['id']:
            with st.form(f"edit_{e['id']}"):
                nt = st.text_input("Inhalt", value=e['content'])
                nc = st.number_input("Kosten", value=float(e.get('cost_amount', 0)))
                if st.form_submit_button("Speichern"):
                    supabase.table("notes").update({"content": nt, "cost_amount": nc}).eq("id", e['id']).execute(); st.session_state.edit_id = None; st.rerun()
        else:
            st.markdown(f"""<div class="card {cat_class}"><strong>{e['category']}</strong><div style="font-weight:600;margin-top:5px;">{e['content']}</div><div style="color:#64748b;font-size:0.9rem;margin-top:5px;">💰 {e.get('cost_amount',0):.2f} €</div></div>""", unsafe_allow_html=True)
            if e.get("image_url"): st.image(e["image_url"])
            if e.get("audio_url"): st.audio(e["audio_url"])
            if not is_archived:
                c1, c2, c3 = st.columns(3)
                if c1.button("✅", key=f"d_{e['id']}"): supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute(); st.rerun()
                if c2.button("✏️", key=f"e_{e['id']}"): st.session_state.edit_id = e['id']; st.rerun()
                if c3.button("🗑️", key=f"x_{e['id']}"): supabase.table("notes").delete().eq("id", e['id']).execute(); st.rerun()

elif st.session_state.page == "📦 Lager":
    st.subheader("📦 Lager")
    m_res = supabase.table("materials").select("*").execute()
    # ZWEIGETEILTES LAGER (EXAKT v2.26)
    tab1, tab2 = st.tabs(["📥 Bestand korrigieren (Inventur)", "📤 Verbrauch verbuchen (Kosten)"])
    with tab1:
        with st.form("m_update"):
            sel_m = st.selectbox("Produkt wählen", [i['name'] for i in m_res.data])
            new_q = st.number_input("Neuer Ist-Bestand", min_value=0.0)
            if st.form_submit_button("BESTAND ÜBERSCHREIBEN"):
                info = next(i for i in m_res.data if i['name'] == sel_m)
                supabase.table("materials").update({"stock_quantity": new_q}).eq("id", info['id']).execute(); st.rerun()
    with tab2:
        if not is_archived:
            with st.form("m_book"):
                sel = st.selectbox("Material wählen", [i['name'] for i in m_res.data])
                q = st.number_input("Verbrauchte Menge", min_value=1.0)
                if st.form_submit_button("VERBRAUCH BUCHEN"):
                    info = next(i for i in m_res.data if i['name'] == sel)
                    supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":info['price_per_unit']*q, "is_completed":False}).execute()
                    supabase.table("materials").update({"stock_quantity": float(info['stock_quantity'])-q}).eq("id", info['id']).execute(); st.rerun()
    for m in m_res.data: st.write(f"📦 **{m['name']}**: {m['stock_quantity']}")

elif st.session_state.page == "⏱️ Zeiten":
    st.subheader("⏱️ Arbeitszeiten")
    if not is_archived:
        s_res = supabase.table("staff").select("*").execute()
        if s_res.data:
            with st.form("s_book"):
                sel_s = st.selectbox("Wer?", [i['name'] for i in s_res.data])
                h = st.number_input("Stunden", min_value=0.5, step=0.5)
                if st.form_submit_button("BUCHEN"):
                    s = next(i for i in s_res.data if i['name'] == sel_s)
                    supabase.table("notes").insert({"content":f"{sel_s}: {h}h", "category":"Aufgabe", "project_name":curr_p, "cost_amount":s['hourly_rate']*h, "is_completed":False}).execute(); st.rerun()
