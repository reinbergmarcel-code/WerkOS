import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
from fpdf import FPDF
import pandas as pd

# --- 1. ZUGANG ---
try:
    S_URL = st.secrets["SUPABASE_URL"]
    S_KEY = st.secrets["SUPABASE_KEY"]
except:
    S_URL = st.sidebar.text_input("URL", value="https://sjviyysbjozculvslrdy.supabase.co")
    S_KEY = st.sidebar.text_input("Key", type="password")

if S_URL and S_KEY:
    supabase = create_client(S_URL, S_KEY)
else:
    st.stop()

# --- 2. TOOLS ---
def speech_to_text(audio_bytes):
    return f"Sprachaufnahme {datetime.datetime.now().strftime('%H:%M')}"

def create_pdf(data, p_name, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Projekt: {p_name} | Gesamt: {total:.2f} EUR", ln=True)
    for e in data:
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, f"{e.get('category')} - {e.get('created_at','')[:10]}", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 7, f"{e.get('content')} | {e.get('cost_amount',0)} EUR")
    return bytes(pdf.output())

st.set_page_config(page_title="WerkOS Pro", layout="wide")

# --- 3. NAVI ---
page = st.sidebar.radio("Menü", ["📊 Dash", "📋 Board", "📦 Lager", "⏱️ Zeit"])
p_res = supabase.table("notes").select("project_name").execute()
p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))
curr_p = st.sidebar.selectbox("Projekt:", p_list if p_list else ["Allgemein"])
if st.sidebar.text_input("✨ Neu:"): curr_p = st.sidebar.text_input("✨ Neu:")

# --- SEITE 1: DASH ---
if page == "📊 Dash":
    st.title(f"📊 {curr_p}")
    m_check = supabase.table("materials").select("*").execute()
    if m_check.data:
        low = [m for m in m_check.data if float(m.get('stock_quantity',0)) <= float(m.get('min_stock',5))]
        if low: st.warning(f"⚠️ {len(low)} Artikel fast leer!")
    res = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Gesamtkosten", f"{df['cost_amount'].sum():.2f} €")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())

# --- SEITE 2: BOARD ---
elif page == "📋 Board":
    st.subheader(f"Board: {curr_p}")
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.form("f1", clear_on_submit=True):
            t = st.text_input("Titel")
            kat = st.selectbox("Kat", ["Notiz", "Aufgabe", "Material", "Wichtig"])
            cost = st.number_input("€", min_value=0.0)
            if st.form_submit_button("OK") and t:
                supabase.table("notes").insert({"content":t, "category":kat, "project_name":curr_p, "cost_amount":cost, "is_completed":False}).execute()
                st.rerun()
    with c2:
        img = st.camera_input("Foto")
        if img:
            fn = f"{datetime.datetime.now().strftime('%H%M%S')}.jpg"
            supabase.storage.from_("werkos_fotos").upload(fn, img.getvalue())
            url = supabase.storage.from_("werkos_fotos").get_public_url(fn)
            supabase.table("notes").insert({"content":"Foto", "category":"Notiz", "project_name":curr_p, "image_url":url, "is_completed":False}).execute()
            st.rerun()
        if audio_recorder():
            supabase.table("notes").insert({"content":"Audio", "category":"Notiz", "project_name":curr_p, "is_completed":False}).execute()
            st.rerun()
    
    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).order("created_at", desc=True).execute()
    for e in res.data:
        st.write(f"**{e['category']}** ({e['cost_amount']}€): {e['content']}")
        if e.get("image_url"): st.image(e["image_url"])
        if st.button("✅", key=e['id']):
            supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute()
            st.rerun()

# --- SEITE 3: LAGER ---
elif page == "📦 Lager":
    st.subheader("📦 Lager")
    with st.expander("Neu"):
        with st.form("f2"):
            n = st.text_input("Name")
            p = st.number_input("Preis")
            s = st.number_input("Bestand")
            l = st.number_input("Limit", value=5.0)
            if st.form_submit_button("Save"):
                supabase.table("materials").insert({"name":n, "price_per_unit":p, "stock_quantity":s, "min_stock":l}).execute()
                st.rerun()
    m_res = supabase.table("materials").select("*").execute()
    if m_res.data:
        df_m = pd.DataFrame(m_res.data)
        # Kurze Logik für Status-Spalte
        df_m['Status'] = df_m.apply(lambda x: "⚠️" if float(x['stock_quantity']) <= float(x['min_stock']) else "✅", axis=1)
        st.table(df_m[['name', 'stock_quantity', 'Status']])
        with st.form("f3"):
            sel = st.selectbox("Nutzen:", df_m['name'].tolist())
            q = st.number_input("Menge", min_value=1.0)
            if st.form_submit_button("Buchen"):
                info = next(i for i in m_res.data if i['name'] == sel)
                supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":info['price_per_unit']*q, "is_completed":False}).execute()
                supabase.table("materials").update({"stock_quantity": float(info['stock_quantity'])-q}).eq("id", info['id']).execute()
                st.rerun()

# --- SEITE 4: ZEIT ---
elif page == "⏱️ Zeit":
    st.subheader("⏱️ Zeit")
    with st.expander("Mitarbeiter"):
        with st.form("f4"):
            sn = st.text_input("Name")
            sr = st.number_input("Satz", value=45.0)
            if st.form_submit_button("Save"):
                supabase.table("staff").insert({"name":sn, "hourly_rate":sr}).execute()
                st.rerun()
    s_res = supabase.table("staff").select("*").execute()
    if s_res.data:
        s_dict = {i['name']: i for i in s_res.data}
        with st.form("f5"):
            sel_s = st.selectbox("Wer?", list(s_dict.keys()))
            h = st.number_input("Stunden", min_value=0.5, step=0.5)
            if st.form_submit_button("Buchen"):
                s = s_dict[sel_s]
                supabase.table("notes").insert({"content":f"{sel_s}: {h}h", "category":"Aufgabe", "project_name":curr_p, "cost_amount":s['hourly_rate']*h, "is_completed":False}).execute()
                st.rerun()

if st.sidebar.button("📄 PDF"):
    r = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
