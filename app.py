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
from fpdf import FPDF

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

# --- PALETA PDF SUNHAVEN ---
C_NAVY = (31, 58, 82)
C_SUN = (211, 84, 0)
C_DARK = (44, 62, 80)
C_LIGHT = (245, 247, 248)

# --- REGLAS DE NEGOCIO ---
ENFERMERAS_ROL_A = ["Consuelo Ceja Liborio", "Jaqueline Hernández Sosa"]
ENFERMERAS_ROL_B = ["Silvia Rodríguez Reynaga", "Guadalupe Georgia Lopez Ceja"]

# ==========================================
# 1. MOTOR PDF LEGAL
# ==========================================
class LegalPDF(FPDF):
    def header(self):
        if self.page_no() == 1: return
        self.set_fill_color(*C_NAVY)
        self.rect(0, 0, 210, 26, 'F')
        self.set_fill_color(*C_SUN)
        self.rect(0, 26, 210, 1.5, 'F')
        self.set_y(9)
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, 'REPORTE EJECUTIVO - BLINDAJE NORMATIVO', 0, 1, 'C')
        self.ln(12)

    def footer(self):
        if self.page_no() == 1: return
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*C_NAVY)
        self.set_draw_color(*C_SUN)
        self.line(10, 282, 200, 282)
        self.set_x(10)
        self.cell(190, 10, f'Página {self.page_no()}', 0, 0, 'C')
        self.set_x(10)
        self.cell(190, 10, 'Ing. Larry Beresford', 0, 0, 'R')

    def cover_page(self, fecha_str):
        self.add_page()
        self.set_fill_color(*C_NAVY)
        self.rect(0, 0, 210, 100, 'F')
        self.set_fill_color(*C_SUN)
        self.rect(0, 100, 210, 3, 'F')
        self.set_y(40)
        self.set_font('Helvetica', 'B', 28)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, 'SUNHAVEN', 0, 1, 'C')
        self.set_font('Helvetica', '', 12)
        self.set_text_color(220, 220, 220)
        self.cell(0, 8, 'CASA DE DESCANSO PARA ADULTOS MAYORES', 0, 1, 'C')
        self.set_y(140)
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(*C_DARK)
        self.cell(0, 10, 'REPORTE EJECUTIVO', 0, 1, 'C')
        self.set_font('Helvetica', 'B', 26)
        self.set_text_color(*C_SUN)
        self.cell(0, 12, 'CUMPLIMIENTO LEGAL Y NORMATIVO', 0, 1, 'C')
        self.set_y(220)
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(*C_NAVY)
        self.cell(0, 8, f'FECHA DE EMISIÓN: {fecha_str}', 0, 1, 'C')
        self.set_y(260)
        self.set_font('Helvetica', '', 11)
        self.set_text_color(*C_DARK)
        self.cell(0, 6, 'Elaborado por:', 0, 1, 'C')
        self.set_font('Helvetica', 'B', 11)
        self.cell(0, 6, 'Ing. Larry Beresford', 0, 1, 'C')

def generar_pdf_legal_bytes(checks_dict, porcentaje):
    pdf = LegalPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.cover_page(datetime.now().strftime("%d/%m/%Y"))
    
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, "ESTATUS GLOBAL DE BLINDAJE INSTITUCIONAL", 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*C_DARK)
    pdf.cell(0, 8, f"Nivel de cumplimiento general de la institución: {porcentaje:.1f}%", 0, 1)
    pdf.ln(5)
    
    # Tabla de Checks
    pdf.set_fill_color(*C_NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(140, 8, "REQUISITO NORMATIVO", 1, 0, 'C', True)
    pdf.cell(50, 8, "ESTATUS", 1, 1, 'C', True)
    
    pdf.set_font('Helvetica', '', 10)
    fill_row = False
    
    for req, estado in checks_dict.items():
        pdf.set_fill_color(*C_LIGHT) if fill_row else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(*C_DARK)
        
        pdf.cell(140, 8, f" {req}", 1, 0, 'L', fill_row)
        
        if estado:
            pdf.set_text_color(39, 174, 96)
            txt_estado = "CUMPLE"
        else:
            pdf.set_text_color(231, 76, 60)
            txt_estado = "PENDIENTE"
            
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(50, 8, txt_estado, 1, 1, 'C', fill_row)
        pdf.set_font('Helvetica', '', 10)
        
        fill_row = not fill_row

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 2. MOTOR DE DATOS
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
# 3. INTERFAZ Y PROCESAMIENTO
# ==========================================
def main():
    with st.sidebar:
        st.markdown("### SISTEMA OPERATIVO SUNHAVEN")
        st.divider()
        if st.button("Sincronizar Base de Datos", use_container_width=True):
            cargar_datos_maestros.clear()
            st.rerun()
            
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
        if st.button("Reporte Rondines (PDF)", use_container_width=True):
            subprocess.run([sys.executable, os.path.join(BASE_DIR, 'tools', 'auditor_rondines.py')])
            st.success("Rondines PDF listo.")
            
    data = cargar_datos_maestros()
    df_ron, df_rop, df_serv = data["n"].copy(), data["v"].copy(), data["s"].copy()

    try:
        def traducir(serie):
            mapeo = {'sí': 10, 'si': 10, 'no': 0, 'cumple': 10, 'no cumple': 0, 'separada': 10, 'bien': 10, 'ok': 10, 'limpio': 10, 'sucio': 0}
            return pd.to_numeric(serie.astype(str).str.strip().str.lower().replace(mapeo), errors='coerce') * 10

        c_5s = [c for c in df_rop.columns if "Orden" in c][0]
        c_cam = [c for c in df_rop.columns if "Tendido" in c][0]
        col_enf = [c for c in df_rop.columns if "enfermera" in c.lower()][0]
        c_uni = [c for c in df_serv.columns if "uniforme" in c.lower()][0]
        c_bas = [c for c in df_serv.columns if "basura" in c.lower()][0]
        c_lav_r = [c for c in df_serv.columns if "ropa" in c.lower() or "separad" in c.lower()][0]
        c_lav_j = [c for c in df_serv.columns if "jabón" in c.lower() or "jabon" in c.lower()][0]
        c_lim = [c for c in df_serv.columns if "zonas asignadas" in c.lower()][0]

        for df in [df_ron, df_rop, df_serv]:
            df['Marca temporal'] = pd.to_datetime(df['Marca temporal'], dayfirst=True, errors='coerce')
            df['Fecha'] = df['Marca temporal'].dt.date
            
        df_ron = df_ron[(df_ron['Fecha'] >= fecha_inicio) & (df_ron['Fecha'] <= fecha_fin)]
        df_rop = df_rop[(df_rop['Fecha'] >= fecha_inicio) & (df_rop['Fecha'] <= fecha_fin)]
        df_serv = df_serv[(df_serv['Fecha'] >= fecha_inicio) & (df_serv['Fecha'] <= fecha_fin)]

        for c in [c_5s, c_cam]: df_rop[c] = traducir(df_rop[c])
        df_rop['Promedio'] = (df_rop[c_5s] + df_rop[c_cam]) / 2
        for c in [c_uni, c_bas, c_lav_r, c_lav_j, c_lim]: df_serv[c] = traducir(df_serv[c])

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
        
        val_nocturno = sum(pct_nocturnos.values()) / len(pct_nocturnos) if pct_nocturnos else 0

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
            crit = {"Uniforme": df_serv[c_uni].mean(), "Basura": df_serv[c_bas].mean(), "Ropa": df_serv[c_lav_r].mean(), "Jabón": df_serv[c_lav_j].mean(), "Zonas": df_serv[c_lim].mean(), "5S": df_rop[c_5s].mean(), "Camas": df_rop[c_cam].mean(), "Nocturno": val_nocturno}
            df_c = pd.DataFrame.from_dict(crit, orient='index', columns=['V']).sort_values('V', ascending=True).reset_index()
            fig_c = px.bar(df_c, x='V', y='index', orientation='h', text_auto='.1f', color_discrete_sequence=[HEX_RED])
            fig_c.add_vline(x=90, line_dash="dash", line_color="black")
            st.plotly_chart(fig_c, use_container_width=True)

    with tabs[1]:
        st.write("### Evolución Histórica de KPIs por Área")
        df_time_v = df_rop.groupby('Fecha')['Promedio'].mean()
        df_time_s = df_serv.groupby('Fecha')[[c_uni, c_bas, c_lav_r, c_lav_j, c_lim]].mean().mean(axis=1)
        df_evol = pd.DataFrame({"Vespertino": df_time_v, "Servicios": df_time_s}).ffill().fillna(0)
        fig_evol = px.line(df_evol, labels={"value": "Cumplimiento (%)", "Fecha": "Día"}, color_discrete_sequence=[HEX_NAVY, HEX_GREEN])
        fig_evol.add_hline(y=90, line_dash="dot", line_color="red")
        st.plotly_chart(fig_evol, use_container_width=True)

    with tabs[2]:
        st.write("### Rendimiento Detallado por Personal (Ranking)")
        
        # --- Construcción del Ranking Inteligente ---
        personal_total = sorted(list(set(df_rop[col_enf].dropna().unique()).union(set(ENFERMERAS_ROL_A + ENFERMERAS_ROL_B))))
        ranking_data = []
        
        for emp in personal_total:
            v_score = df_rop[df_rop[col_enf] == emp]['Promedio'].mean()
            n_score = pct_nocturnos.get(emp, None)
            
            if pd.notna(v_score) and n_score is not None:
                promedio_final = (v_score + n_score) / 2
                tipo = "Vespertino / Nocturno"
            elif pd.notna(v_score):
                promedio_final = v_score
                tipo = "Vespertino"
            elif n_score is not None:
                promedio_final = n_score
                tipo = "Nocturno"
            else:
                continue
            ranking_data.append({"Colaborador": emp, "Turno Efectivo": tipo, "Puntaje (%)": round(promedio_final, 1)})
            
        df_ranking = pd.DataFrame(ranking_data).sort_values("Puntaje (%)", ascending=False).reset_index(drop=True)
        
        c_r1, c_r2 = st.columns([1, 1])
        with c_r1:
            st.write("🏆 **Tabla de Posiciones General**")
            st.dataframe(df_ranking, use_container_width=True)
            
        with c_r2:
            st.write("🔍 **Buscador Individual**")
            sel = st.selectbox("Selecciona para ver métricas específicas:", personal_total)
            
            es_vespertino = not df_rop[df_rop[col_enf] == sel].empty
            es_nocturno = sel in pct_nocturnos
            
            # Solo muestra las tarjetas de métricas que le corresponden a esa persona
            if es_vespertino and es_nocturno:
                c_p1, c_p2 = st.columns(2)
                c_p1.metric("🌙 Desempeño Nocturno", f"{pct_nocturnos[sel]:.1f}%")
                c_p2.metric("☀️ Desempeño Vespertino", f"{df_rop[df_rop[col_enf] == sel]['Promedio'].mean():.1f}%")
            elif es_nocturno:
                st.metric("🌙 Desempeño Nocturno (Rondines)", f"{pct_nocturnos[sel]:.1f}%")
            elif es_vespertino:
                st.metric("☀️ Desempeño Vespertino (5S / Camas)", f"{df_rop[df_rop[col_enf] == sel]['Promedio'].mean():.1f}%")
            else:
                st.info("Sin registros operativos en este periodo.")

    with tabs[3]:
        st.write("### Checklist de Blindaje Institucional")
        st.write("Controles preventivos requeridos para auditorías gubernamentales (STPS, COPRISJAL, Protección Civil).")
        
        categorias = {
            "Riesgo Comercial y Sanitario": ["Contrato de Adhesión PROFECO", "Aviso de Funcionamiento Vigente", "NOM-087-SEMARNAT (RPBI)", "NOM-251-SSA1 (Higiene Cocina)"],
            "Protección Civil y Bomberos": ["Programa Interno (PIPC)", "Póliza de Responsabilidad Civil", "Dictamen Estructural", "Mantenimiento Extintores"],
            "Riesgo Laboral (STPS)": ["NOM-035 (Psicosocial)", "NOM-019 (Comisión Mixta)", "Constancias de Habilidades DC-3"]
        }
        
        if 'checks_normas' not in st.session_state:
            st.session_state.checks_normas = {item: False for cat in categorias.values() for item in cat}

        # Visualización clara y expuesta de checkboxes
        c_leg1, c_leg2 = st.columns(2)
        idx = 0
        for cat, items in categorias.items():
            col = c_leg1 if idx % 2 == 0 else c_leg2
            with col.container():
                st.markdown(f"<p style='font-weight:700; color:{HEX_NAVY}; margin-top:10px;'>{cat}</p>", unsafe_allow_html=True)
                for item in items:
                    st.session_state.checks_normas[item] = st.checkbox(item, value=st.session_state.checks_normas[item], key=item)
            idx += 1
            
        porcentaje_legal = (sum(st.session_state.checks_normas.values()) / len(st.session_state.checks_normas)) * 100
        st.write("---")
        st.write(f"#### Integridad Institucional actual: {int(porcentaje_legal)}%")
        st.progress(porcentaje_legal / 100)
        
        # Botón para descargar el PDF de Legal
        pdf_bytes = generar_pdf_legal_bytes(st.session_state.checks_normas, porcentaje_legal)
        st.download_button(
            label="📄 Descargar Reporte Legal en PDF",
            data=pdf_bytes,
            file_name=f"Reporte_Blindaje_Legal_{datetime.now().strftime('%Y_%m_%d')}.pdf",
            mime="application/pdf",
        )

    with tabs[4]:
        st.write("### Consola de Verificación")
        st.dataframe(df_serv.head(10), use_container_width=True)

    st.markdown("<div class='footer-watermark'>Sunhaven Intelligence Suite - Enterprise Edition</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()