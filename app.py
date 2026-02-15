import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd

# 1. DATENBANK-SETUP
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Verbindung fehlgeschlagen."); st.stop()

# 2. APP-STEUERUNG
if 'page' not in st.session_state: st.session_state.page = "🏠 Home"
if 'edit_id' not in st.session_state: st.session_state.edit_id = None

st.title("WerkOS Pro")

# 3. DATEN ABFRAGEN
res = supabase.table("notes").select("*").execute()
all_data = res.data if res.data else []
all_p = sorted(list(set([e['project_name'] for e in all_data if e.get('project_name')])))
arch_p = list(set([e['project_name'] for e in all_data if e['content'] == "PROJECT_ARCHIVED"]))

# 4. KOPFZEILE (PROJEKTE)
c1, c2 = st.columns([3, 1])
with c1:
    show_arch = st.checkbox("Archiv anzeigen")
    curr_p = st.selectbox("📍 Baustelle", [p for p in all_p if p not in arch_p] if not show_arch else all_p)
with c2:
    with st.popover("➕ Neu"):
        np = st.text_input("Projektname:")
        if st.button("Anlegen"):
            if np: 
                supabase.table("notes").insert({"content": "Start", "project_name": np, "category": "Notiz", "is_completed": False}).execute()
                st.rerun()

is_archived = curr_p in arch_p
if curr_p and curr_p != "Allgemein":
    if not is_archived:
        if st.button(f"📁 '{curr_p}' ARCHIVIEREN", use_container_width=True):
            supabase.table("notes").insert({"content": "PROJECT_ARCHIVED", "project_name": curr_p, "category": "System", "is_completed": True}).execute()
            st.rerun()
    else:
        if st.button(f"🔓 '{curr_p}' REAKTIVIEREN", use_container_width=True):
            supabase.table("notes").delete().eq("project_name", curr_p).eq("content", "PROJECT_ARCHIVED").execute()
            st.rerun()

st.divider()

# 5. NAVIGATION
if st.session_state.page == "🏠 Home":
    col1, col2 = st.columns(2)
    if col1.button("📋 BOARD", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
    if col1.button("📦 LAGER", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    if col2.button("⏱️ ZEITEN", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()
    if col2.button("📊 STATS", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()

elif st.session_state.page == "📋 Board":
    if st.button("⬅️ MENÜ"): st.session_state.page = "🏠 Home"; st.rerun()
    if not is_archived:
        with st.expander("➕ EINTRAG"):
            audio_recorder(text="Sprachaufnahme")
            st.camera_input("Foto")
            with st.form("nb"):
                t = st.text_input("Titel/Notiz")
                k = st.selectbox("Kategorie", ["Notiz", "Aufgabe", "Wichtig"])
                c = st.number_input("Kosten €", value=0.0)
                if st.form_submit_button("Speichern"):
                    supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute()
                    st.rerun()

    items = [e for e in all_data if e['project_name'] == curr_p and not e['is_completed'] and e['content'] != "PROJECT_ARCHIVED"]
    for e in items:
        if st.session_state.edit_id == e['id']:
            with st.form(f"ed_{e['id']}"):
                nt = st.text_input("Ändern", value=e['content'])
                if st.form_submit_button("OK"):
                    supabase.table("notes").update({"content": nt}).eq("id", e['id']).execute()
                    st.session_state.edit_id = None; st.rerun()
        else:
            st.info(f"**{e['category']}**: {e['content']} (💰 {e.get('cost_amount',0)}€)")
            if not is_archived:
                b1, b2, b3 = st.columns(3)
                if b1.button("✅", key=f"d_{e['id']}"): 
                    supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute(); st.rerun()
                if b2.button("✏️", key=f"e_{e['id']}"): 
                    st.session_state.edit_id = e['id']; st.rerun()
                if b3.button("🗑️", key=f"x_{e['id']}"): 
                    supabase.table("notes").delete().eq("id", e['id']).execute(); st.rerun()

elif st.session_state.page == "📦 Lager":
    if st.button("⬅️ MENÜ"): st.session_state.page = "🏠 Home"; st.rerun()
    materials = supabase.table("materials").select("*").execute().data
    t1, t2 = st.tabs(["📥 Inventur", "📤 Verbrauch"])
    with t1:
        with st.form("inv"):
            sel = st.selectbox("Material", [i['name'] for i in materials])
            q = st.number_input("Aktueller Bestand", step=1.0)
            if st.form_submit_button("Bestand setzen"):
                mid = next(i for i in materials if i['name'] == sel)['id']
                supabase.table("materials").update({"stock_quantity": q}).eq("id", mid).execute(); st.rerun()
    with t2:
        if not is_archived:
            with st.form("cons"):
                sel = st.selectbox("Was wurde genutzt?", [i['name'] for i in materials])
                q = st.number_input("Menge", step=1.0)
                if st.form_submit_button("Buchen"):
                    m = next(i for i in materials if i['name'] == sel)
                    supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":m['price_per_unit']*q, "is_completed":False}).execute()
                    supabase.table("materials").update({"stock_quantity": float(m['stock_quantity'])-q}).eq("id", m['id']).execute(); st.rerun()
    for m in materials:
        st.write(f"📦 {m['name']}: **{m['stock_quantity']}**")
