import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd

# --- 1. APP CONFIG & ORIGINAL STYLING ---
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
    }
    
    .stButton>button {
        border-radius: 18px !important;
        height: 4rem !important;
        font-weight: 600 !important;
    }

    /* STATUS-AMPEL CSS */
    .card-notiz { border-left: 10px solid #3498db !important; }
    .card-aufgabe { border-left: 10px solid #f1c40f !important; }
    .card-wichtig { border-left: 10px solid #e74c3c !important; }
    .card-material { border-left: 10px solid #95a5a6 !important; }

    .card {
        background: white;
        padding: 20px;
        border-radius: 20px;
        margin-bottom: 15px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.03);
    }
    
    header {visibility: hidden;}
    footer {visibility: hidden;}

    iframe[title="audio_recorder_streamlit.audio_recorder"] {
        min-height: 100px !important;
        display: block !important;
    }

    div.stButton > button[key^="d_"] { background-color: #2ecc71 !important; color: white !important; height: 3rem !important; }
    div.stButton > button[key^="e_"] { background-color: #f1c40f !important; color: black !important; height: 3rem !important; }
    div.stButton > button[key^="x_"] { background-color: #e74c3c !important; color: white !important; height: 3rem !important; }
    
    div.stButton > button[key="back_to_menu"] { 
        background-color: #1e3a8a !important; 
        color: white !important; 
        height: 3rem !important;
        margin-bottom: 20px !important;
    }
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

# --- HEADER & BACK BUTTON ---
st.markdown("""<div class="app-header"><h1>🏗️ WerkOS Pro</h1><p>Digitales Baustellenmanagement</p></div>""", unsafe_allow_html=True)

if st.session_state.page != "🏠 Home":
    if st.button("⬅️ ZURÜCK ZUM MENÜ", key="back_to_menu", use_container_width=True):
        st.session_state.page = "🏠 Home"
        st.rerun()

# Projektwahl
p_res = supabase.table("notes").select("project_name").execute()
p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))
c_top1, c_top2 = st.columns([3,1])
curr_p = c_top1.selectbox("📍 Baustelle:", p_list if p_list else ["Allgemein"])
with c_top2:
    with st.popover("➕ Projekt"):
        new_p = st.text_input("Name:")
        if st.button("Anlegen"):
            if new_p:
                supabase.table("notes").insert({"content": "Start", "project_name": new_p, "category": "Notiz", "is_completed": False}).execute()
                st.rerun()
st.divider()

# --- SEITEN LOGIK ---
if st.session_state.page == "🏠 Home":
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊\nDASHBOARD", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()
        if st.button("📦\nLAGER", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    with col2:
        if st.button("📋\nBOARD", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
        if st.button("⏱️\nZEITEN", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()

elif st.session_state.page == "📊 Dashboard":
    st.markdown(f"### 📊 Dashboard: {curr_p}")
    res = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Gesamtkosten", f"{df['cost_amount'].sum():.2f} €")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())

elif st.session_state.page == "📋 Board":
    with st.expander("➕ NEUER EINTRAG / FOTO / AUDIO"):
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

        st.markdown("---")
        st.write("🎤 Sprachnotiz:")
        audio_data = audio_recorder(text="Aufnahme", icon_size="3x", key="audio_v26_final")
        
        if audio_data:
            st.audio(audio_data)
            if st.button("💾 AUDIO SPEICHERN"):
                afn = f"rec_{datetime.datetime.now().strftime('%H%M%S')}.mp3"
                supabase.storage.from_("werkos_fotos").upload(afn, audio_data)
                a_url = supabase.storage.from_("werkos_fotos").get_public_url(afn)
                supabase.table("notes").insert({"content": "Sprachnotiz", "category": "Notiz", "project_name": curr_p, "audio_url": a_url, "is_completed": False}).execute()
                st.rerun()

    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).order("created_at", desc=True).execute()
    for e in res.data:
        # AMPEL LOGIK ZUWEISUNG
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
            st.markdown(f"""<div class="card {cat_class}"><strong>{e['category']}</strong><br>{e['content']}<br><small>{e.get('cost_amount',0)} €</small></div>""", unsafe_allow_html=True)
            if e.get("image_url"): st.image(e["image_url"])
            if e.get("audio_url"): st.audio(e["audio_url"])
            c1, c2, c3 = st.columns(3)
            if c1.button("✅", key=f"d_{e['id']}"):
                supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute(); st.rerun()
            if c2.button("✏️", key=f"e_{e['id']}"):
                st.session_state.edit_id = e['id']; st.rerun()
            if c3.button("🗑️", key=f"x_{e['id']}"):
                supabase.table("notes").delete().eq("id", e['id']).execute(); st.rerun()

elif st.session_state.page == "📦 Lager":
    st.markdown("### 📦 Lager")
    m_res = supabase.table("materials").select("*").execute()
    
    with st.expander("📥 BESTAND AKTUALISIEREN / LIEFERUNG"):
        with st.form("m_update"):
            sel_m = st.selectbox("Material:", [i['name'] for i in m_res.data])
            new_q = st.number_input("Neuer Ist-Bestand", min_value=0.0)
            if st.form_submit_button("Bestand überschreiben"):
                info = next(i for i in m_res.data if i['name'] == sel_m)
                supabase.table("materials").update({"stock_quantity": new_q}).eq("id", info['id']).execute()
                st.rerun()

    with st.expander("📤 MATERIAL VERBRAUCHEN (BUCHUNG)"):
        with st.form("m_book"):
            sel = st.selectbox("Material:", [i['name'] for i in m_res.data], key="consume")
            q = st.number_input("Menge", min_value=1.0)
            if st.form_submit_button("Verbuchen"):
                info = next(i for i in m_res.data if i['name'] == sel)
                supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":info['price_per_unit']*q, "is_completed":False}).execute()
                supabase.table("materials").update({"stock_quantity": float(info['stock_quantity'])-q}).eq("id", info['id']).execute()
                st.rerun()

    if m_res.data:
        for m in m_res.data: st.write(f"📦 {m['name']}: {m['stock_quantity']}")
    
    with st.expander("➕ NEUES PRODUKT ANLEGEN"):
        with st.form("m_add"):
            n = st.text_input("Name")
            p = st.number_input("Preis")
            s = st.number_input("Anfangsbestand")
            if st.form_submit_button("Anlegen"):
                supabase.table("materials").insert({"name":n, "price_per_unit":p, "stock_quantity":s}).execute()
                st.rerun()

elif st.session_state.page == "⏱️ Zeiten":
    # ... (Stunden-Logik wie v2.22/v2.25)
    st.markdown("### ⏱️ Zeiten")
    s_res = supabase.table("staff").select("*").execute()
    if s_res.data:
        with st.form("s_book"):
            sel_s = st.selectbox("Wer?", [i['name'] for i in s_res.data])
            h = st.number_input("Stunden", min_value=0.5, step=0.5)
            if st.form_submit_button("Buchen"):
                s = next(i for i in s_res.data if i['name'] == sel_s)
                supabase.table("notes").insert({"content":f"{sel_s}: {h}h", "category":"Aufgabe", "project_name":curr_p, "cost_amount":s['hourly_rate']*h, "is_completed":False}).execute()
                st.rerun()
