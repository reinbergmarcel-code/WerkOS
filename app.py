import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd

# --- 1. APP CONFIG & NATIVE APP STYLING ---
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] { 
        font-family: 'Inter', sans-serif; 
        background-color: #F8FAFC; 
    }

    /* Modern App Header */
    .app-header {
        background: #1e3a8a;
        padding: 1.5rem;
        border-radius: 0 0 20px 20px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }

    /* Clean Card Design */
    .stMetric {
        background: white;
        padding: 15px !important;
        border-radius: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .card {
        background: white;
        padding: 1.2rem;
        border-radius: 16px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
    }

    /* Category Badges */
    .badge-wichtig { background-color: #fee2e2; color: #991b1b; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; }
    .badge-notiz { background-color: #e0e7ff; color: #3730a3; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; }
    .badge-aufgabe { background-color: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; }

    /* Bottom Navigation Simulation */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: white;
        padding: 10px;
        border-radius: 15px;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    }
    
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. ZUGANG (UNVERÄNDERT) ---
try:
    S_URL, S_KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    supabase = create_client(S_URL, S_KEY)
except:
    st.error("Konfiguration fehlt.")
    st.stop()

# --- 3. APP LOGIC ---
st.markdown('<div class="app-header"><h1>WerkOS Pro</h1></div>', unsafe_allow_html=True)

# Projekt-Selector (Immer oben präsent)
p_res = supabase.table("notes").select("project_name").execute()
p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))
curr_p = st.selectbox("📍 Aktuelles Projekt", p_list if p_list else ["Allgemein"])

# Haupt-Navigation als Tabs (Fühlt sich mehr nach App an)
tab_board, tab_lager, tab_zeiten, tab_dash = st.tabs(["📋 Board", "📦 Lager", "⏱️ Zeiten", "📊 Statistik"])

# --- TAB: BOARD ---
with tab_board:
    with st.expander("➕ Neuer Eintrag", expanded=False):
        with st.form("new_e"):
            t = st.text_input("Was ist zu tun?")
            k = st.selectbox("Kategorie", ["Aufgabe", "Notiz", "Wichtig"])
            c = st.number_input("Kosten €", min_value=0.0)
            if st.form_submit_button("Hinzufügen"):
                supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute()
                st.rerun()
        
        c1, c2 = st.columns(2)
        with c1:
            img = st.camera_input("Foto")
        with c2:
            st.write("🎤 Audio")
            audio_data = audio_recorder(text="", icon_size="2x", key="recorder_v23")
        
        if img:
            fn = f"{datetime.datetime.now().strftime('%H%M%S')}.jpg"
            supabase.storage.from_("werkos_fotos").upload(fn, img.getvalue())
            url = supabase.storage.from_("werkos_fotos").get_public_url(fn)
            supabase.table("notes").insert({"content":"Foto-Anhang", "category":"Notiz", "project_name":curr_p, "image_url":url, "is_completed":False}).execute()
            st.rerun()

        if audio_data:
            if st.button("💾 Audio speichern"):
                afn = f"rec_{datetime.datetime.now().strftime('%H%M%S')}.mp3"
                supabase.storage.from_("werkos_fotos").upload(afn, audio_data)
                a_url = supabase.storage.from_("werkos_fotos").get_public_url(afn)
                supabase.table("notes").insert({"content": "Sprachnotiz", "category": "Notiz", "project_name": curr_p, "audio_url": a_url, "is_completed": False}).execute()
                st.rerun()

    # Board Liste
    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).order("created_at", desc=True).execute()
    for e in res.data:
        badge_class = f"badge-{e['category'].lower()}"
        st.markdown(f"""
            <div class="card">
                <span class="{badge_class}">{e['category']}</span>
                <p style="font-size: 1.1rem; margin-top: 10px;"><strong>{e['content']}</strong></p>
                <p style="color: #64748b; font-size: 0.9rem;">💰 {e.get('cost_amount',0)} €</p>
            </div>
        """, unsafe_allow_html=True)
        
        if e.get("image_url"): st.image(e["image_url"], use_container_width=True)
        if e.get("audio_url"): st.audio(e["audio_url"])
        
        c1, c2, c3 = st.columns(3)
        if c1.button("✅", key=f"d_{e['id']}"):
            supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute(); st.rerun()
        if c2.button("✏️", key=f"e_{e['id']}"):
            st.session_state.edit_id = e['id']; st.rerun()
        if c3.button("🗑️", key=f"x_{e['id']}"):
            supabase.table("notes").delete().eq("id", e['id']).execute(); st.rerun()

# --- TAB: LAGER ---
with tab_lager:
    st.subheader("Lagerbestand")
    m_res = supabase.table("materials").select("*").execute()
    if m_res.data:
        for m in m_res.data:
            stock = m['stock_quantity']
            color = "red" if stock < 5 else "green"
            st.markdown(f"**{m['name']}**: <span style='color:{color};'>{stock} Einheiten</span>", unsafe_allow_html=True)
            st.progress(min(stock/20, 1.0)) # Beispiel-Progress-Bar
    
    with st.expander("Material verbuchen"):
        with st.form("m_book"):
            sel = st.selectbox("Material:", [i['name'] for i in m_res.data])
            q = st.number_input("Menge", min_value=1.0)
            if st.form_submit_button("Abbuche"):
                info = next(i for i in m_res.data if i['name'] == sel)
                supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":info['price_per_unit']*q, "is_completed":False}).execute()
                supabase.table("materials").update({"stock_quantity": float(info['stock_quantity'])-q}).eq("id", info['id']).execute()
                st.rerun()

# --- TAB: ZEITEN ---
with tab_zeiten:
    st.subheader("Stundenbuchung")
    s_res = supabase.table("staff").select("*").execute()
    if s_res.data:
        with st.form("s_book"):
            sel_s = st.selectbox("Mitarbeiter:", [i['name'] for i in s_res.data])
            h = st.number_input("Stunden", min_value=0.5, step=0.5)
            if st.form_submit_button("Buchen"):
                s = next(i for i in s_res.data if i['name'] == sel_s)
                supabase.table("notes").insert({"content":f"{sel_s}: {h}h", "category":"Aufgabe", "project_name":curr_p, "cost_amount":s['hourly_rate']*h, "is_completed":False}).execute()
                st.rerun()

# --- TAB: STATISTIK ---
with tab_dash:
    st.subheader("Übersicht")
    res = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Projektkosten Aktuell", f"{df['cost_amount'].sum():.2f} €")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())
