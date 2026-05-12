import streamlit as st
import pandas as pd
import gspread
import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

# ==========================================
# 0. CONFIGURACION Y SEGURIDAD
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH_CREDS = os.path.join(BASE_DIR, 'config', 'sunhaven-credentials.json')

st.set_page_config(page_title="Sunhaven | Operational Intelligence", layout="wide", initial_sidebar_state="expanded")

# --- DISEÑO CORPORATIVO REFINADO ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .block-container { padding-top: 1.5rem; max-width: 95%; }
    h1, h2, h3 { color: #1e293b; font-weight: 800; letter-spacing: -0.5px; }
    .exec-header {
        background-color: #ffffff; padding: 2rem; border-radius: 4px;
        border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center;
    }
    .kpi-card {
        background-color: #ffffff; padding: 25px; border-radius: 4px;
        border: 1px solid #e2e8f0; text-align: center;
        transition: all 0.3s ease;
    }
    .kpi-card:hover { border-color: #94a3b8; background-color: #f8fafc; }
    .metric-label { font-size: 12px; color: #64748b; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 34px; font-weight: 800; color: #0f172a; margin: 0; }
    .footer-watermark { text-align: center; margin-top: 80px; opacity: 0.3; font-size: 11px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #f1f5f9; border-radius: 4px; padding: 10px 20px; font-weight: 600; color: #475569; }
    .stTabs [aria-selected="true"] { background-color: #1e293b !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

HEX_NAVY = "#1e293b"
HEX_RED = "#dc2626"
HEX_GREEN = "#16a34a"

# --- REGLAS DE NEGOCIO ---
ENFERMERAS_ROL_A = ["Consuelo Ceja Liborio", "Jaqueline Hernández Sosa"]
ENFERMERAS_ROL_B = ["Silvia Rodríguez Reynaga", "Guadalupe Georgia Lopez Ceja"]

# ==========================================
# 1. MOTOR DE DATOS
# ==========================================
@st.cache_data(ttl=600)
def cargar_datos_maestros():
    try:
        if "GOOGLE_JSON" in st.secrets:
            gc = gspread.service_account_from_dict(json.loads(st.secrets["GOOGLE_JSON"]))
        else:
            gc = gspread.service_account(filename=PATH_CREDS)
            
        sh_n = gc.open_by_url("https://docs.google.com/spreadsheets/d/10wWKmjsyj501OXaFWs7Rd_XF_2R-H0YzV66B2K6HvPE/edit").get_worksheet(0)
        sh_v = gc.open_by_url("https://docs.google.com/spreadsheets/d/1C1AVmNXG0ggRekB1HF4_IhX-NGiTkwzgvZn2Z31rCsc/edit").get_worksheet(0)
        sh_s = gc.open_by_url("https://docs.google.com/spreadsheets/d/1wdP3mbW_k4a90ubPG-ZQy8FvfAZiwKnhPjCj1BZHcBs/edit").get_worksheet(0)
        
        dfs = {
            "n": pd.DataFrame(sh_n.get_all_records()),
            "v": pd.DataFrame(sh_v.get_all_records()),
            "s": pd.DataFrame(sh_s.get_all_records())
        }
        for k in dfs:
            dfs[k].columns = dfs[k].columns.str.strip().str.replace('\n', ' ')
        return dfs
    except Exception as e:
        st.error(f"Falla de conexion: {e}")
        st.stop()

# ==========================================
# 2. INTERFAZ Y PROCESAMIENTO
# ==========================================
def main():
    with st.sidebar:
        st.markdown("### SISTEMA OPERATIVO SUNHAVEN")
        st.divider()
        if st.button("Sincronizar Base de Datos", use_container_width=True):
            cargar_datos_maestros.clear()
            st.rerun()
            
        # RANGO DE FECHAS MEJORADO
        hoy = datetime.now()
        treinta_dias_atras = hoy - timedelta(days=30)
        fechas = st.date_input("Seleccionar Rango de Análisis", [treinta_dias_atras, hoy])
        
        if len(fechas) == 2:
            fecha_inicio, fecha_fin = fechas
        else:
            st.stop()
        
        st.divider()
        st.markdown("### GENERACION DE REPORTES")
        if st.button("Reporte de Operaciones (PDF)", use_container_width=True):
            subprocess.run([sys.executable, os.path.join(BASE_DIR, 'tools', 'bot_operaciones.py')])
            st.success("Operaciones PDF listo.")
        if st.button("Reporte Legal / Normativo (PDF)", use_container_width=True):
            st.info("Generando reporte de cumplimiento legal...")
            # Aquí se conectará tu formato legal
            
    data = cargar_datos_maestros()
    df_ron, df_rop, df_serv = data["n"].copy(), data["v"].copy(), data["s"].copy()

    try:
        def traducir(serie):
            mapeo = {'sí': 10, 'si': 10, 'no': 0, 'cumple': 10, 'no cumple': 0, 'separada': 10, 'bien': 10, 'ok': 10, 'limpio': 10, 'sucio': 0}
            return pd.to_numeric(serie.astype(str).str.strip().str.lower().replace(mapeo), errors='coerce') * 10

        # Mapeo de columnas
        c_5s = [c for c in df_rop.columns if "Orden" in c][0]
        c_cam = [c for c in df_rop.columns if "Tendido" in c][0]
        col_enf = [c for c in df_rop.columns if "enfermera" in c.lower()][0]
        c_uni = [c for c in df_serv.columns if "uniforme" in c.lower()][0]
        c_bas = [c for c in df_serv.columns if "basura" in c.lower()][0]
        c_lav_r = [c for c in df_serv.columns if "ropa" in c.lower() or "separad" in c.lower()][0]
        c_lav_j = [c for c in df_serv.columns if "jabón" in c.lower() or "jabon" in c.lower()][0]
        c_lim = [c for c in df_serv.columns if "zonas asignadas" in c.lower()][0]

        # Procesar Fechas
        for df in [df_ron, df_rop, df_serv]:
            df['Marca temporal'] = pd.to_datetime(df['Marca temporal'], dayfirst=True, errors='coerce')
            df['Fecha'] = df['Marca temporal'].dt.date
            
        # Filtrar por Rango
        df_ron = df_ron[(df_ron['Fecha'] >= fecha_inicio) & (df_ron['Fecha'] <= fecha_fin)]
        df_rop = df_rop[(df_rop['Fecha'] >= fecha_inicio) & (df_rop['Fecha'] <= fecha_fin)]
        df_serv = df_serv[(df_serv['Fecha'] >= fecha_inicio) & (df_serv['Fecha'] <= fecha_fin)]

        # Limpieza de valores
        for c in [c_5s, c_cam]: df_rop[c] = traducir(df_rop[c])
        df_rop['Promedio'] = (df_rop[c_5s] + df_rop[c_cam]) / 2
        for c in [c_uni, c_bas, c_lav_r, c_lav_j, c_lim]: df_serv[c] = traducir(df_serv[c])

        # --- CALCULO NOCTURNO (ALGORITMO RONDINES) ---
        turnos_A = sum(1 for d in pd.date_range(fecha_inicio, fecha_fin) if d.weekday() in [0, 2, 4])
        turnos_B = sum(1 for d in pd.date_range(fecha_inicio, fecha_fin) if d.weekday() in [1, 3, 5])
        
        df_ron['Hora'] = df_ron['Marca temporal'].dt.hour
        def get_bloque(h):
            if 21 <= h <= 23: return "B1"
            if 0 <= h <= 3: return "B2"
            if 4 <= h <= 6: return "B3"
            return None
        df_ron['Bloque'] = df_ron['Hora'].apply(get_bloque)
        
        pct_nocturnos = {}
        for enf in ENFERMERAS_ROL_A + ENFERMERAS_ROL_B:
            meta = (turnos_A if enf in ENFERMERAS_ROL_A else turnos_B) * 3
            realizadas = len(df_ron[(df_ron['Enfermera'] == enf) & (df_ron['Bloque'].notnull())][['Fecha', 'Bloque']].drop_duplicates())
            pct_nocturnos[enf] = min((realizadas / meta * 100), 100) if meta > 0 else 100
        
        val_nocturno = sum(pct_nocturnos.values()) / len(pct_nocturnos)

        # KPIs Maestro
        areas_kpi = {
            "Nocturno": val_nocturno,
            "Vespertino": df_rop['Promedio'].mean(),
            "Cocina": (df_serv[c_uni].mean() + df_serv[c_bas].mean()) / 2,
            "Lavandería": (df_serv[c_lav_r].mean() + df_serv[c_lav_j].mean()) / 2,
            "Limpieza": df_serv[c_lim].mean()
        }
        areas_kpi = {k: (v if pd.notna(v) else 0) for k, v in areas_kpi.items()}
        ico_master = sum(areas_kpi.values()) / len(areas_kpi)

    except Exception as e:
        st.error(f"Error: {e}")
        ico_master = 0

    # --- HEADER ---
    st.markdown(f"""<div class='exec-header'>
        <div><p style='margin:0; font-weight:700; color:#64748b; font-size:12px; letter-spacing:1px; text-transform:uppercase;'>Estatus Institucional</p>
        <h2 style='margin:0; color:{HEX_GREEN if ico_master >= 90 else HEX_RED};'>{"ESTABLE" if ico_master >= 90 else "ATENCION REQUERIDA"}</h2></div>
        <div style='text-align:right;'><p style='margin:0; font-weight:700; color:#64748b; font-size:12px; letter-spacing:1px; text-transform:uppercase;'>ICO Maestro</p>
        <h1 style='margin:0; font-size:48px;'>{ico_master:.1f}%</h1></div>
    </div>""", unsafe_allow_html=True)

    tabs = st.tabs(["Tablero de Control", "Evolución Temporal", "Rendimiento Individual", "Blindaje Legal", "Auditoría"])

    with tabs[0]:
        cols = st.columns(5)
        for i, (area, valor) in enumerate(areas_kpi.items()):
            with cols[i]:
                st.markdown(f"<div class='kpi-card'><p class='metric-label'>{area}</p><p class='metric-value'>{valor:.1f}%</p></div>", unsafe_allow_html=True)
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.write("### Pareto por Área")
            df_a = pd.DataFrame.from_dict(areas_kpi, orient='index', columns=['V']).sort_values('V', ascending=False).reset_index()
            fig = px.bar(df_a, x='index', y='V', text_auto='.1f', color_discrete_sequence=[HEX_NAVY])
            fig.add_hline(y=90, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.write("### Análisis de Causa Raíz")
            # Agregamos los criterios base
            crit = {"Uniforme": df_serv[c_uni].mean(), "Basura": df_serv[c_bas].mean(), "Ropa": df_serv[c_lav_r].mean(), "Jabón": df_serv[c_lav_j].mean(), "Zonas": df_serv[c_lim].mean(), "5S": df_rop[c_5s].mean(), "Camas": df_rop[c_cam].mean(), "Nocturno": val_nocturno}
            df_c = pd.DataFrame.from_dict(crit, orient='index', columns=['V']).sort_values('V', ascending=True).reset_index()
            fig_c = px.bar(df_c, x='V', y='index', orientation='h', text_auto='.1f', color_discrete_sequence=[HEX_RED])
            st.plotly_chart(fig_c, use_container_width=True)

    with tabs[1]:
        st.write("### Evolución Histórica de KPIs por Área")
        # Generar data de tiempo
        df_time_v = df_rop.groupby('Fecha')['Promedio'].mean()
        df_time_s = df_serv.groupby('Fecha')[[c_uni, c_bas, c_lav_r, c_lav_j, c_lim]].mean().mean(axis=1)
        
        df_evol = pd.DataFrame({"Vespertino": df_time_v, "Servicios": df_time_s}).fillna(method='ffill')
        fig_evol = px.line(df_evol, labels={"value": "Cumplimiento (%)", "Fecha": "Día"}, color_discrete_sequence=[HEX_NAVY, HEX_GREEN])
        fig_evol.add_hline(y=90, line_dash="dot", line_color="red")
        st.plotly_chart(fig_evol, use_container_width=True)

    with tabs[2]:
        st.write("### Rendimiento Detallado por Personal")
        personal = sorted(list(set(df_rop[col_enf].unique()).union(set(ENFERMERAS_NOCHE := ENFERMERAS_ROL_A + ENFERMERAS_ROL_B))))
        sel = st.selectbox("Seleccionar Colaborador", personal)
        
        c_p1, c_p2 = st.columns(2)
        if sel in pct_nocturnos:
            c_p1.metric("Cumplimiento Nocturno", f"{pct_nocturnos[sel]:.1f}%")
        
        df_sel_v = df_rop[df_rop[col_enf] == sel]
        if not df_sel_v.empty:
            c_p2.metric("Cumplimiento Vespertino", f"{df_sel_v['Promedio'].mean():.1f}%")
            st.dataframe(df_sel_v[['Fecha', c_5s, c_cam, 'Promedio']], use_container_width=True)

    with tabs[3]:
        st.write("### Checklist de Blindaje Institucional")
        st.progress(0.75)
        st.caption("Estatus preventivo ante auditorías externas.")

    with tabs[4]:
        st.write("### Consola de Verificación")
        st.dataframe(df_serv.head(10), use_container_width=True)

    st.markdown("<div class='footer-watermark'>Sunhaven Intelligence Suite - Enterprise Edition</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()