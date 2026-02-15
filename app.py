import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
from fpdf import FPDF
import pandas as pd

# --- 1. APP-KONFIGURATION (Für das App-Feeling) ---
st.set_page_config(
    page_title="WerkOS Pro",
    page_icon="🏗️", # Dies wird dein App-Icon auf dem Handy
    layout="wide",
    initial_sidebar_state="collapsed" # Sidebar am Handy standardmäßig zu für mehr Platz
)

# --- CSS FÜR MOBILE OPTIMIERUNG ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #007bff; color: white; }
    iframe { border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ZUGANG ---
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

# --- 3. TOOLS ---
def speech_to_text(audio_bytes):
    return f"Sprachaufnahme {datetime.datetime.now().strftime('%H:%M')}"

def create_pdf(data, p_name, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Bericht: {p_name} | {total:.2f} EUR", ln=True)
    for e in data:
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, f"{e.get('category')} - {e.get('created_at','')[:10]}", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 7, f"{e.get('content')} | {e.get('cost_amount',0)} EUR")
    return bytes(pdf.output())

# --- 4. NAVI ---
# Ein etwas schöneres Menü in der Sidebar
st.sidebar.title("🏗️ WerkOS Menu")
page = st.sidebar.radio("Navigation", ["📊 Dash", "📋 Board", "📦 Lager", "⏱️ Zeit"])

p_res = supabase.table("notes").select("project_name").execute()
p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))
curr_p = st.sidebar.selectbox("Aktives Projekt:", p_list if p_list else ["Allgemein"])
new_p = st.sidebar.text_input("✨ Neues Projekt:")
if new_p: curr_p = new_p

# --- SEITE 1: DASH ---
if page == "📊 Dash":
    st.title(f"📊 {curr_p}")
    m_check = supabase.table("materials").select("*").execute()
    if m_check.data:
        low = [m for m in m_check.data if float(m.get('stock_quantity',0)) <= float(m.get('min_stock',5))]
        if low: st.error(f"⚠️ {len(low)} Artikel im Lager fast leer!")
    
    res = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        c1, c2 = st.columns(2)
        c1.metric("Kosten", f"{df['cost_amount'].sum():.2f} €")
        c2.metric("Einträge", len(df))
        st.divider()
        st.subheader("Kosten nach Kategorie")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())

# --- SEITE 2: BOARD ---
elif page == "📋 Board":
    st.subheader(f"Board: {curr_p}")
    c1, c2 = st.columns([1, 1])
    with c1:
        with st.form("f1", clear_on_submit=True):
            t = st.text_input("Titel / Info")
            kat = st.selectbox("Kat", ["Notiz", "Aufgabe", "Material", "Wichtig"])
            cost = st.number_input("Kosten €", min_value=0.0)
            if st.form_submit_button("Eintragen") and t:
                supabase.table("notes").insert({"content":t, "category":kat, "project_name":curr_p, "cost_amount":cost, "is_completed":False}).execute()
                st.rerun()
    with c2:
        img = st.camera_input("Foto aufnehmen")
        if img:
            fn = f"{datetime.datetime.now().strftime('%H%M%S')}.jpg"
            supabase.storage.from_("werkos_fotos").upload(fn, img.getvalue())
            url = supabase.storage.from_("werkos_fotos").get_public_url(fn)
            supabase.table("notes").insert({"content":"Foto-Notiz", "category":"Notiz", "project_name":curr_p, "image_url":url, "is_completed":False}).execute()
            st.rerun()
        
        st.write("🎤 Sprachnotiz")
        aud = audio_recorder(text="", icon_size="2x")
        if aud:
            supabase.table("notes").insert({"content":speech_to_text(aud), "category":"Notiz", "project_name":curr_p, "is_completed":False}).execute()
            st.rerun()
    
    st.divider()
    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).order("created_at", desc=True).execute()
    for e in res.data:
        with st.expander(f"{e['category']} - {e['cost_amount']}€"):
            st.write(e['content'])
            if e.get("image_url"): st.image(e["image_url"])
            if st.button("✅ Erledigt", key=e['id']):
                supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute()
                st.rerun()

# --- SEITE 3: LAGER ---
elif page == "📦 Lager":
    st.subheader("📦 Lager-Kontrolle")
    with st.expander("Neues Material erfassen"):
        with st.form("f2"):
            n = st.text_input("Bezeichnung")
            p = st.number_input("Preis")
            s = st.number_input("Ist-Bestand")
            l = st.number_input("Warn-Limit", value=5.0)
            if st.form_submit_button("Speichern"):
                supabase.table("materials").insert({"name":n, "price_per_unit":p, "stock_quantity":s, "min_stock":l}).execute()
                st.rerun()
    
    m_res = supabase.table("materials").select("*").execute()
    if m_res.data:
        df_m = pd.DataFrame(m_res.data)
        df_m['Status'] = df_m.apply(lambda x: "🔴" if float(x['stock_quantity']) <= float(x['min_stock']) else "🟢", axis=1)
        st.table(df_m[['name', 'stock_quantity', 'Status']])
        
        with st.form("f3"):
            sel = st.selectbox("Entnahme für Baustelle:", df_m['name'].tolist())
            q = st.number_input("Menge", min_value=1.0)
            if st.form_submit_button("Jetzt buchen"):
                info = next(i for i in m_res.data if i['name'] == sel)
                supabase.table("notes").insert({"content":f"{q}x {sel} verbaut", "category":"Material", "project_name":curr_p, "cost_amount":info['price_per_unit']*q, "is_completed":False}).execute()
                supabase.table("materials").update({"stock_quantity": float(info['stock_quantity'])-q}).eq("id", info['id']).execute()
                st.rerun()

# --- SEITE 4: ZEIT ---
elif page == "⏱️ Zeit":
    st.subheader("⏱️ Zeiterfassung")
    with st.expander("Mitarbeiter verwalten"):
        with st.form("f4"):
            sn = st.text_input("Name")
            sr = st.number_input("Lohn/Std", value=45.0)
            if st.form_submit_button("Anlegen"):
                supabase.table("staff").insert({"name":sn, "hourly_rate":sr}).execute()
                st.rerun()
    
    s_res = supabase.table("staff").select("*").execute()
    if s_res.data:
        s_dict = {i['name']: i for i in s_res.data}
        with st.form("f5"):
            sel_s = st.selectbox("Wer arbeitet?", list(s_dict.keys()))
            h = st.number_input("Stunden", min_value=0.5, step=0.5)
            if st.form_submit_button("Zeit buchen"):
                s = s_dict[sel_s]
                supabase.table("notes").insert({"content":f"{sel_s}: {h} Std.", "category":"Aufgabe", "project_name":curr_p, "cost_amount":s['hourly_rate']*h, "is_completed":False}).execute()
                st.rerun()

# --- PDF EXPORT ---
if st.sidebar.button("📄 Projekt-Bericht erzeugen"):
    r = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
    pdf_data = create_pdf(r.data, curr_p, sum([float(x['cost_amount']) for x in r.data]))
    st.sidebar.download_button("Datei herunterladen", pdf_data, f"Bericht_{curr_p}.pdf")
