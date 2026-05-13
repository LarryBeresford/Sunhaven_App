import streamlit as st
import pandas as pd
import gspread
import json
import os
import io
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from fpdf import FPDF
from openpyxl import load_workbook
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import shutil
import uuid
import re

# ==========================================
# 0. CONFIGURACION Y SEGURIDAD
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH_CREDS = os.path.join(BASE_DIR, 'config', 'sunhaven-credentials.json')

st.set_page_config(page_title="Sunhaven | Nómina y Kaizen", layout="wide", initial_sidebar_state="expanded")

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
        background-color: #ffffff; padding: 20px; border-radius: 4px;
        border: 1px solid #e2e8f0; text-align: center;
    }
    .metric-label { font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 28px; font-weight: 800; color: #0f172a; margin: 0; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #f1f5f9; border-radius: 4px; padding: 10px 20px; font-weight: 600; color: #475569; }
    .stTabs [aria-selected="true"] { background-color: #1e293b !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

HEX_NAVY = "#1e293b"
HEX_RED = "#dc2626"
HEX_GREEN = "#16a34a"
HEX_SUN = "#d35400"

C_NAVY = (31, 58, 82)
C_SUN = (211, 84, 0)
C_DARK = (44, 62, 80)
C_LIGHT = (245, 247, 248)

# --- REGLAS DE NEGOCIO ---
EXCEPCIONES_KAIZEN = ["Yareli Yamile Luquin Puga", "Blanca Aracely Figueroa Marroquín", "Guadalupe Georgia Lopez Ceja"]
TURNO_NOCHE = ["Jaqueline Hernández Sosa", "Silvia Rodríguez Reynaga", "Consuelo Ceja Liborio", "Guadalupe Georgia Lopez Ceja"]
HORA_ENTRADA_DIA = datetime.strptime("08:15", "%H:%M").time()
HORA_ENTRADA_NOCHE = datetime.strptime("20:15", "%H:%M").time()

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
    pdf.set_font('Helvetica', 'B', 8)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 7, sanitizar_texto(h), 1, 0, 'C', True)
    pdf.ln()
    
    pdf.set_font('Helvetica', '', 8)
    fill = False
    for row in data:
        pdf.set_x(start_x)
        pdf.set_fill_color(*C_LIGHT) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(*C_DARK)
        for i, val in enumerate(row):
            align = 'C' if i > 0 else 'L'
            pdf.cell(col_widths[i], 6, sanitizar_texto(str(val)), 1, 0, align, fill)
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
        self.cell(0, 8, sanitizar_texto('REPORTE EJECUTIVO - NÓMINA Y KAIZEN'), 0, 1, 'C')
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

    def cover_page(self, titulo, subtitulo, fecha_str):
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
        self.cell(0, 10, sanitizar_texto('REPORTE EJECUTIVO UNIFICADO'), 0, 1, 'C')
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(*C_SUN)
        self.cell(0, 12, sanitizar_texto(titulo), 0, 1, 'C')
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

# --- GENERADOR DE IMÁGENES TEMPORALES ---
def generar_graficos(df_incidencias, df_retardos, stats_kaizen):
    temp_dir = os.path.join(os.path.dirname(__file__), f'temp_img_{uuid.uuid4().hex}')
    os.makedirs(temp_dir, exist_ok=True)
    paths = {}
    
    # 1. Pareto Incidencias
    plt.figure(figsize=(7, 4))
    inc_counts = df_incidencias['INCIDENCIA'].value_counts()
    plt.bar(inc_counts.index, inc_counts.values, color=HEX_NAVY)
    plt.title('Pareto de Incidencias Operativas', fontsize=10, fontweight='bold')
    plt.xticks(rotation=15, ha='right', fontsize=8)
    plt.tight_layout()
    paths['pareto'] = os.path.join(temp_dir, 'pareto.png')
    plt.savefig(paths['pareto'])
    plt.close()

    # 2. Ranking Retardos
    plt.figure(figsize=(7, 4))
    ret_counts = df_retardos['EMPLEADO'].value_counts().head(10)
    plt.barh(ret_counts.index, ret_counts.values, color=HEX_RED)
    plt.title('Ranking de Retardos Acumulados (Top 10)', fontsize=10, fontweight='bold')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    paths['retardos'] = os.path.join(temp_dir, 'retardos.png')
    plt.savefig(paths['retardos'])
    plt.close()

    # 3. Kaizen Pie Chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4))
    colors = [HEX_GREEN, HEX_RED]
    
    # Mes Anterior
    ax1.pie([stats_kaizen['prev_si'], stats_kaizen['prev_no']], labels=['Sí', 'No'], autopct='%1.1f%%', colors=colors, startangle=90)
    ax1.set_title('Participación Mes Anterior', fontsize=10)
    # Mes Actual
    ax2.pie([stats_kaizen['curr_si'], stats_kaizen['curr_no']], labels=['Sí', 'No'], autopct='%1.1f%%', colors=colors, startangle=90)
    ax2.set_title('Participación Mes Actual', fontsize=10)
    
    plt.tight_layout()
    paths['kaizen_pie'] = os.path.join(temp_dir, 'kaizen_pie.png')
    plt.savefig(paths['kaizen_pie'])
    plt.close()

    return paths, temp_dir

# --- ENSAMBLAJE DEL PDF MAESTRO ---
def generar_pdf_nomina_kaizen(df_nomina, df_incidencias, df_retardos, stats_kaizen, propuestas, mes_str):
    rutas_img, temp_dir = generar_graficos(df_incidencias, df_retardos, stats_kaizen)
    
    pdf = SunhavenPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.cover_page("CONTROL DE BONOS Y MEJORA CONTINUA", "Auditoría de Desempeño y Participación", mes_str)
    
    # SECCIÓN 1: INCIDENCIAS Y RETARDOS
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("1. ANÁLISIS DE INCIDENCIAS Y RETARDOS"), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.image(rutas_img['pareto'], x=10, w=90)
    pdf.image(rutas_img['retardos'], x=110, w=90)
    pdf.ln(80)
    
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(*C_SUN)
    pdf.multi_cell(0, 6, sanitizar_texto("Conclusión Estratégica: Las incidencias mostradas en el Pareto dictaminan directamente las deducciones aplicadas a los bonos de puntualidad y administración del personal."))
    
    # SECCIÓN 2: NÓMINA FINAL
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("2. DESGLOSE DE BONOS (TOTAL A PAGAR)"), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    datos_nomina = []
    for _, row in df_nomina.iterrows():
        datos_nomina.append([
            row['COLABORADOR'], 
            f"${row['$ PUNTUAL']}", f"${row['$ UNIFORM']}", f"${row['$ ADMIN']}", 
            f"${row['TOTAL A PAGAR']}"
        ])
    
    tabla_centrada(pdf, ["COLABORADOR", "PUNTUAL", "UNIFORME", "ADMIN", "TOTAL"], datos_nomina, [70, 25, 25, 25, 25])
    
    # SECCIÓN 3: KAIZEN ESTADÍSTICAS
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("3. ESTADÍSTICAS DE PARTICIPACIÓN KAIZEN"), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.image(rutas_img['kaizen_pie'], x=20, w=170)
    pdf.ln(85)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*C_DARK)
    pdf.cell(0, 6, sanitizar_texto("Personal que NO participó en este periodo (Se aplica deducción Administrativa):"), 0, 1)
    pdf.set_font('Helvetica', '', 10)
    for emp in stats_kaizen['lista_no']:
        pdf.cell(0, 5, sanitizar_texto(f"  - {emp}"), 0, 1)
        
    # SECCIÓN 4: KAIZEN PROPUESTAS
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("4. PROPUESTAS DE MEJORA CONTINUA (KAIZEN)"), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    for prop in propuestas:
        pdf.set_fill_color(240, 245, 250)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*C_NAVY)
        pdf.cell(130, 8, sanitizar_texto(f" Colaborador(a): {prop['nombre']}"), 'L T', 0, 'L', True)
        pdf.set_font('Helvetica', 'I', 9)
        pdf.cell(60, 8, sanitizar_texto(f"Fecha: {prop['fecha']} "), 'T R', 1, 'R', True)
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*C_DARK)
        pdf.multi_cell(0, 6, sanitizar_texto(f"Propuesta:\n{prop['propuesta']}\n"), 'L R B', 'J', False)
        pdf.ln(3)

    shutil.rmtree(temp_dir, ignore_errors=True)
    return pdf.output(dest='S').encode('latin-1', 'replace')

# ==========================================
# 2. PROCESAMIENTO DE DATOS (ETL)
# ==========================================
@st.cache_data(ttl=600)
def fetch_kaizen_data():
    try:
        if "GOOGLE_JSON" in st.secrets:
            gc = gspread.service_account_from_dict(json.loads(st.secrets["GOOGLE_JSON"]))
        else:
            gc = gspread.service_account(filename=PATH_CREDS)
        sheet = gc.open("SUNHAVEN_KAIZEN (Respuestas)").get_worksheet(0)
        df = pd.DataFrame(sheet.get_all_records())
        return df
    except Exception as e:
        st.error("Error conectando a Google Sheets para Kaizen. Verifique credenciales.")
        return pd.DataFrame()

def limpiar_biometrico(file_bytes):
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active
    datos = []
    empleado_actual = None
    departamento_actual = None
    
    for row in ws.iter_rows(values_only=True):
        row_str = [str(cell) if cell is not None else "" for cell in row]
        if "ID:" in row_str[0]:
            try:
                idx_nombre = row_str.index("Nombre:") + 2
                idx_depto = row_str.index("Departamento:") + 3
                empleado_actual = row_str[idx_nombre].strip()
                departamento_actual = row_str[idx_depto].strip()
            except ValueError:
                pass
        elif empleado_actual and any(":" in str(cell) for cell in row_str):
            for dia, celda in enumerate(row_str, 1):
                celda = str(celda).strip()
                if len(celda) >= 5 and ":" in celda:
                    entrada = celda[:5]
                    datos.append({"Checador": empleado_actual, "Día": dia, "Entrada": entrada})
            empleado_actual = None
            
    return pd.DataFrame(datos)

def procesar_super_nomina(df_bio, df_bitacora, df_padron, df_kaizen, mes_num, anio_num):
    # 1. Padrón Enfermería
    df_enf = df_padron[df_padron['Departamento'].str.contains('Enferm', case=False, na=False)].copy()
    dict_nombres = dict(zip(df_enf['Nombre checador'].str.upper(), df_enf['Nombre completo']))
    
    # 2. Retardos Biométrico
    retardos_list = []
    for _, row in df_bio.iterrows():
        checador = str(row['Checador']).upper()
        if checador in dict_nombres:
            nombre_real = dict_nombres[checador]
            entrada_str = row['Entrada']
            try:
                h_entrada = datetime.strptime(entrada_str, "%H:%M").time()
                es_noche = nombre_real in TURNO_NOCHE
                limite = HORA_ENTRADA_NOCHE if es_noche else HORA_ENTRADA_DIA
                if h_entrada > limite:
                    retardos_list.append({"FECHA": f"{anio_num}-{mes_num:02d}-{row['Día']:02d}", "EMPLEADO": nombre_real, "INCIDENCIA": "Retardo Biométrico", "OBS": f"Entró a las {entrada_str}"})
            except: pass
    df_retardos = pd.DataFrame(retardos_list)
    
    # 3. Kaizen (Castigo Admin)
    df_kaizen['Marca temporal'] = pd.to_datetime(df_kaizen['Marca temporal'], dayfirst=True, errors='coerce')
    df_k_curr = df_kaizen[(df_kaizen['Marca temporal'].dt.month == mes_num) & (df_kaizen['Marca temporal'].dt.year == anio_num)]
    participantes_curr = df_k_curr.iloc[:, 1].str.strip().unique().tolist()
    
    no_participaron = []
    for emp in df_enf['Nombre completo'].tolist():
        if emp not in participantes_curr and emp not in EXCEPCIONES_KAIZEN:
            no_participaron.append(emp)
            
    # Extraer stats Kaizen
    mes_prev = mes_num - 1 if mes_num > 1 else 12
    anio_prev = anio_num if mes_num > 1 else anio_num - 1
    df_k_prev = df_kaizen[(df_kaizen['Marca temporal'].dt.month == mes_prev) & (df_kaizen['Marca temporal'].dt.year == anio_prev)]
    part_prev = df_k_prev.iloc[:, 1].str.strip().unique().tolist()
    
    stats_k = {
        'curr_si': len([e for e in df_enf['Nombre completo'] if e in participantes_curr]),
        'curr_no': len(no_participaron),
        'prev_si': len([e for e in df_enf['Nombre completo'] if e in part_prev]),
        'prev_no': len([e for e in df_enf['Nombre completo'] if e not in part_prev and e not in EXCEPCIONES_KAIZEN]),
        'lista_no': no_participaron
    }
    
    propuestas = []
    for _, row in df_k_curr.iterrows():
        propuestas.append({'nombre': row.iloc[1], 'fecha': row['Marca temporal'].strftime("%d/%m/%Y"), 'propuesta': str(row.iloc[2])})
        
    # 4. Fusión de Incidencias
    incidencias_admin = pd.DataFrame([{"FECHA": f"{anio_num}-{mes_num:02d}-28", "EMPLEADO": e, "INCIDENCIA": "Falla Admin/Kaizen", "OBS": "No presentó propuesta en el mes"} for e in no_participaron])
    
    df_bitacora['FECHA'] = pd.to_datetime(df_bitacora['FECHA'], errors='coerce')
    df_bitacora_curr = df_bitacora[(df_bitacora['FECHA'].dt.month == mes_num) & (df_bitacora['FECHA'].dt.year == anio_num)].copy()
    df_bitacora_curr['FECHA'] = df_bitacora_curr['FECHA'].dt.strftime('%Y-%m-%d')
    df_bitacora_curr = df_bitacora_curr.rename(columns={'OBSERVACIÓN': 'OBS'})
    
    df_todas_inc = pd.concat([df_retardos, df_bitacora_curr, incidencias_admin], ignore_index=True)
    
    # 5. Cálculo de Nómina
    nomina = []
    for emp in df_enf['Nombre completo'].tolist():
        df_emp = df_todas_inc[df_todas_inc['EMPLEADO'] == emp]
        
        c_retardos = len(df_emp[df_emp['INCIDENCIA'].str.contains('Retardo', case=False, na=False)])
        c_admin = len(df_emp[df_emp['INCIDENCIA'].str.contains('Admin', case=False, na=False)])
        c_uniforme = len(df_emp[df_emp['INCIDENCIA'].str.contains('Uniforme', case=False, na=False)])
        
        # Reglas estándar Sunhaven (Ajustables)
        bono_p = 500 if c_retardos <= 3 else 0
        bono_a = 500 if c_admin == 0 else 0
        bono_u = 500 if c_uniforme == 0 else 0
        
        nomina.append({
            "COLABORADOR": emp,
            "RETARDOS": c_retardos,
            "INCIDENCIAS EXTRA": len(df_emp) - c_retardos,
            "$ PUNTUAL": bono_p,
            "$ UNIFORM": bono_u,
            "$ ADMIN": bono_a,
            "TOTAL A PAGAR": bono_p + bono_u + bono_a
        })
        
    df_nomina = pd.DataFrame(nomina)
    return df_nomina, df_todas_inc, df_retardos, stats_k, propuestas

# ==========================================
# 3. INTERFAZ WEB STREAMLIT
# ==========================================
def main():
    with st.sidebar:
        st.markdown("### PANEL DE NÓMINA")
        st.divider()
        
        mes_eval = st.selectbox("Mes a evaluar:", range(1, 13), index=datetime.now().month-1)
        anio_eval = st.number_input("Año:", min_value=2020, max_value=2050, value=datetime.now().year)
        
        st.markdown("#### Archivos Requeridos")
        file_asis = st.file_uploader("1. Subir 'Asistencia.xlsx' (Biométrico)", type=['xlsx'])
        file_bonos = st.file_uploader("2. Subir 'Master_Bonos.xlsx'", type=['xlsx'])
        
        procesar = st.button("Procesar Nómina Integral", use_container_width=True, type="primary")
        
    if procesar and file_asis and file_bonos:
        with st.spinner("Conectando con Google Sheets y cruzando datos..."):
            try:
                df_kaizen = fetch_kaizen_data()
                df_bio = limpiar_biometrico(file_asis.read())
                
                xls_bonos = pd.ExcelFile(io.BytesIO(file_bonos.read()))
                df_padron = pd.read_excel(xls_bonos, sheet_name="Listado de personal")
                df_bitacora = pd.read_excel(xls_bonos, sheet_name="BITACORA")
                
                df_nomina, df_inc, df_ret, stats_k, props = procesar_super_nomina(df_bio, df_bitacora, df_padron, df_kaizen, mes_eval, anio_eval)
                
                st.session_state['nomina_data'] = (df_nomina, df_inc, df_ret, stats_k, props)
                st.success("Cruce de datos completado con éxito.")
            except Exception as e:
                st.error(f"Error procesando archivos: {e}")

    if 'nomina_data' in st.session_state:
        df_nomina, df_inc, df_ret, stats_k, props = st.session_state['nomina_data']
        mes_str = f"{mes_eval:02d}/{anio_eval}"
        
        st.markdown(f"""<div class='exec-header'>
            <div><p style='margin:0; font-weight:700; color:#64748b; font-size:12px; text-transform:uppercase;'>Estado de Nómina</p>
            <h2 style='margin:0; color:{HEX_NAVY};'>PERIODO: {mes_str}</h2></div>
            <div style='text-align:right;'><p style='margin:0; font-weight:700; color:#64748b; font-size:12px; text-transform:uppercase;'>Presupuesto a Dispersar</p>
            <h1 style='margin:0; font-size:48px; color:{HEX_GREEN};'>${df_nomina['TOTAL A PAGAR'].sum():,}</h1></div>
        </div>""", unsafe_allow_html=True)

        tabs = st.tabs(["Dashboard de Nómina", "Gestión Kaizen", "Auditoría de Datos"])

        with tabs[0]:
            st.write("### Dictamen de Bonos y Deducciones")
            c_btn1, c_btn2 = st.columns([0.3, 0.7])
            with c_btn1:
                pdf_bytes = generar_pdf_nomina_kaizen(df_nomina, df_inc, df_ret, stats_k, props, mes_str)
                st.download_button("Descargar PDF Unificado", data=pdf_bytes, file_name=f"Nomina_Kaizen_{mes_str.replace('/','_')}.pdf", mime="application/pdf", use_container_width=True)
                
            st.divider()
            c1, c2 = st.columns([0.6, 0.4])
            with c1:
                st.write("**Desglose de Nómina Final**")
                st.dataframe(df_nomina, use_container_width=True, hide_index=True)
            with c2:
                st.write("**Top Retardos**")
                if not df_ret.empty:
                    ret_counts = df_ret['EMPLEADO'].value_counts().reset_index()
                    ret_counts.columns = ['EMPLEADO', 'CANTIDAD']
                    st.dataframe(ret_counts, use_container_width=True, hide_index=True)
                else:
                    st.success("No hay retardos registrados en el periodo.")

        with tabs[1]:
            st.write("### Participación en Mejora Continua (Google Forms)")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Métricas del Periodo Actual**")
                st.metric("Participaron", stats_k['curr_si'])
                st.metric("No Participaron (Penalizados)", stats_k['curr_no'])
            with col2:
                fig = px.pie(values=[stats_k['curr_si'], stats_k['curr_no']], names=['Sí Participó', 'No Participó'], color_discrete_sequence=[HEX_GREEN, HEX_RED])
                st.plotly_chart(fig, use_container_width=True)
            
            st.write("**Propuestas Enviadas:**")
            for p in props:
                st.info(f"**{p['nombre']} ({p['fecha']}):** {p['propuesta']}")

        with tabs[2]:
            st.write("### Auditoría de Tuberías de Datos (Data Cruda)")
            sub1, sub2, sub3 = st.tabs(["⌚ Reloj Biométrico Limpio", "📋 Bitácora + Falla Admin", "💡 Kaizen Raw Data"])
            with sub1:
                st.write("Datos extraídos y formateados del Excel de Asistencia:")
                st.dataframe(df_ret, use_container_width=True)
            with sub2:
                st.write("Incidencias combinadas (Manuales del Excel + Castigos Kaizen Automáticos):")
                st.dataframe(df_inc, use_container_width=True)
            with sub3:
                st.write("Respuestas directas de Google Sheets:")
                st.dataframe(fetch_kaizen_data(), use_container_width=True)

    else:
        st.info("Por favor, sube los archivos 'Asistencia.xlsx' y 'Master_Bonos.xlsx' en el panel lateral y presiona procesar.")

st.markdown("<div class='footer-watermark'>Sunhaven Intelligence Suite - Enterprise Edition</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()