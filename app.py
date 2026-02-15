import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
from fpdf import FPDF
import pandas as pd
import os

# --- 1. APP CONFIG ---
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

# --- 2. MODERN APP STYLING (CSS) ---
st.markdown("""
    <style>
    /* Hintergrund und Header */
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; background-color: #F0F2F6; }
    .main .block-container {padding-top: 1rem;}
    
    /* Buttons als große Touch-Flächen */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5rem;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Cards für Board-Einträge */
    .board-card {
        background: white;
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border-left: 5px solid #007bff;
    }
    
    /* Navigation oben fixieren */
    .nav-box {
        background-color: white;
        padding: 10px;
        border-radius: 15px;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ZUGANG ---
try:
    S_URL, S_KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
except:
    S_URL = st.sidebar.text_input("URL", value="https://sjviyysbjozculvslrdy.supabase.co")
    S_KEY = st.sidebar.text_input("Key", type="password")

if S_URL and S_KEY:
    supabase = create_client(S_URL, S_KEY)
else:
    st.stop()

# --- 4. NAVIGATION (JETZT ALS REITER OBEN) ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏗️ WerkOS Pro</h1>", unsafe_allow_html=True)

# Navigation über Radio-Buttons im "Button-Look"
page = st.selectbox("📂 Menü wählen:", ["📊 Dashboard", "📋 Board", "📦 Lager", "⏱️ Zeiten"], index=1)

# Projektwahl
p_res = supabase.table("notes").select("project_name").execute()
p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))
curr_p = st.selectbox("📍 Aktuelle Baustelle:", p_list if p_list else ["Allgemein"])

st.divider()

# --- SEITE 1: DASHBOARD ---
if page == "📊 Dashboard":
    st.subheader("Projekt-Übersicht")
    res = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        c1, c2 = st.columns(2)
        c1.metric("Kosten", f"{df['cost_amount'].sum():.2f} €")
        c2.metric("Einträge", len(df))
        st.bar_chart(df.groupby('category')['cost_amount'].sum())
    
    # Lager-Warnung
    m_check = supabase.table("materials").select("*").execute()
    if m_check.data:
        low = [m for m in m_check.data if float(m.get('stock_quantity',0)) <= float(m.get('min_stock',5))]
        for l in low:
            st.error(f"⚠️ Lager leer: {l['name']} ({l['stock_quantity']} rest)")

# --- SEITE 2: BOARD ---
elif page == "📋 Board":
    with st.expander("➕ Neuer Eintrag / Foto / Audio"):
        with st.form("entry"):
            t = st.text_input("Notiz/Aufgabe")
            k = st.selectbox("Kat", ["Notiz", "Aufgabe", "Material", "Wichtig"])
            c = st.number_input("Kosten €", min_value=0.0)
            if st.form_submit_button("SPEICHERN"):
                supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute()
                st.rerun()
        
        # Media direkt im Expander
        img = st.camera_input("Kamera")
        if img:
            fn = f"{datetime.datetime.now().strftime('%H%M%S')}.jpg"
            supabase.storage.from_("werkos_fotos").upload(fn, img.getvalue())
            url = supabase.storage.from_("werkos_fotos").get_public_url(fn)
            supabase.table("notes").insert({"content":"Foto-Notiz", "category":"Notiz", "project_name":curr_p, "image_url":url, "is_completed":False}).execute()
            st.rerun()
        
        aud = audio_recorder(text="🎤 Audio aufnehmen", icon_size="2x")
        if aud:
            supabase.table("notes").insert({"content":"Audio-Notiz", "category":"Notiz", "project_name":curr_p, "is_completed":False}).execute()
            st.rerun()

    st.write("### Aktuelle Liste")
    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).order("created_at", desc=True).execute()
    for e in res.data:
        st.markdown(f"""<div class='board-card'><strong>{e['category']}</strong>: {e['content']}<br><small>{e.get('cost_amount', 0)} €</small></div>""", unsafe_allow_html=True)
        if e.get("image_url"): st.image(e["image_url"])
        if st.button("Erledigt ✅", key=e['id']):
            supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute()
            st.rerun()

# --- SEITE 3: LAGER ---
elif page == "📦 Lager":
    st.subheader("Lager & Buchung")
    m_res = supabase.table("materials").select("*").execute()
    if m_res.data:
        df_m = pd.DataFrame(m_res.data)
        st.dataframe(df_m[['name', 'stock_quantity']], use_container_width=True)
        
        with st.form("book"):
            sel = st.selectbox("Material:", df_m['name'].tolist())
            q = st.number_input("Menge entnommen", min_value=1.0)
            if st.form_submit_button("ABBUCHEN"):
                info = next(i for i in m_res.data if i['name'] == sel)
                supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":info['price_per_unit']*q, "is_completed":False}).execute()
                supabase.table("materials").update({"stock_quantity": float(info['stock_quantity'])-q}).eq("id", info['id']).execute()
                st.rerun()

# --- SEITE 4: ZEIT ---
elif page == "⏱️ Zeiten":
    st.subheader("Stunden buchen")
    s_res = supabase.table("staff").select("*").execute()
    if s_res.data:
        with st.form("time"):
            sel_s = st.selectbox("Mitarbeiter", [i['name'] for i in s_res.data])
            h = st.number_input("Stunden", min_value=0.5, step=0.5)
            if st.form_submit_button("BUCHEN"):
                s = next(i for i in s_res.data if i['name'] == sel_s)
                supabase.table("notes").insert({"content":f"{sel_s}: {h}h", "category":"Aufgabe", "project_name":curr_p, "cost_amount":s['hourly_rate']*h, "is_completed":False}).execute()
                st.rerun()

# Footer / PDF
st.divider()
if st.button("📄 PDF BERICHT ERSTELLEN"):
    st.info("PDF wird generiert...")
