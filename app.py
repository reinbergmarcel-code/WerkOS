import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd

# --- 1. APP CONFIG & NATIVE APP STYLING (v2.22 Standard) ---
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC; }
    .app-header { background: #1e3a8a; padding: 1.5rem; border-radius: 0 0 20px 20px; color: white; text-align: center; margin-bottom: 1rem; }
    .card { background: white; padding: 1.2rem; border-radius: 16px; margin-bottom: 1rem; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab-list"] { background-color: white; padding: 10px; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    header {visibility: hidden;} footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. ZUGANG ---
try:
    S_URL, S_KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    supabase = create_client(S_URL, S_KEY)
except:
    st.error("Konfiguration fehlt.")
    st.stop()

# --- 3. APP LOGIC ---
st.markdown('<div class="app-header"><h1>WerkOS Pro</h1></div>', unsafe_allow_html=True)

p_res = supabase.table("notes").select("project_name").execute()
p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))
curr_p = st.selectbox("📍 Projekt", p_list if p_list else ["Allgemein"])

tab_board, tab_lager, tab_zeiten, tab_dash = st.tabs(["📋 Board", "📦 Lager", "⏱️ Zeiten", "📊 Statistik"])

# --- TAB: BOARD (Identisch zu v2.22/23) ---
with tab_board:
    # ... (Code wie v2.23)
    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).order("created_at", desc=True).execute()
    for e in res.data:
        st.markdown(f'<div class="card"><strong>{e["category"]}</strong><br>{e["content"]}</div>', unsafe_allow_html=True)
        # Buttons etc...

# --- TAB: LAGER (ERWEITERT) ---
with tab_lager:
    st.subheader("📦 Lagerbestand & Verwaltung")
    
    m_res = supabase.table("materials").select("*").execute()
    
    # 1. BESTANDSÜBERSICHT
    if m_res.data:
        df_m = pd.DataFrame(m_res.data)
        for _, m in df_m.iterrows():
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.write(f"**{m['name']}** ({m['price_per_unit']} €/Einheit)")
                st.progress(min(max(float(m['stock_quantity'])/100, 0.0), 1.0))
            with col_b:
                st.write(f"**{m['stock_quantity']}**")
    
    st.divider()
    
    # 2. LAGER-AKTIONEN
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("📥 Bestand auffüllen / Korrektur"):
            with st.form("inventory_adj"):
                sel_m = st.selectbox("Material wählen", [i['name'] for i in m_res.data], key="adj_m")
                new_qty = st.number_input("Neuer Gesamtbestand", min_value=0.0, step=1.0)
                if st.form_submit_button("Bestand aktualisieren"):
                    info = next(i for i in m_res.data if i['name'] == sel_m)
                    supabase.table("materials").update({"stock_quantity": new_qty}).eq("id", info['id']).execute()
                    st.success(f"Bestand für {sel_m} auf {new_qty} gesetzt.")
                    st.rerun()

    with col2:
        with st.expander("📤 Material verbrauchen (Baustelle)"):
            with st.form("inventory_use"):
                sel_u = st.selectbox("Material wählen", [i['name'] for i in m_res.data], key="use_m")
                use_qty = st.number_input("Verbrauchte Menge", min_value=1.0, step=1.0)
                if st.form_submit_button("Auf Projekt buchen"):
                    info = next(i for i in m_res.data if i['name'] == sel_u)
                    # Kosten buchen
                    total_c = info['price_per_unit'] * use_qty
                    supabase.table("notes").insert({
                        "content": f"Verbrauch: {use_qty}x {sel_u}",
                        "category": "Material",
                        "project_name": curr_p,
                        "cost_amount": total_c,
                        "is_completed": False
                    }).execute()
                    # Bestand reduzieren
                    supabase.table("materials").update({"stock_quantity": float(info['stock_quantity']) - use_qty}).eq("id", info['id']).execute()
                    st.rerun()

    st.divider()
    
    # 3. NEUES MATERIAL ANLEGEN
    with st.expander("➕ Neues Material-Produkt anlegen"):
        with st.form("new_material"):
            n_m = st.text_input("Bezeichnung (z.B. Zementsack 25kg)")
            p_m = st.number_input("Preis pro Einheit (€)", min_value=0.0)
            s_m = st.number_input("Anfangsbestand", min_value=0.0)
            if st.form_submit_button("Produkt anlegen"):
                supabase.table("materials").insert({"name": n_m, "price_per_unit": p_m, "stock_quantity": s_m}).execute()
                st.rerun()

# --- TAB: ZEITEN & DASHBOARD (Unverändert) ---
# ...
