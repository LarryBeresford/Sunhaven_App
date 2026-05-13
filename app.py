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

# --- LIBRERÍAS PARA GENERAR IMÁGENES EN EL PDF ---
import matplotlib
matplotlib.use('Agg') # Fundamental para que no crashee en la nube
import matplotlib.pyplot as plt
import shutil
import uuid

# ==========================================
# 0. CONFIGURACION Y SEGURIDAD
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH_CREDS = os.path.join(BASE_DIR, 'config', 'sunhaven-credentials.json')

st.set_page_config(page_title="Sunhaven | Operaciones", layout="wide", initial_sidebar_state="expanded")

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

C_NAVY = (31, 58, 82)
C_SUN = (211, 84, 0)
C_DARK = (44, 62, 80)
C_LIGHT = (245, 247, 248)

# --- REGLAS DE NEGOCIO Y TURNOS ---
ENFERMERAS_ROL_A = ["Consuelo Ceja Liborio", "Jaqueline Hernández Sosa"]
ENFERMERAS_ROL_B = ["Silvia Rodríguez Reynaga", "Guadalupe Georgia Lopez Ceja"]
ENFERMERAS_NOCHE = ENFERMERAS_ROL_A + ENFERMERAS_ROL_B

# ==========================================
# 1. MOTOR PDF (CLASE MAESTRA SUNHAVEN)
# ==========================================
def sanitizar_texto(texto):
    txt = str(texto).replace('•', '-').replace('“', '"').replace('”', '"').replace('–', '-')
    return txt.encode('latin-1', 'replace').decode('latin-1')

def tabla_centrada(pdf, headers, data, col_widths):
    total_width = sum(col_widths)
    start_x = (210 - total_width) / 2
    
    pdf.set_x(start_x)
    pdf.set_fill_color(*C_NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 9)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, sanitizar_texto(h), 1, 0, 'C', True)
    pdf.ln()
    
    pdf.set_font('Helvetica', '', 9)
    fill = False
    for row in data:
        pdf.set_x(start_x)
        pdf.set_fill_color(*C_LIGHT) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(*C_DARK)
        for i, val in enumerate(row):
            align = 'C' if i > 0 else 'L'
            pdf.cell(col_widths[i], 7, sanitizar_texto(str(val)), 1, 0, align, fill)
        pdf.ln()
        fill = not fill

class SunhavenPDF(FPDF):
    def header(self):
        if self.page_no() == 1: return
        self.set_fill_color(*C_NAVY)
        self.rect(0, 0, 210, 26, 'F')
        self.set_fill_color(*C_SUN)
        self.rect(0, 26, 210, 1.5, 'F')
        self.set_y(9)
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, sanitizar_texto(getattr(self, 'titulo_header', 'REPORTE EJECUTIVO')), 0, 1, 'C')
        self.ln(12)

    def footer(self):
        if self.page_no() == 1: return
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*C_NAVY)
        self.set_draw_color(*C_SUN)
        self.line(10, 282, 200, 282)
        self.set_x(10)
        self.cell(190, 10, sanitizar_texto(f'Página {self.page_no()}'), 0, 0, 'C')
        self.set_x(10)
        self.cell(190, 10, sanitizar_texto('Ing. Larry Beresford'), 0, 0, 'R')

    def cover_page(self, titulo_principal, subtitulo, fecha_str):
        self.add_page()
        self.set_fill_color(*C_NAVY)
        self.rect(0, 0, 210, 100, 'F')
        self.set_fill_color(*C_SUN)
        self.rect(0, 100, 210, 3, 'F')
        self.set_y(40)
        self.set_font('Helvetica', 'B', 28)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, sanitizar_texto('SUNHAVEN'), 0, 1, 'C')
        self.set_font('Helvetica', '', 12)
        self.set_text_color(220, 220, 220)
        self.cell(0, 8, sanitizar_texto('CASA DE DESCANSO PARA ADULTOS MAYORES'), 0, 1, 'C')
        self.set_y(140)
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(*C_DARK)
        self.cell(0, 10, sanitizar_texto('REPORTE EJECUTIVO'), 0, 1, 'C')
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(*C_SUN)
        self.cell(0, 12, sanitizar_texto(titulo_principal), 0, 1, 'C')
        self.set_font('Helvetica', '', 14)
        self.set_text_color(*C_DARK)
        self.cell(0, 8, sanitizar_texto(subtitulo), 0, 1, 'C')
        self.set_y(220)
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(*C_NAVY)
        self.cell(0, 8, sanitizar_texto(f'PERIODO EVALUADO: {fecha_str}'), 0, 1, 'C')
        self.set_y(260)
        self.set_font('Helvetica', '', 11)
        self.set_text_color(*C_DARK)
        self.cell(0, 6, sanitizar_texto('Elaborado por:'), 0, 1, 'C')
        self.set_font('Helvetica', 'B', 11)
        self.cell(0, 6, sanitizar_texto('Ing. Larry Beresford'), 0, 1, 'C')

# --- GENERADOR DE PDF: DASHBOARD OPERATIVO (CON GRÁFICOS Y CONCLUSIONES) ---
def generar_graficos_temporales(df_a, df_c, df_evol, df_ranking):
    temp_dir = os.path.join(os.path.dirname(__file__), f'temp_images_{uuid.uuid4().hex}')
    os.makedirs(temp_dir, exist_ok=True)
    paths = {}
    
    plt.figure(figsize=(8, 4))
    plt.bar(df_a['index'], df_a['V'], color=HEX_NAVY)
    plt.axhline(90, color='red', linestyle='--')
    plt.title('Pareto de Cumplimiento por Área Operativa', fontsize=12, fontweight='bold')
    plt.tight_layout()
    paths['pareto'] = os.path.join(temp_dir, 'pareto.png')
    plt.savefig(paths['pareto'])
    plt.close()
    
    plt.figure(figsize=(8, 5))
    df_c_sorted = df_c.sort_values('V', ascending=True)
    plt.barh(df_c_sorted['index'], df_c_sorted['V'], color=HEX_RED)
    plt.axvline(90, color='black', linestyle='--')
    plt.title('Análisis de Causa Raíz (Criterios Específicos)', fontsize=12, fontweight='bold')
    plt.tight_layout()
    paths['causa'] = os.path.join(temp_dir, 'causa.png')
    plt.savefig(paths['causa'])
    plt.close()
    
    plt.figure(figsize=(10, 4))
    for col in df_evol.columns:
        plt.plot(df_evol.index, df_evol[col], marker='o', label=col)
    plt.axhline(90, color='red', linestyle='--')
    plt.title('Evolución Histórica de Departamentos', fontsize=12, fontweight='bold')
    plt.legend(loc='lower center', bbox_to_anchor=(0.5, -0.3), ncol=5)
    plt.tight_layout()
    paths['evol'] = os.path.join(temp_dir, 'evol.png')
    plt.savefig(paths['evol'])
    plt.close()
    
    return paths, temp_dir

def generar_pdf_dashboard(ico, estatus, areas_kpi, df_c, df_ranking, fechas_str, df_evol):
    rutas_img, temp_dir = generar_graficos_temporales(pd.DataFrame(list(areas_kpi.items()), columns=['index', 'V']), df_c, df_evol, df_ranking)
    
    pdf = SunhavenPDF()
    pdf.titulo_header = "REPORTE EJECUTIVO - OPERACIONES"
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.cover_page("INDICADORES OPERATIVOS (KPI)", "Estado de las Infraestructuras y Servicios", fechas_str)
    
    # SECCIÓN 1: GLOBAL
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("1. ESTATUS GLOBAL INSTITUCIONAL"), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*C_DARK)
    pdf.cell(0, 8, sanitizar_texto(f"Índice de Cumplimiento Operativo (ICO Maestro): {ico:.1f}%"), 0, 1)
    pdf.cell(0, 8, sanitizar_texto(f"Dictamen del Sistema: {estatus}"), 0, 1)
    pdf.ln(10)
    
    # SECCIÓN 2: ÁREAS
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("2. DESEMPEÑO POR DEPARTAMENTO (PARETO)"), 0, 1, 'L')
    pdf.ln(3)
    
    datos_areas = [[k, f"{v:.1f}%"] for k, v in sorted(areas_kpi.items(), key=lambda x: x[1], reverse=True)]
    tabla_centrada(pdf, ["Área Operativa", "Cumplimiento"], datos_areas, [80, 40])
    
    pdf.ln(5)
    pdf.image(rutas_img['pareto'], x=30, w=150)
    
    peor_area = datos_areas[-1][0]
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(*C_SUN)
    pdf.multi_cell(0, 6, sanitizar_texto(f"Conclusión Estratégica: El área con mayor área de oportunidad en este periodo es '{peor_area}'. Se recomienda enfocar los recursos de supervisión inmediatos en este departamento para estabilizar el ICO Maestro."))
    pdf.ln(10)
    
    # SECCIÓN 3: CAUSA RAÍZ
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("3. ANÁLISIS DE CAUSA RAÍZ (TODOS LOS CRITERIOS)"), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    
    datos_cr = [[row['index'], f"{row['V']:.1f}%"] for _, row in df_c.sort_values('V', ascending=True).iterrows()]
    tabla_centrada(pdf, ["Criterio Evaluado", "Desempeño"], datos_cr, [100, 40])
    
    pdf.ln(5)
    pdf.image(rutas_img['causa'], x=30, w=150)
    
    peor_criterio = datos_cr[0][0]
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(*C_SUN)
    pdf.multi_cell(0, 6, sanitizar_texto(f"Dictamen de Causa Raíz: El factor crítico que está arrastrando la métrica global hacia abajo es '{peor_criterio}'. La acción correctiva debe aplicarse directamente sobre este proceso."))
    
    # SECCIÓN 4: LÍNEA DEL TIEMPO
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("4. EVOLUCIÓN HISTÓRICA (LÍNEA DE TIEMPO)"), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.image(rutas_img['evol'], x=15, w=180)
    pdf.ln(5)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(*C_SUN)
    pdf.multi_cell(0, 6, sanitizar_texto("Análisis de Tendencia: La gráfica superior demuestra la fluctuación diaria/semanal de la operación. Las caídas por debajo de la línea roja (90%) representan días de alto riesgo operativo."))

    # SECCIÓN 5: RENDIMIENTO INDIVIDUAL
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("5. RANKING DE DESEMPEÑO INDIVIDUAL"), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    datos_ranking = [[row['Colaborador'], row['Turno'], f"{row['Puntaje (%)']:.1f}%"] for _, row in df_ranking.iterrows()]
    tabla_centrada(pdf, ["Colaborador", "Tipo de Evaluación", "Puntaje"], datos_ranking, [80, 60, 30])
    
    pdf.ln(10)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(*C_SUN)
    pdf.multi_cell(0, 6, sanitizar_texto("Conclusión de Recursos Humanos: Este ranking unificado permite identificar al personal sobresaliente (apto para programas de bonos) y al personal que requiere capacitación inmediata para elevar sus estándares de ejecución."))

    # Limpieza de imágenes temporales
    shutil.rmtree(temp_dir, ignore_errors=True)
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- GENERADOR DE PDF: LEGAL ---
def generar_pdf_legal_bytes(categorias_dict, checks_dict, porcentaje):
    pdf = SunhavenPDF()
    pdf.titulo_header = "REPORTE EJECUTIVO - BLINDAJE NORMATIVO"
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.cover_page("CUMPLIMIENTO LEGAL Y NORMATIVO", "Auditoría de Prevención Gubernamental", datetime.now().strftime("%d/%m/%Y"))
    
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("ESTATUS GLOBAL DE BLINDAJE INSTITUCIONAL"), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*C_DARK)
    pdf.cell(0, 8, sanitizar_texto(f"Nivel de cumplimiento general de la institución: {porcentaje:.1f}%"), 0, 1)
    pdf.ln(5)
    
    pdf.set_fill_color(*C_NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(150, 8, sanitizar_texto("REQUISITO NORMATIVO"), 1, 0, 'C', True)
    pdf.cell(40, 8, sanitizar_texto("ESTATUS"), 1, 1, 'C', True)
    
    for cat, items in categorias_dict.items():
        pdf.set_fill_color(220, 230, 240) 
        pdf.set_text_color(*C_NAVY)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(190, 7, sanitizar_texto(f" {cat.upper()}"), 1, 1, 'L', True)
        
        fill_row = False
        for req in items:
            estado = checks_dict.get(req, False)
            pdf.set_fill_color(*C_LIGHT) if fill_row else pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(*C_DARK)
            
            req_texto = f"   - {req}"
            if len(req_texto) > 90: req_texto = req_texto[:87] + "..."
            
            pdf.set_font('Helvetica', '', 8)
            pdf.cell(150, 7, sanitizar_texto(req_texto), 1, 0, 'L', fill_row)
            
            if estado:
                pdf.set_text_color(39, 174, 96)
                txt_estado = "CUMPLE"
            else:
                pdf.set_text_color(231, 76, 60)
                txt_estado = "PENDIENTE"
                
            pdf.set_font('Helvetica', 'B', 8)
            pdf.cell(40, 7, sanitizar_texto(txt_estado), 1, 1, 'C', fill_row)
            fill_row = not fill_row

    return pdf.output(dest='S').encode('latin-1', 'replace')

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
        st.markdown("### PANEL DE CONTROL")
        st.divider()
        if st.button("Sincronizar Base de Datos", use_container_width=True):
            cargar_datos_maestros.clear()
            st.rerun()
            
        st.markdown("#### Periodo de Análisis")
        hoy = datetime.now()
        treinta_dias_atras = hoy - timedelta(days=30)
        fechas = st.date_input("Seleccione el rango operativo:", [treinta_dias_atras, hoy])
        
        if len(fechas) == 2:
            fecha_inicio, fecha_fin = fechas
            fechas_str = f"{fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}"
        else:
            st.stop()
            
    data = cargar_datos_maestros()
    df_ron, df_rop, df_serv = data["n"].copy(), data["v"].copy(), data["s"].copy()

    try:
        def traducir(serie):
            mapeo = {'sí': 10, 'si': 10, 'no': 0, 'cumple': 10, 'no cumple': 0, 'separada': 10, 'bien': 10, 'ok': 10, 'limpio': 10, 'sucio': 0}
            return pd.to_numeric(serie.astype(str).str.strip().str.lower().replace(mapeo), errors='coerce') * 10

        c_5s = [c for c in df_rop.columns if "Orden" in c][0]
        c_cam = [c for c in df_rop.columns if "Tendido" in c][0]
        
        col_enf_candidates = [c for c in df_rop.columns if "asignado" in c.lower() or "evaluad" in c.lower()]
        if col_enf_candidates:
            col_enf = col_enf_candidates[0]
        else:
            col_enf = [c for c in df_rop.columns if "enfermera" in c.lower() or "nombre" in c.lower()][0]

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
        for enf in ENFERMERAS_NOCHE:
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

        crit = {"Uniforme": df_serv[c_uni].mean(), "Basura": df_serv[c_bas].mean(), "Ropa": df_serv[c_lav_r].mean(), "Jabón": df_serv[c_lav_j].mean(), "Zonas": df_serv[c_lim].mean(), "5S Roperos": df_rop[c_5s].mean(), "Tendido Camas": df_rop[c_cam].mean(), "Rondines Noct.": val_nocturno}
        df_c = pd.DataFrame.from_dict(crit, orient='index', columns=['V']).sort_values('V', ascending=True).reset_index()

        personal_diurno = set(df_rop[col_enf].dropna().unique()) - set(ENFERMERAS_NOCHE)
        personal_total = sorted(list(personal_diurno.union(set(ENFERMERAS_NOCHE))))
        ranking_data = []
        for emp in personal_total:
            if emp in ENFERMERAS_NOCHE:
                n_score = pct_nocturnos.get(emp, None)
                if n_score is not None:
                    ranking_data.append({"Colaborador": emp, "Turno": "Nocturno", "Puntaje (%)": round(n_score, 1)})
            else:
                v_score = df_rop[df_rop[col_enf] == emp]['Promedio'].mean()
                if pd.notna(v_score):
                    ranking_data.append({"Colaborador": emp, "Turno": "Vespertino", "Puntaje (%)": round(v_score, 1)})
        df_ranking = pd.DataFrame(ranking_data).sort_values("Puntaje (%)", ascending=False).reset_index(drop=True)
        
        # PREPARAR DATA EVOLUCION
        rango_fechas = pd.date_range(fecha_inicio, fecha_fin)
        df_ron_valido = df_ron[df_ron['Bloque'].notnull()].drop_duplicates(subset=['Fecha', 'Enfermera', 'Bloque'])
        conteo_diario_noc = df_ron_valido.groupby('Fecha').size()
        noc_diario = []
        for d in rango_fechas:
            d_date = d.date()
            if d.weekday() in [0, 2, 4]: exp = len(ENFERMERAS_ROL_A) * 3
            elif d.weekday() in [1, 3, 5]: exp = len(ENFERMERAS_ROL_B) * 3
            else: exp = 0
            if exp > 0: noc_diario.append(min((conteo_diario_noc.get(d_date, 0) / exp) * 100, 100))
            else: noc_diario.append(None)
            
        df_time_v = df_rop.groupby('Fecha')['Promedio'].mean()
        df_time_coc = df_serv.groupby('Fecha')[[c_uni, c_bas]].mean().mean(axis=1)
        df_time_lav = df_serv.groupby('Fecha')[[c_lav_r, c_lav_j]].mean().mean(axis=1)
        df_time_lim = df_serv.groupby('Fecha')[c_lim].mean()

        df_evol_base = pd.DataFrame(index=rango_fechas.date)
        df_evol_base['Nocturno'] = noc_diario
        df_evol_base['Vespertino'] = df_evol_base.index.map(df_time_v)
        df_evol_base['Cocina'] = df_evol_base.index.map(df_time_coc)
        df_evol_base['Lavandería'] = df_evol_base.index.map(df_time_lav)
        df_evol_base['Limpieza'] = df_evol_base.index.map(df_time_lim)

        df_evol_base = df_evol_base.ffill().bfill().fillna(0)
        df_evol_base.index = pd.to_datetime(df_evol_base.index)

    except Exception as e:
        st.error(f"Error: {e}")
        ico_master = 0
        estatus_txt = "ERROR DE DATOS"
        df_c = pd.DataFrame()
        df_ranking = pd.DataFrame()
        df_evol_base = pd.DataFrame()

    estatus_txt = "ESTABLE" if ico_master >= 90 else "ATENCION REQUERIDA"

    # --- HEADER ---
    st.markdown(f"""<div class='exec-header'>
        <div><p style='margin:0; font-weight:700; color:#64748b; font-size:12px; letter-spacing:1px; text-transform:uppercase;'>Estatus Institucional</p>
        <h2 style='margin:0; color:{HEX_GREEN if ico_master >= 90 else HEX_RED};'>{estatus_txt}</h2></div>
        <div style='text-align:right;'><p style='margin:0; font-weight:700; color:#64748b; font-size:12px; letter-spacing:1px; text-transform:uppercase;'>ICO Maestro</p>
        <h1 style='margin:0; font-size:48px;'>{ico_master:.1f}%</h1></div>
    </div>""", unsafe_allow_html=True)

    tabs = st.tabs(["Tablero de Control", "Evolución Temporal", "Rendimiento Individual", "Blindaje Legal", "Auditoría de Datos"])

    with tabs[0]:
        st.write("### Generador de Reporte Ejecutivo")
        c_btn1, c_btn2 = st.columns([0.2, 0.8])
        with c_btn1:
            if st.button("Generar Reporte PDF", use_container_width=True):
                with st.spinner("Procesando gráficos analíticos y ensamblando PDF..."):
                    pdf_bytes = generar_pdf_dashboard(ico_master, estatus_txt, areas_kpi, df_c, df_ranking, fechas_str, df_evol_base)
                    st.session_state['pdf_dash'] = pdf_bytes
                    
        with c_btn2:
            if 'pdf_dash' in st.session_state:
                st.download_button(label="Descargar Reporte Operativo", data=st.session_state['pdf_dash'], file_name=f"Dashboard_Sunhaven_{fecha_fin.strftime('%d%m%Y')}.pdf", mime="application/pdf", use_container_width=False)

        st.divider()

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
            fig_c = px.bar(df_c, x='V', y='index', orientation='h', text_auto='.1f', color_discrete_sequence=[HEX_RED])
            fig_c.add_vline(x=90, line_dash="dash", line_color="black")
            st.plotly_chart(fig_c, use_container_width=True)

    with tabs[1]:
        st.write("### Evolución Histórica de Todos los Departamentos")
        agrupacion = st.radio("Seleccionar Agrupación Temporal:", ["Día", "Semana", "Mes", "Año"], horizontal=True)
        
        if agrupacion == "Semana":
            df_plot = df_evol_base.resample('W-MON').mean()
            df_plot.index = df_plot.index.strftime('Semana %W - %Y')
        elif agrupacion == "Mes":
            df_plot = df_evol_base.resample('ME').mean()
            df_plot.index = df_plot.index.strftime('%Y-%m')
        elif agrupacion == "Año":
            df_plot = df_evol_base.resample('YE').mean()
            df_plot.index = df_plot.index.strftime('%Y')
        else:
            df_plot = df_evol_base.copy()
            df_plot.index = df_plot.index.strftime('%Y-%m-%d')

        fig_evol = px.line(df_plot, labels={"value": "Cumplimiento (%)", "index": "Periodo", "variable": "Área Operativa"}, markers=True)
        fig_evol.add_hline(y=90, line_dash="dot", line_color="red", annotation_text="Línea Base 90%")
        st.plotly_chart(fig_evol, use_container_width=True)

    with tabs[2]:
        st.write("### Rendimiento Detallado por Personal")
        c_r1, c_r2 = st.columns([1.2, 0.8])
        with c_r1:
            st.write("**Tabla de Posiciones General**")
            st.dataframe(df_ranking, use_container_width=True)
            
        with c_r2:
            st.write("**Buscador de Expediente Operativo**")
            sel = st.selectbox("Selecciona colaborador(a):", personal_total)
            if sel in ENFERMERAS_NOCHE:
                st.metric("Desempeño Nocturno (Conductual)", f"{pct_nocturnos.get(sel, 0):.1f}%")
                st.info("**Aviso Metodológico:**\nEste KPI evalúa estrictamente el cumplimiento del protocolo de rondines de seguridad.")
            else:
                df_sel = df_rop[df_rop[col_enf] == sel]
                if not df_sel.empty:
                    st.metric("Desempeño Vespertino (Físico)", f"{df_sel['Promedio'].mean():.1f}%")
                    st.info("**Aviso Metodológico:**\nEste KPI evalúa las condiciones físicas de la zona asignada.")
                    st.dataframe(df_sel[['Fecha', c_5s, c_cam, 'Promedio']], use_container_width=True)
                else:
                    st.warning("Sin registros operativos.")

    with tabs[3]:
        st.write("### Auditoría y Blindaje Institucional")
        st.write("Desglose normativo aplicable para cumplimiento ante autoridades.")
        
        categorias = {
            "COPRISJAL (Regulación Sanitaria)": [
                "Aviso de Funcionamiento y Responsable Sanitario exhibido",
                "Aviso de Botiquín/Farmacia y Recetario Controlado autorizado",
                "NOM-031-SSA3 (Asistencia Social, Manuales y Bitácoras)",
                "NOM-004-SSA3 (Expedientes Clínicos y Resguardo seguro)",
                "NOM-087-SEMARNAT (Botes rígidos, bolsas rojas y contrato RPBI)",
                "NOM-045 y NOM-251 (Protocolos de Infecciones e Higiene en Cocina)",
                "Certificado vigente de fumigación y control de plagas"
            ],
            "STPS (Seguridad y Salud Laboral)": [
                "Reglamento Interior de Trabajo (RIT) depositado ante autoridad",
                "NOM-035-STPS (Política de prevención de Riesgos Psicosociales)",
                "NOM-019-STPS (Comisión de Seguridad e Higiene conformada)",
                "NOM-036-STPS (Prevención de Riesgos Ergonómicos / Carga)",
                "NOM-030-STPS (Diagnóstico Integral de seguridad en el trabajo)",
                "Constancias de Habilidades Laborales emitidas (DC-3)"
            ],
            "Protección Civil y Ecología (Ayuntamiento)": [
                "Programa Interno de Protección Civil (PIPC) con visto bueno",
                "Póliza de Responsabilidad Civil (Daños a terceros) vigente",
                "Dictámenes Técnicos vigentes (Estructural DRO, Eléctrico y Gas LP)",
                "Equipamiento instalado (Extintores ABC/K, Detectores, Señalética)",
                "Brigadas capacitadas y evidencia de mínimo 2 simulacros anuales",
                "Mantenimiento de trampas de grasa y recolección de aceite vegetal",
                "Licencia Municipal de Giro Comercial vigente y a la vista"
            ],
            "Legal, Privacidad y PROFECO": [
                "Aviso de Privacidad Integral exhibido (INAI)",
                "Consentimiento expreso firmado para tratamiento de Datos Sensibles",
                "Contratos de prestación de servicios registrados ante PROFECO",
                "Constancia de registro vigente ante Asistencia Social (IJAS/DIF)",
                "Contratos laborales actualizados con cláusulas de confidencialidad"
            ]
        }
        
        if 'checks_normas' not in st.session_state:
            st.session_state.checks_normas = {}
            
        for cat, items in categorias.items():
            for item in items:
                if item not in st.session_state.checks_normas:
                    st.session_state.checks_normas[item] = False

        c_leg1, c_leg2 = st.columns([0.7, 0.3])
        with c_leg1:
            for cat, items in categorias.items():
                with st.expander(cat, expanded=True):
                    for item in items:
                        st.session_state.checks_normas[item] = st.checkbox(item, value=st.session_state.checks_normas[item], key=item)
            
        total_items_actuales = sum(len(items) for items in categorias.values())
        items_cumplidos = sum(1 for cat in categorias.values() for item in cat if st.session_state.checks_normas.get(item, False))
        porcentaje_legal = (items_cumplidos / total_items_actuales) * 100 if total_items_actuales > 0 else 0
        
        with c_leg2:
            st.write(f"#### Índice de Integridad: {int(porcentaje_legal)}%")
            st.progress(porcentaje_legal / 100)
            st.divider()
            if st.button("Preparar Reporte Legal", use_container_width=True):
                with st.spinner("Compilando auditoría normativa..."):
                    st.session_state['pdf_legal'] = generar_pdf_legal_bytes(categorias, st.session_state.checks_normas, porcentaje_legal)
            
            if 'pdf_legal' in st.session_state:
                st.download_button(label="Descargar Auditoría PDF", data=st.session_state['pdf_legal'], file_name=f"Reporte_Legal_{datetime.now().strftime('%d%m%Y')}.pdf", mime="application/pdf", use_container_width=True)

    with tabs[4]:
        st.write("### Auditoría de Tuberías de Datos (Data Cruda)")
        st.info("Verifica los registros extraídos de Google Sheets tras aplicar los filtros de fecha. Usa las pestañas internas para navegar.")
        
        sub_t1, sub_t2, sub_t3 = st.tabs(["Servicios Generales", "Enfermería Vespertina", "Rondines Nocturnos"])
        with sub_t1: st.dataframe(df_serv, use_container_width=True)
        with sub_t2: st.dataframe(df_rop, use_container_width=True)
        with sub_t3: st.dataframe(df_ron, use_container_width=True)

st.markdown("<div class='footer-watermark'>Sunhaven Intelligence Suite - Enterprise Edition</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()