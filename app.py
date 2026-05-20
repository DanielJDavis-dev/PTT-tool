import streamlit as st
import json
import csv
from pathlib import Path
from jinja2 import Template

st.set_page_config(page_title="PTT Generator — DSV", page_icon="📄", layout="centered")

TEMPLATES_DIR = Path("templates")
AIRLINES_CSV  = Path("data/airlines.csv")

# ─── Load airlines ────────────────────────────────────────────────────────────
@st.cache_data
def load_airlines():
    code3_to_iata = {}
    code3_to_name = {}
    with open(AIRLINES_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code3 = str(row.get("3 digit code", "")).strip().zfill(3)
            iata  = row.get("IATA Designator", "").strip()
            name  = row.get("Airline Name", "").strip()
            if code3 and code3 != "000":
                code3_to_iata[code3] = iata
                code3_to_name[code3] = name
    return code3_to_iata, code3_to_name

# ─── Load templates ───────────────────────────────────────────────────────────
def load_templates():
    templates = {}
    for f in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            templates[data["name"]] = data
        except Exception as e:
            st.warning(f"No se pudo cargar {f.name}: {e}")
    return templates

# ─── Render HTML from template ────────────────────────────────────────────────
def render_html(tpl_data, values):
    return Template(tpl_data["html_template"]).render(**values)

# ─── Print button — opens new tab with print dialog ──────────────────────────
def print_button(html_content, filename):
    # Encode HTML and open in new tab with auto-print
    import base64
    b64 = base64.b64encode(html_content.encode("utf-8")).decode()
    st.markdown(f"""
    <a href="data:text/html;base64,{b64}" download="{filename.replace('.pdf','.html')}" target="_blank"
       id="printlink"
       style="display:inline-block;padding:12px 32px;background:#c0392b;color:white;
              border-radius:6px;text-decoration:none;font-weight:700;font-size:15px;margin-top:10px">
       🖨️ Abrir documento para imprimir / guardar PDF
    </a>
    <p style="font-size:12px;color:#666;margin-top:8px">
      👆 Se abrirá en una nueva pestaña → usa <b>Ctrl+P</b> (o Cmd+P en Mac) → <b>Guardar como PDF</b>
    </p>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# UI
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
.block-container{padding-top:1.8rem;max-width:740px}
h1{color:#1a1a2e;font-size:1.55rem;margin-bottom:0}
.airline-badge{background:#fff3cd;border:1px solid #ffc107;border-radius:6px;
               padding:6px 14px;font-size:.9rem;font-weight:600;color:#856404;
               display:inline-block;margin-top:4px}
</style>
""", unsafe_allow_html=True)

st.title("📄 PTT / Customs Transfer Generator")
st.caption("Genera los documentos de transferencia aduanal para DSV")
st.divider()

code3_to_iata, code3_to_name = load_airlines()
templates = load_templates()

if not templates:
    st.error("No hay plantillas en la carpeta `templates/`.")
    st.stop()

# ── Template selector ─────────────────────────────────────────────────────────
selected = st.selectbox("🗂️ Selecciona la plantilla", list(templates.keys()))
tpl = templates[selected]
if tpl.get("description"):
    st.caption(tpl["description"])
st.divider()

st.subheader("✏️ Llena los campos")

col1, col2 = st.columns(2)
with col1:
    fecha = st.text_input("📅 Date (MM/DD/YYYY)", placeholder="5/16/2026")
with col2:
    firms = st.selectbox("🔑 Confirm Firms Code", ["Y807", "WAG6", "W274", "Y652"])

st.markdown("---")
st.markdown("**✈️ Master Air Waybill (MAWB)**")
mawb_full = st.text_input(
    "Pega o escribe el MAWB completo", placeholder="001-22762132",
    help="Formato: XXX-XXXXXXXX — se separa automáticamente y busca la aerolínea"
)

mawb_prefix = mawb_suffix = iata_auto = airline_name_auto = ""

if mawb_full.strip():
    parts = mawb_full.strip().replace(" ", "").split("-")
    if len(parts) == 2:
        mawb_prefix, mawb_suffix = parts[0].zfill(3), parts[1]
    elif len(parts) == 1 and len(parts[0]) >= 3:
        mawb_prefix, mawb_suffix = parts[0][:3].zfill(3), parts[0][3:]
    else:
        mawb_prefix = parts[0] if parts else ""
    iata_auto         = code3_to_iata.get(mawb_prefix, "")
    airline_name_auto = code3_to_name.get(mawb_prefix, "")

col_p, col_s = st.columns([1, 2])
with col_p:
    st.text_input("Prefijo (3 dígitos)", value=mawb_prefix, disabled=True)
with col_s:
    st.text_input("Número restante", value=mawb_suffix, disabled=True)

if iata_auto:
    st.markdown(f'<div class="airline-badge">✅ {iata_auto} — {airline_name_auto}</div>',
                unsafe_allow_html=True)
elif mawb_prefix:
    st.warning(f"Código `{mawb_prefix}` no encontrado. Verifica el MAWB.")

st.markdown("---")

col3, col4 = st.columns(2)
with col3:
    flight = st.text_input("🛫 Flight Number", placeholder="950")
with col4:
    aircraft_no = st.text_input("Aircraft NO", placeholder="(opcional)")

arrival_date = st.text_input("📆 Arrival Date", placeholder="MM/DD/YYYY")

col5, col6 = st.columns(2)
with col5:
    tacm = st.text_input("LAX manifest or port TACM NO.", placeholder="(opcional)")
with col6:
    hawb_count = st.text_input("Total Number of House Air Waybills", placeholder="ej. 1")

col7, col8 = st.columns(2)
with col7:
    packages = st.text_input("📦 Total Units / Packages", placeholder="4")
with col8:
    weight = st.text_input("⚖️ Total Weight", placeholder="86.80")

st.divider()

if st.button("📄 Generar Documento", type="primary", use_container_width=True):
    required = {"Date": fecha, "MAWB": mawb_full, "Flight": flight,
                "Packages": packages, "Weight": weight}
    missing = [k for k, v in required.items() if not str(v).strip()]

    if missing:
        st.error(f"Campos obligatorios vacíos: **{', '.join(missing)}**")
    elif not iata_auto:
        st.error(f"No se encontró aerolínea para el prefijo **{mawb_prefix}**.")
    else:
        values = {
            "fecha": fecha, "firms": firms,
            "iata": iata_auto, "airline_name": airline_name_auto,
            "flight": flight, "aircraft_no": aircraft_no,
            "arrival_date": arrival_date, "tacm": tacm,
            "mawb_full": f"{mawb_prefix}-{mawb_suffix}",
            "mawb_prefix": mawb_prefix, "mawb_suffix": mawb_suffix,
            "hawb_count": hawb_count, "packages": packages, "weight": weight,
        }
        html = render_html(tpl, values)
        filename = f"PTT_{mawb_prefix}-{mawb_suffix}_{fecha.replace('/', '-')}.pdf"
        st.success("✅ Documento listo")
        print_button(html, filename)
