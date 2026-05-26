import streamlit as st
import pandas as pd
import gspread
import json
import os
import io
from datetime import datetime, timedelta
import plotly.express as px
from fpdf import FPDF
from openpyxl import load_workbook
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import shutil
import uuid

# ==========================================
# 0. CONFIGURACION Y SEGURIDAD GLOBAL
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATH_CREDS = os.path.join(BASE_DIR, 'config', 'sunhaven-credentials.json')
PATH_BITACORA = os.path.join(BASE_DIR, 'data', 'bitacora_interna.csv')

st.set_page_config(page_title="Sunhaven Intelligence Suite", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .block-container { padding-top: 1.5rem; max-width: 95%; }
    h1, h2, h3 { color: #1e293b; font-weight: 800; letter-spacing: -0.5px; }
    .exec-header { background-color: #ffffff; padding: 2rem; border-radius: 4px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; }
    .kpi-card { background-color: #ffffff; padding: 25px; border-radius: 4px; border: 1px solid #e2e8f0; text-align: center; }
    .metric-label { font-size: 12px; color: #64748b; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 34px; font-weight: 800; margin: 0; }
    .footer-watermark { text-align: center; margin-top: 80px; opacity: 0.3; font-size: 11px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; }
    .dictamen-box { background-color: #f8fafc; border-left: 6px solid #d35400; padding: 15px; border-radius: 4px; margin-bottom: 2rem; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0;}
    .dictamen-title { margin-top: 0; color: #1e293b; font-size: 13px; text-transform: uppercase; font-weight: 800; margin-bottom: 8px;}
    .dictamen-text { margin: 0; color: #334155; font-size: 14px; line-height: 1.5;}
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #f1f5f9; border-radius: 4px; padding: 10px 20px; font-weight: 600; color: #475569; }
    .stTabs [aria-selected="true"] { background-color: #1e293b !important; color: white !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* ---------------------------------------------------
       MEJORAS DE UX: OCULTAR BASURA Y ANIMAR BOTONES
       --------------------------------------------------- */
       
    /* 1. Ocultar el menú de navegación residual de Streamlit (los nombres fantasma) */
    [data-testid="stSidebarNav"] {display: none !important;}
    
    /* 2. Crear la animación de vibración (Shake/Vibrate) */
    @keyframes vibrar {
        0% { transform: translateX(0); }
        20% { transform: translateX(-2px) rotate(-1deg); }
        40% { transform: translateX(2px) rotate(1deg); }
        60% { transform: translateX(-2px) rotate(-1deg); }
        80% { transform: translateX(2px) rotate(1deg); }
        100% { transform: translateX(0); }
    }
    
    /* 3. Aplicar la animación a los botones cuando se pasa el mouse (hover) */
    .stButton > button, .stDownloadButton > button {
        transition: all 0.2s ease-in-out !important; /* Transición suave */
    }
    
    .stButton > button:hover, .stDownloadButton > button:hover {
        animation: vibrar 0.35s linear !important; /* Llama a la animación */
    }
</style>
""", unsafe_allow_html=True)

HEX_NAVY, HEX_RED, HEX_GREEN, HEX_SUN = "#1e293b", "#dc2626", "#16a34a", "#d35400"
C_NAVY, C_SUN, C_DARK, C_LIGHT = (31, 58, 82), (211, 84, 0), (44, 62, 80), (245, 247, 248)

# --- REGLAS DE NEGOCIO ---
ENFERMERAS_ROL_A = ["Consuelo Ceja Liborio", "Jaqueline Hernández Sosa"]
ENFERMERAS_ROL_B = ["Silvia Rodríguez Reynaga", "Guadalupe Georgia Lopez Ceja"]
ENFERMERAS_NOCHE = ENFERMERAS_ROL_A + ENFERMERAS_ROL_B

EMPLEADOS_DB = {
    "ALE": "Alejandra Itzel de la Fuente Ramírez", "ARIANA": "Ariana Villanueva Temores",
    "Araceli Figueroa": "Blanca Aracely Figueroa Marroquín", "BLANCARUVC": "Blanca Estela Ruvalcaba Ruiz",
    "CARMEN": "Carmen Torres Reyes", "ConsueloCeja": "Consuelo Ceja Liborio", "CRISTY": "Cristina Ramos Aquino", 
    "HUGO": "Hugo Silva Esparza", "JACK": "Jaqueline Hernández Sosa", "CESAR": "Julio César Pérez Carranza",
    "MARIASEO": "Maribel Herrera Mauricio", "MarthaCastro": "Martha Manuela Castro García",
    "MAYT": "Mayte López Romero", "MONI": "Mónica Teresa Grande Figueroa", "NANCI": "Nancy Estephania González Velasco", 
    "NIRE": "Nireida Flores Núñez", "Olga Gabriela Jimenez": "Olga Gabriela Jiménez Medina", 
    "RosaCastro": "Rosa Isela Antonieta Castro García", "SANDY": "Sandy Yusbeth Cruz González", 
    "Silvia Rodriguez": "Silvia Rodríguez Reynaga", "VERO": "Verónica Janeth Gómez López", 
    "YamileLuquin": "Yareli Yamile Luquin Puga", "Guadalupe": "Guadalupe Georgia Lopez Ceja"
}

ENFERMERAS_LISTA = [
    "Ariana Villanueva Temores", "Blanca Aracely Figueroa Marroquín", "Blanca Estela Ruvalcaba Ruiz",
    "Consuelo Ceja Liborio", "Cristina Ramos Aquino", "Jaqueline Hernández Sosa", "Mayte López Romero",
    "Nancy Estephania González Velasco", "Nireida Flores Núñez", "Olga Gabriela Jiménez Medina",
    "Rosa Isela Antonieta Castro García", "Sandy Yusbeth Cruz González", "Silvia Rodríguez Reynaga",
    "Verónica Janeth Gómez López", "Yareli Yamile Luquin Puga", "Guadalupe Georgia Lopez Ceja"
]

EXCEPCIONES_KAIZEN = ["Yareli Yamile Luquin Puga", "Blanca Aracely Figueroa Marroquín", "Guadalupe Georgia Lopez Ceja"]
CHECADORES_ESPECIALES = ["CESAR", "MONI", "MARTHACASTRO", "HUGO"] 
HORA_ENTRADA_DIA, HORA_ENTRADA_NOCHE = datetime.strptime("08:15", "%H:%M").time(), datetime.strptime("20:15", "%H:%M").time()
TIPO_INCIDENCIAS = ["Falta de uniforme (Leve)", "Uso de celular (Leve)", "No hacer entrega (Leve)", "No hacer ronda (Leve)", "Salida anticipada (Leve)", "AGRESIÓN / CONFLICTO (Grave)", "REGLA DE ORO (Grave)"]

# ==========================================
# 1. CLASE MAESTRA DE PDF Y HELPERS
# ==========================================
def sanitizar_texto(texto):
    return str(texto).replace('•', '-').replace('“', '"').replace('”', '"').replace('–', '-').encode('latin-1', 'replace').decode('latin-1')

def tabla_centrada(pdf, headers, data, col_widths):
    start_x = (210 - sum(col_widths)) / 2
    pdf.set_x(start_x)
    pdf.set_fill_color(*C_NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 8)
    for i, h in enumerate(headers): pdf.cell(col_widths[i], 7, sanitizar_texto(h), 1, 0, 'C', True)
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
        self.cell(0, 10, sanitizar_texto('SUN HAVEN'), 0, 1, 'C')
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

# ==========================================
# 2. MOTORES DE DIAGNÓSTICO (CONCLUSIONES)
# ==========================================
def generar_dictamen_operativo(ico, df_a, df_c):
    if df_a.empty or df_c.empty:
        return "No hay datos suficientes para generar un dictamen.", "No hay datos suficientes."

    areas_bajas = df_a[df_a['V'] < 90].sort_values('V', ascending=True)
    causas_bajas = df_c[df_c['V'] < 90].sort_values('V', ascending=True)

    if ico >= 90:
        html = "[ ESTADO ESTABLE ] Todas las áreas superan la línea base del 90%. Se recomienda mantener los protocolos de supervisión actuales."
        pdf_text = "El ecosistema operativo se encuentra en estado ESTABLE. Todas las métricas superan la línea base del 90%. Se recomienda mantener los protocolos de supervisión actuales y extender un reconocimiento al equipo."
    elif ico >= 80:
        peor_area = areas_bajas.iloc[0]['index'] if not areas_bajas.empty else "N/A"
        peor_causa = causas_bajas.iloc[0]['index'] if not causas_bajas.empty else "N/A"
        html = f"<strong>[ ALERTA PREVENTIVA ]</strong> El rendimiento general está decayendo.<br><br>1. <strong>Foco Primario:</strong> El departamento de '{peor_area}' muestra debilidad operativa.<br>2. <strong>Causa Principal:</strong> El criterio de '{peor_causa}' necesita revisión.<br>3. <strong>Acción Sugerida:</strong> Agendar reunión de calibración con el personal del turno afectado."
        pdf_text = f"ALERTA PREVENTIVA: El rendimiento general requiere ajustes antes de volverse crítico.\n\n1. Foco Primario: El departamento de '{peor_area}' presenta las métricas más bajas.\n2. Causa Principal: El criterio de '{peor_causa}' necesita revisión operativa.\n3. Acción Sugerida: Se recomienda una sesión de retroalimentación (feedback) con el personal involucrado."
    else:
        peor_area = areas_bajas.iloc[0]['index'] if not areas_bajas.empty else "N/A"
        peor_causa = causas_bajas.iloc[0]['index'] if not causas_bajas.empty else "N/A"
        html = f"<strong>[ ATENCIÓN CRÍTICA ]</strong> Existen deficiencias serias en la operación.<br><br>1. <strong>ÁREA ROJA:</strong> El departamento de '{peor_area}' requiere intervención gerencial urgente.<br>2. <strong>FALLA SISTÉMICA:</strong> El incumplimiento en '{peor_causa}' está arrastrando la calificación.<br>3. <strong>ACCIÓN OBLIGATORIA:</strong> Ejecutar plan de corrección inmediato."
        pdf_text = f"ATENCIÓN CRÍTICA: Se detectan deficiencias operativas que requieren intervención gerencial inmediata.\n\n1. ÁREA ROJA: El departamento de '{peor_area}' muestra un rendimiento deficiente.\n2. FALLA SISTÉMICA: El incumplimiento en el criterio de '{peor_causa}' es la principal causa del rezago.\n3. ACCIÓN OBLIGATORIA: Implementar un plan de choque esta semana. Se sugiere mayor presencia de supervisión física."

    return html, pdf_text

def generar_dictamen_nomina(stats_kaizen, df_retardos):
    t_kz = stats_kaizen['curr_si'] + stats_kaizen['curr_no']
    pct_kz = (stats_kaizen['curr_si'] / t_kz * 100) if t_kz > 0 else 0
    
    html, pdf_text = "", ""
    
    if pct_kz < 80:
        html += f"<strong>[ MEJORA CONTINUA (KAIZEN) ]</strong> El {pct_kz:.1f}% del personal entregó sus propuestas. Nivel bajo de cumplimiento. Se recomienda aplicar deducción administrativa a los omisos.<br><br>"
        pdf_text += f"1. PARTICIPACIÓN KAIZEN: El {pct_kz:.1f}% del personal entregó sus propuestas. Nivel bajo de cumplimiento. Se recomienda aplicar la deducción administrativa de inmediato a los omisos para fomentar la disciplina.\n\n"
    else:
        html += f"<strong>[ MEJORA CONTINUA (KAIZEN) ]</strong> El {pct_kz:.1f}% del personal entregó sus propuestas. Nivel de participación excelente.<br><br>"
        pdf_text += f"1. PARTICIPACIÓN KAIZEN: El {pct_kz:.1f}% del personal entregó sus propuestas. Nivel de participación excelente. Se sugiere reconocer públicamente las mejores propuestas.\n\n"
        
    if not df_retardos.empty:
        peor_emp = df_retardos['EMPLEADO'].value_counts().index[0]
        max_ret = df_retardos['EMPLEADO'].value_counts().iloc[0]
        html += f"<strong>[ PUNTUALIDAD ]</strong> El colaborador con mayor reincidencia de retardos biométricos es '{peor_emp}' ({max_ret} retardos). Se recomienda citación para diálogo y acta administrativa."
        pdf_text += f"2. PUNTUALIDAD: El colaborador con mayor reincidencia de retardos biométricos es '{peor_emp}' con {max_ret} retardos. Se recomienda citación para diálogo y acta administrativa en caso de continuar la tendencia."
    else:
        html += "<strong>[ PUNTUALIDAD ]</strong> Excelente puntualidad general en este periodo. No hay reincidencias críticas."
        pdf_text += "2. PUNTUALIDAD: Excelente puntualidad general en este periodo. No hay reincidencias críticas."
        
    return html, pdf_text

def generar_dictamen_rondines(alertas_fraude, df_resumen):
    html, pdf_text = "", ""
    
    if alertas_fraude > 0:
        html += f"<strong>[ ALERTA ANTIFRAUDE ]</strong> Se han detectado {alertas_fraude} escaneos realizados en menos de 60 segundos entre sí. Cruzar horarios con cámaras de vigilancia.<br><br>"
        pdf_text += f"ALERTA DE AUDITORÍA: Se han detectado {alertas_fraude} escaneos realizados en menos de 60 segundos entre sí. Esto indica un fuerte indicio de llenado fraudulento de la bitácora desde un mismo dispositivo físico. Se exige cruzar estos horarios con las cámaras de vigilancia.\n\n"
    
    bajos = df_resumen[df_resumen['% Cumplimiento'] < 90]
    if not bajos.empty:
        nombres = ", ".join(bajos['Colaborador'].tolist())
        html += f"<strong>[ DESEMPEÑO INSUFICIENTE ]</strong> Las siguientes enfermeras no alcanzaron la meta mínima del 90% en sus rondines: {nombres}. Se recomienda sanción administrativa."
        pdf_text += f"DESEMPEÑO: Las siguientes enfermeras no alcanzaron la meta mínima del 90% en sus rondines: {nombres}. Se recomienda aplicar la sanción administrativa y dialogar para evitar negligencias nocturnas."
    else:
        html += "<strong>[ DESEMPEÑO ÓPTIMO ]</strong> El equipo nocturno cumplió satisfactoriamente con la meta de rondas de seguridad."
        pdf_text += "DESEMPEÑO: El equipo nocturno cumplió satisfactoriamente con la meta de rondas de seguridad establecidas."
        
    return html, pdf_text


# ==========================================
# 3. GENERADORES DE PDF POR MÓDULO
# ==========================================
def generar_pdf_dashboard_op(ico, estatus, df_a, df_c, df_evol, agrupacion, fecha_str, pdf_dictamen):
    temp_dir = os.path.join(os.path.dirname(__file__), f'temp_img_{uuid.uuid4().hex}')
    os.makedirs(temp_dir, exist_ok=True)
    
    plt.figure(figsize=(7, 4))
    plt.bar(df_a['index'], df_a['V'], color=HEX_NAVY)
    plt.axhline(90, color='red', linestyle='--')
    plt.title('Pareto por Área Operativa', fontsize=10, fontweight='bold')
    plt.tight_layout()
    p_pareto = os.path.join(temp_dir, 'pareto_op.png')
    plt.savefig(p_pareto)
    plt.close()

    plt.figure(figsize=(7, 4))
    df_c_sorted = df_c.sort_values('V', ascending=True)
    plt.barh(df_c_sorted['index'], df_c_sorted['V'], color=HEX_RED)
    plt.axvline(90, color='black', linestyle='--')
    plt.title('Análisis de Causa Raíz', fontsize=10, fontweight='bold')
    plt.tight_layout()
    p_causa = os.path.join(temp_dir, 'causa_op.png')
    plt.savefig(p_causa)
    plt.close()
    
    plt.figure(figsize=(9, 4))
    if not df_evol.empty:
        for col in df_evol.columns: plt.plot(df_evol.index, df_evol[col], marker='o', label=col)
        plt.axhline(90, color='red', linestyle='--')
        plt.title(f'Evolución Histórica Sincronizada ({agrupacion})', fontsize=10, fontweight='bold')
        plt.xticks(rotation=45, ha='right', fontsize=8)
        plt.legend(loc='lower center', bbox_to_anchor=(0.5, -0.4), ncol=5)
    plt.tight_layout()
    p_evol = os.path.join(temp_dir, 'evol_op.png')
    plt.savefig(p_evol)
    plt.close()

    pdf = SunhavenPDF()
    pdf.titulo_header = "REPORTE EJECUTIVO - OPERACIONES"
    pdf.cover_page("INDICADORES OPERATIVOS (KPI)", "Estado de las Infraestructuras y Servicios", fecha_str)
    
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
    
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("2. DESEMPEÑO POR DEPARTAMENTO"), 0, 1, 'L')
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.image(p_pareto, x=30, w=150)
    pdf.ln(75)
    
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("3. ANÁLISIS DE CAUSA RAÍZ"), 0, 1, 'L')
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.image(p_causa, x=30, w=150)
    pdf.ln(75)
    
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("4. EVOLUCIÓN HISTÓRICA (TENDENCIA)"), 0, 1, 'L')
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.image(p_evol, x=15, w=180)
    pdf.ln(100)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(240, 245, 250)
    pdf.cell(0, 8, sanitizar_texto(" CONCLUSIONES Y RECOMENDACIONES EJECUTIVAS"), 1, 1, 'L', True)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 6, sanitizar_texto(pdf_dictamen), 1, 'L')

    shutil.rmtree(temp_dir, ignore_errors=True)
    return pdf.output(dest='S').encode('latin-1', 'replace')

def generar_pdf_nomina(df_nomina, df_incidencias, df_retardos, stats_kaizen, propuestas,
                       df_bio, mes_num, anio_num, mes_str, pdf_dictamen):
    temp_dir = os.path.join(os.path.dirname(__file__), f'temp_img_{uuid.uuid4().hex}')
    os.makedirs(temp_dir, exist_ok=True)

    # ================================================================
    # FIGURA 1: Pareto + Ranking lado a lado (figura combinada)
    # ================================================================
    fig1, (ax_par, ax_ret) = plt.subplots(1, 2, figsize=(14, 5))

    inc_counts = df_incidencias['INCIDENCIA'].value_counts()
    if not inc_counts.empty:
        bar_colors_p = ['#dc2626' if ('Kaizen' in i or 'Admin' in i) else '#1e293b' for i in inc_counts.index]
        bars = ax_par.bar(range(len(inc_counts)), inc_counts.values, color=bar_colors_p)
        ax_par.set_xticks(range(len(inc_counts)))
        ax_par.set_xticklabels([t[:22] for t in inc_counts.index], rotation=25, ha='right', fontsize=8)
        for b, v in zip(bars, inc_counts.values):
            ax_par.text(b.get_x() + b.get_width()/2, b.get_height() + 0.05, str(v), ha='center', fontsize=8)
    ax_par.set_title('Pareto de Incidencias del Periodo', fontsize=11, fontweight='bold')
    ax_par.set_ylabel('Cantidad')

    ret_counts = df_retardos['EMPLEADO'].value_counts().head(12)
    if not ret_counts.empty:
        bar_cols_r = ['#dc2626' if c >= 4 else '#d97706' if c == 3 else '#1e293b' for c in ret_counts.values]
        names_short = [n.split()[0] + ' ' + n.split()[-1] if len(n.split()) > 1 else n for n in ret_counts.index]
        y_pos = range(len(ret_counts))
        ax_ret.barh(list(y_pos), list(ret_counts.values), color=bar_cols_r)
        ax_ret.set_yticks(list(y_pos))
        ax_ret.set_yticklabels(names_short, fontsize=8)
        ax_ret.axvline(x=4, color='red', linestyle='--', linewidth=1.2, label='Pierde bono (>=4)')
        ax_ret.axvline(x=3, color='orange', linestyle='--', linewidth=1.2, label='En riesgo (3)')
        ax_ret.legend(fontsize=8)
    ax_ret.set_title('Ranking de Retardos por Colaborador', fontsize=11, fontweight='bold')
    ax_ret.set_xlabel('Retardos')

    plt.tight_layout()
    p_chart1 = os.path.join(temp_dir, 'chart1_nom.png')
    plt.savefig(p_chart1, dpi=150, bbox_inches='tight')
    plt.close()

    # ================================================================
    # FIGURA 2: Donuts Kaizen (mes anterior vs. mes actual)
    # ================================================================
    fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
    colors_kz = [HEX_GREEN, HEX_RED]
    tot_p = stats_kaizen['prev_si'] + stats_kaizen['prev_no']
    tot_c = stats_kaizen['curr_si'] + stats_kaizen['curr_no']
    if tot_p > 0:
        ax1.pie([stats_kaizen['prev_si'], stats_kaizen['prev_no']],
                labels=['Participo', 'No participo'], autopct='%1.1f%%',
                colors=colors_kz, startangle=90, wedgeprops=dict(width=0.55))
    ax1.set_title('Mes Anterior', fontsize=12, fontweight='bold')
    if tot_c > 0:
        ax2.pie([stats_kaizen['curr_si'], stats_kaizen['curr_no']],
                labels=['Participo', 'No participo'], autopct='%1.1f%%',
                colors=colors_kz, startangle=90, wedgeprops=dict(width=0.55))
    ax2.set_title('Mes Actual', fontsize=12, fontweight='bold')
    fig2.suptitle('Participacion en Programa Kaizen — Mejora Continua',
                  fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    p_kz = os.path.join(temp_dir, 'kz_nom.png')
    plt.savefig(p_kz, dpi=150, bbox_inches='tight')
    plt.close()

    # ================================================================
    # CALCULAR HORAS SEMANALES (Checadores Especiales)
    # ================================================================
    horas_semana = {}
    if not df_bio.empty and 'Salida' in df_bio.columns:
        DB_UP = {" ".join(k.upper().split()): v for k, v in EMPLEADOS_DB.items()}
        for ch_up in {" ".join(c.upper().split()) for c in CHECADORES_ESPECIALES}:
            nombre = DB_UP.get(ch_up, ch_up)
            df_ch = df_bio[df_bio['Checador'].apply(lambda x: " ".join(str(x).upper().split())) == ch_up]
            if df_ch.empty:
                continue
            semanas = {}
            for _, r in df_ch.iterrows():
                try:
                    fecha_d = datetime(anio_num, mes_num, int(r['Día']))
                except Exception:
                    continue
                iso_w = fecha_d.isocalendar()[1]
                ent_s = str(r.get('Entrada', ''))
                sal_s = str(r.get('Salida', ''))
                if len(ent_s) == 5 and len(sal_s) == 5 and ':' in ent_s and ':' in sal_s:
                    try:
                        t_e = datetime.strptime(ent_s, "%H:%M")
                        t_s = datetime.strptime(sal_s, "%H:%M")
                        dh  = (t_s - t_e).total_seconds() / 3600
                        if dh < 0:
                            dh += 24
                        semanas[iso_w] = semanas.get(iso_w, 0) + dh
                    except Exception:
                        pass
            if semanas:
                horas_semana[nombre] = semanas

    # ================================================================
    # CONSTRUIR PDF
    # ================================================================
    pdf = SunhavenPDF()
    pdf.titulo_header = "REPORTE EJECUTIVO — NOMINA Y MEJORA CONTINUA"
    pdf.cover_page("NOMINA Y RECURSOS HUMANOS", "Bonos, Retardos y Programa Kaizen", mes_str)

    # ---- SECCION 1: Gráficas de análisis ----
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("1. ANALISIS DE INCIDENCIAS DEL PERIODO"), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 5, sanitizar_texto(
        "El grafico izquierdo (Pareto) muestra la frecuencia de cada tipo de incidencia en el periodo. "
        "Las barras ROJAS corresponden a fallas Kaizen — cada una representa $500 perdidos por el colaborador omiso. "
        "El grafico derecho es el ranking de retardos: barras en NARANJA = exactamente 3 retardos "
        "(un retardo mas y pierde el Bono de Puntualidad de $500); barras en ROJO = bono ya perdido (>=4 retardos)."
    ), 0, 'J')
    pdf.ln(3)
    pdf.image(p_chart1, x=10, w=190)
    pdf.ln(5)

    # ---- SECCION 2: Tabla total a pagar ----
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("2. TOTAL A PAGAR POR RUBRO"), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 5, sanitizar_texto(
        "Cada colaborador puede ganar hasta $1,500 en bonos: Puntualidad ($500, maximo 3 retardos tolerados), "
        "Uniforme ($500, sin incidencias de imagen) y Admin/Kaizen ($500, requiere entregar propuesta mensual de mejora). "
        "Un bono en $0 indica que la falta correspondiente fue comprobada con evidencia biometrica o bitacora."
    ), 0, 'J')
    pdf.ln(3)
    total_dispersar = df_nomina['TOTAL A PAGAR'].sum()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*C_SUN)
    pdf.cell(0, 7, sanitizar_texto(f"Total a Dispersar este Periodo: ${total_dispersar:,}"), 0, 1, 'R')
    pdf.ln(2)
    datos_nomina = [
        [row['COLABORADOR'], str(row['RETARDOS']),
         f"${row['$ PUNTUAL']}", f"${row['$ UNIFORM']}", f"${row['$ ADMIN']}", f"${row['TOTAL A PAGAR']}"]
        for _, row in df_nomina.iterrows()
    ]
    tabla_centrada(pdf, ["COLABORADOR", "RETARDOS", "PUNTUALIDAD", "UNIFORME", "ADMIN/KAIZEN", "TOTAL"],
                   datos_nomina, [68, 18, 25, 25, 30, 24])

    # ---- SECCION 3: Justificación de retenciones y advertencias ----
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("3. JUSTIFICACION DE RETENCIONES Y ADVERTENCIAS"), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 5, sanitizar_texto(
        "Esta seccion documenta, con fechas exactas, la razon por la cual cada colaborador perdio uno o mas bonos. "
        "Sirve como evidencia documental para sustentar los descuentos aplicados en nomina. "
        "Solo se muestran colaboradores con al menos una retencion o en situacion de riesgo."
    ), 0, 'J')
    pdf.ln(5)

    for _, emp_row in df_nomina.iterrows():
        emp   = emp_row['COLABORADOR']
        total = int(emp_row['TOTAL A PAGAR'])
        c_ret = int(emp_row['RETARDOS'])
        bp    = int(emp_row['$ PUNTUAL'])
        bu    = int(emp_row['$ UNIFORM'])
        ba    = int(emp_row['$ ADMIN'])

        perdio_algo = (total < 1500)
        en_riesgo   = (c_ret == 3 and bp == 500)
        if not perdio_algo and not en_riesgo:
            continue

        if pdf.get_y() > 245:
            pdf.add_page()

        # Cabecera con color según resultado
        if total == 1500:
            fill_c = (22, 163, 74)
        elif total == 0:
            fill_c = (220, 38, 38)
        else:
            fill_c = (211, 84, 0)

        pdf.set_fill_color(*fill_c)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 7, sanitizar_texto(
            f"  {emp}   |   Total Bono: ${total}  "
            f"(Puntualidad: ${bp} | Uniforme: ${bu} | Admin/Kaizen: ${ba})"
        ), 0, 1, 'L', True)

        pdf.set_text_color(*C_DARK)
        pdf.set_font('Helvetica', '', 9)

        # Fechas de retardos
        df_emp_ret = df_retardos[df_retardos['EMPLEADO'] == emp]
        if not df_emp_ret.empty:
            fechas_ret = ", ".join(df_emp_ret['FECHA'].tolist())
            pdf.multi_cell(0, 5, sanitizar_texto(f"   Retardos biometricos ({c_ret}): {fechas_ret}"), 0, 'L')
            if bp == 0:
                pdf.set_text_color(220, 38, 38)
                pdf.set_font('Helvetica', 'B', 9)
                pdf.cell(0, 5, sanitizar_texto(
                    "   >> Bono Puntualidad PERDIDO: -$500 (supero el limite de 3 retardos)"
                ), 0, 1)
                pdf.set_text_color(*C_DARK)
                pdf.set_font('Helvetica', '', 9)

        # Falla Kaizen
        df_emp_inc = df_incidencias[df_incidencias['EMPLEADO'] == emp]
        es_kaizen_falla = not df_emp_inc[df_emp_inc['INCIDENCIA'] == 'Falla Admin/Kaizen'].empty
        if es_kaizen_falla:
            pdf.set_text_color(220, 38, 38)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(0, 5, sanitizar_texto(
                "   >> No presento Kaizen del mes  ->  Bono Admin/Kaizen PERDIDO: -$500"
            ), 0, 1)
            pdf.set_text_color(*C_DARK)
            pdf.set_font('Helvetica', '', 9)

        # Otras incidencias de bitácora
        df_otras = df_emp_inc[~df_emp_inc['INCIDENCIA'].isin(['Retardo Biométrico', 'Falla Admin/Kaizen'])]
        for _, inc_row in df_otras.iterrows():
            pdf.multi_cell(0, 5, sanitizar_texto(
                f"   Incidencia {inc_row['FECHA']}: {inc_row['INCIDENCIA']} — {str(inc_row['OBSERVACION'])[:60]}"
            ), 0, 'L')

        # Alerta: exactamente 3 retardos (en riesgo)
        if en_riesgo:
            pdf.ln(1)
            pdf.set_fill_color(255, 243, 205)
            pdf.set_draw_color(202, 138, 4)
            pdf.set_text_color(133, 77, 14)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.multi_cell(190, 6, sanitizar_texto(
                "[!] ALERTA: Este colaborador tiene 3 retardos. "
                "Un retardo mas y PIERDE el Bono de Puntualidad ($500)."
            ), 1, 'L', True)
            pdf.set_text_color(*C_DARK)
            pdf.set_fill_color(255, 255, 255)
            pdf.set_draw_color(*C_SUN)
            pdf.set_font('Helvetica', '', 9)

        pdf.ln(4)

    # ---- SECCION 4: Horas semanales (checadores especiales) ----
    if horas_semana:
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(*C_NAVY)
        pdf.cell(0, 8, sanitizar_texto("4. CONTROL DE HORAS SEMANALES — PERSONAL ADMINISTRATIVO"), 0, 1, 'L')
        pdf.set_draw_color(*C_SUN)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*C_DARK)
        pdf.multi_cell(0, 5, sanitizar_texto(
            "Control de horas trabajadas por semana ISO para el personal administrativo de tiempo completo, "
            "calculadas a partir del primer y ultimo registro del checador biometrico por dia. "
            "La meta de referencia para tiempo completo es 40 horas semanales."
        ), 0, 'J')
        pdf.ln(5)
        sec_base = 5
        for nombre, semanas in sorted(horas_semana.items()):
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_text_color(*C_SUN)
            pdf.cell(0, 6, sanitizar_texto(f"  {nombre}"), 0, 1, 'L')
            filas_h = []
            total_h = 0.0
            for sw in sorted(semanas):
                hrs = semanas[sw]
                total_h += hrs
                filas_h.append([f"Semana {sw}", f"{hrs:.1f} hrs",
                                 "OK" if hrs >= 40 else "INCOMPLETA"])
            filas_h.append(["TOTAL MES", f"{total_h:.1f} hrs", ""])
            tabla_centrada(pdf, ["Semana ISO", "Horas Trabajadas", "Estatus"],
                           filas_h, [55, 55, 55])
            pdf.ln(5)
    else:
        sec_base = 4

    # ---- SECCION 5 (o 4): Kaizen ----
    pdf.add_page()
    pdf.titulo_header = "REPORTE EJECUTIVO — NOMINA Y MEJORA CONTINUA"
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto(f"{sec_base}. PROGRAMA KAIZEN — MEJORA CONTINUA"), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pct_c = (stats_kaizen['curr_si'] / tot_c * 100) if tot_c > 0 else 0
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 5, sanitizar_texto(
        f"El Programa Kaizen es una iniciativa mensual OBLIGATORIA de mejora continua. "
        f"Cada colaborador que NO entrega su propuesta pierde automaticamente el Bono Admin/Kaizen de $500. "
        f"Este mes el {pct_c:.1f}% del personal elegible participo ({stats_kaizen['curr_si']} de {tot_c}). "
        f"Los {stats_kaizen['curr_no']} omisos generaron una perdida de "
        f"${stats_kaizen['curr_no'] * 500:,} en bonos no devengados."
    ), 0, 'J')
    pdf.ln(4)
    pdf.image(p_kz, x=20, w=170)
    pdf.ln(5)

    if stats_kaizen['lista_no']:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*C_NAVY)
        pdf.cell(0, 6, sanitizar_texto("Colaboradores que NO participaron en Kaizen este mes:"), 0, 1)
        pdf.set_font('Helvetica', '', 10)
        for emp_no in stats_kaizen['lista_no']:
            pdf.set_text_color(220, 38, 38)
            pdf.cell(0, 5, sanitizar_texto(f"  - {emp_no}   >>  Bono Admin/Kaizen PERDIDO: -$500"), 0, 1)
        pdf.set_text_color(*C_DARK)

    pdf.ln(8)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(240, 245, 250)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto(" CONCLUSIONES Y RECOMENDACIONES EJECUTIVAS"), 1, 1, 'L', True)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 6, sanitizar_texto(pdf_dictamen), 1, 'L')

    # ---- SECCION 6 (o 5): Propuestas ----
    if propuestas:
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(*C_NAVY)
        pdf.cell(0, 8, sanitizar_texto(f"{sec_base + 1}. PROPUESTAS DE MEJORA RECIBIDAS"), 0, 1, 'L')
        pdf.set_draw_color(*C_SUN)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*C_DARK)
        pdf.multi_cell(0, 5, sanitizar_texto(
            "A continuacion se presentan todas las propuestas de mejora entregadas este mes. "
            "Se recomienda revisar cada idea y dar seguimiento a las mas viables en la proxima reunion de equipo. "
            "Las propuestas son la base del ciclo de mejora continua de la institucion."
        ), 0, 'J')
        pdf.ln(5)

        for prop in propuestas:
            if pdf.get_y() > 250:
                pdf.add_page()
            pdf.set_fill_color(240, 245, 250)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_text_color(*C_NAVY)
            pdf.cell(130, 8, sanitizar_texto(f"  Colaborador(a): {prop['nombre']}"), 'L T', 0, 'L', True)
            pdf.set_font('Helvetica', 'I', 9)
            pdf.cell(60, 8, sanitizar_texto(f"Fecha: {prop['fecha']} "), 'T R', 1, 'R', True)
            if prop.get('area'):
                pdf.set_font('Helvetica', 'I', 9)
                pdf.set_text_color(*C_SUN)
                pdf.cell(0, 6, sanitizar_texto(f"  Area: {prop['area']}"), 'L R', 1, 'L', False)
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(*C_DARK)
            pdf.multi_cell(0, 6, sanitizar_texto(f"Propuesta:\n{prop['propuesta']}\n"), 'L R B', 'J', False)
            pdf.ln(3)

    shutil.rmtree(temp_dir, ignore_errors=True)
    return pdf.output(dest='S').encode('latin-1', 'replace')

def generar_pdf_rondines(df_resumen, escaneos_totales, alertas_fraude, fecha_str, pdf_dictamen):
    temp_dir = os.path.join(os.path.dirname(__file__), f'temp_img_{uuid.uuid4().hex}')
    os.makedirs(temp_dir, exist_ok=True)
    
    plt.figure(figsize=(7, 4))
    plt.bar(df_resumen['Colaborador'], df_resumen['% Cumplimiento'], color=HEX_NAVY)
    plt.axhline(90, color='red', linestyle='--')
    plt.title('% Cumplimiento por Colaborador', fontsize=10, fontweight='bold')
    plt.tight_layout()
    p_bar = os.path.join(temp_dir, 'bar_ron.png')
    plt.savefig(p_bar)
    plt.close()

    pdf = SunhavenPDF()
    pdf.titulo_header = "REPORTE DE AUDITORÍA - RONDINES NOCTURNOS"
    pdf.cover_page("SUPERVISIÓN Y CUIDADO CONTINUO", "Auditoría Operativa y Antifraude", fecha_str)
    
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("1. CUMPLIMIENTO OPERATIVO MENSUAL"), 0, 1, 'L')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 6, sanitizar_texto("Esquema: 3 rondines obligatorios por noche. La siguiente tabla evalúa el cumplimiento según el rol asignado (Los días domingo están excluidos del cálculo de desempeño):"))
    pdf.ln(5)
    
    datos_tabla = [[r['Colaborador'], r['Turnos Meta'], r['Meta Rondas'], r['Rondas Real.'], f"{r['% Cumplimiento']:.1f}%"] for _, r in df_resumen.iterrows()]
    tabla_centrada(pdf, ["Colaborador", "Turnos Meta", "Meta Rondas", "Rondas Real.", "% Cumplimiento"], datos_tabla, [60, 30, 30, 30, 40])
    pdf.ln(10)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, sanitizar_texto("Resumen de Escaneos y Auditoría Antifraude:"), 0, 1)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, sanitizar_texto(f"Total de escaneos QR procesados en el periodo: {escaneos_totales}"), 0, 1)
    pdf.cell(0, 6, sanitizar_texto(f"Alertas de velocidad detectadas (posible fraude < 60s): {alertas_fraude}"), 0, 1)
    pdf.ln(5)
    
    pdf.image(p_bar, x=30, w=150)
    pdf.ln(80)

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(240, 245, 250)
    pdf.cell(0, 8, sanitizar_texto(" CONCLUSIONES Y RECOMENDACIONES EJECUTIVAS"), 1, 1, 'L', True)
    pdf.set_font('Helvetica', '', 10)
    pdf.multi_cell(0, 6, sanitizar_texto(pdf_dictamen), 1, 'L')

    shutil.rmtree(temp_dir, ignore_errors=True)
    return pdf.output(dest='S').encode('latin-1', 'replace')

def generar_pdf_legal_bytes(categorias_dict, checks_dict, porcentaje):
    pdf = SunhavenPDF()
    pdf.titulo_header = "REPORTE EJECUTIVO - BLINDAJE NORMATIVO"
    pdf.cover_page("CUMPLIMIENTO LEGAL Y NORMATIVO", "Auditoría de Prevención Gubernamental", datetime.now().strftime("%d/%m/%Y"))
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto("ESTATUS GLOBAL DE BLINDAJE INSTITUCIONAL"), 0, 1, 'L')
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*C_DARK)
    pdf.cell(0, 8, sanitizar_texto(f"Nivel de cumplimiento general de la institución: {porcentaje:.1f}%"), 0, 1)
    pdf.ln(5)
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
            pdf.set_font('Helvetica', '', 7.5)
            req_texto = sanitizar_texto(f"   - {req}"[:115] + ("..." if len(req) > 112 else ""))
            pdf.cell(150, 7, req_texto, 1, 0, 'L', fill_row)
            pdf.set_text_color(39, 174, 96) if estado else pdf.set_text_color(231, 76, 60)
            pdf.set_font('Helvetica', 'B', 8)
            pdf.cell(40, 7, sanitizar_texto("CUMPLE" if estado else "PENDIENTE"), 1, 1, 'C', fill_row)
            fill_row = not fill_row
    return pdf.output(dest='S').encode('latin-1', 'replace')

# ==========================================
# 4. ETL Y CÁLCULOS
# ==========================================
@st.cache_data(ttl=600)
def cargar_datos_operaciones():
    try:
        if "GOOGLE_JSON" in st.secrets:
            # Opción 1: Streamlit Cloud (Secretos)
            creds_dict = json.loads(st.secrets["GOOGLE_JSON"])
            gc = gspread.service_account_from_dict(creds_dict)
        elif os.path.exists(PATH_CREDS):
            # Opción 2: Local (Archivo JSON)
            gc = gspread.service_account(filename=PATH_CREDS)
        else:
            st.error("No se encontraron credenciales de Google (Ni en Secrets ni archivo local).")
            return None

        # Conectar a las 3 hojas de cálculo
        sheet_n = gc.open_by_url("https://docs.google.com/spreadsheets/d/10wWKmjsyj501OXaFWs7Rd_XF_2R-H0YzV66B2K6HvPE/edit")
        sheet_v = gc.open_by_url("https://docs.google.com/spreadsheets/d/1C1AVmNXG0ggRekB1HF4_IhX-NGiTkwzgvZn2Z31rCsc/edit")
        sheet_s = gc.open_by_url("https://docs.google.com/spreadsheets/d/1wdP3mbW_k4a90ubPG-ZQy8FvfAZiwKnhPjCj1BZHcBs/edit")

        dfs = {
            "n": pd.DataFrame(sheet_n.get_worksheet(0).get_all_records()),
            "v": pd.DataFrame(sheet_v.get_worksheet(0).get_all_records()),
            "s": pd.DataFrame(sheet_s.get_worksheet(0).get_all_records())
        }
        
        # Limpiar nombres de columnas
        for k in dfs:
            if not dfs[k].empty:
                dfs[k].columns = dfs[k].columns.str.strip().str.replace('\n', ' ')
        return dfs
        
    except Exception as e:
        # En caso de error (ej. cuota excedida, no hay internet), devolvemos None
        print(f"Error interno en cargar_datos_operaciones: {e}")
        return None

@st.cache_data(ttl=600)
def fetch_kaizen_data():
    try:
        if "GOOGLE_JSON" in st.secrets:
            creds_dict = json.loads(st.secrets["GOOGLE_JSON"])
            gc = gspread.service_account_from_dict(creds_dict)
        elif os.path.exists(PATH_CREDS):
            gc = gspread.service_account(filename=PATH_CREDS)
        else:
            return pd.DataFrame()

        sheet = gc.open("SUNHAVEN_KAIZEN (Respuestas)")
        return pd.DataFrame(sheet.get_worksheet(0).get_all_records())
    except Exception as e:
        print(f"Error interno en fetch_kaizen_data: {e}")
        return pd.DataFrame()

def cargar_bitacora():
    if os.path.exists(PATH_BITACORA):
        return pd.read_csv(PATH_BITACORA)
    else:
        df = pd.DataFrame(columns=["FECHA", "EMPLEADO", "INCIDENCIA", "OBSERVACION"])
        # Asegurar que el directorio data/ exista
        os.makedirs(os.path.dirname(PATH_BITACORA), exist_ok=True)
        df.to_csv(PATH_BITACORA, index=False)
        return df

def guardar_incidencia(fecha, empleado, incidencia, obs):
    df = cargar_bitacora()
    nuevo_registro = pd.DataFrame([{"FECHA": fecha, "EMPLEADO": empleado, "INCIDENCIA": incidencia, "OBSERVACION": obs}])
    df = pd.concat([df, nuevo_registro], ignore_index=True)
    df.to_csv(PATH_BITACORA, index=False)

def borrar_incidencia(index):
    df = cargar_bitacora()
    if 0 <= index < len(df):
        df = df.drop(index)
        df.to_csv(PATH_BITACORA, index=False)

def limpiar_biometrico(file_bytes):
    # Lector de Excel ROBUSTO para el checador
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active
    datos = []
    emp = None
    
    for row in ws.iter_rows(values_only=True):
        row_str = [str(cell) if cell is not None else "" for cell in row]
        
        # Buscar la fila que contiene el nombre del empleado
        if any("ID:" in str(c) for c in row_str):
            for i, c in enumerate(row_str):
                if "Nombre:" in str(c):
                    try:
                        emp = " ".join(row_str[i+2].split())  # normaliza espacios dobles
                    except IndexError:
                        pass
                    break
        
        # Si ya tenemos un empleado, buscar las celdas con formato de hora (ej. "08:15")
        elif emp and any(":" in str(cell) for cell in row_str):
            for dia, celda in enumerate(row_str, 1): # Empezamos a contar desde el día 1
                celda = str(celda).strip()
                if len(celda) >= 5 and ":" in celda:
                    # Entrada = primeros 5 chars; Salida = últimos 5 chars si hay >=10
                    datos.append({
                        "Checador": emp,
                        "Día": dia,
                        "Entrada": celda[:5],
                        "Salida": celda[-5:] if len(celda) >= 10 else ""
                    })
            # Reiniciamos el empleado después de procesar su fila de horarios
            emp = None
            
    return pd.DataFrame(datos)

def procesar_super_nomina(df_bio, df_bitacora, df_kaizen, mes_num, anio_num):
    # Lookup case-insensitive para evitar bugs de mayúsculas/minúsculas
    EMPLEADOS_DB_UPPER = {" ".join(k.upper().split()): v for k, v in EMPLEADOS_DB.items()}
    CHECADORES_ESP_SET = {" ".join(c.upper().split()) for c in CHECADORES_ESPECIALES}
    HORA_CORTE_NOCHE   = datetime.strptime("14:00", "%H:%M").time()

    ret_list = []

    # 1. Procesar Biométrico (Retardos)
    if not df_bio.empty:
        for _, row in df_bio.iterrows():
            ch = " ".join(str(row['Checador']).upper().split())
            if ch not in EMPLEADOS_DB_UPPER:
                continue
            nm  = EMPLEADOS_DB_UPPER[ch]

            # Ignorar checadores especiales (administrativos)
            if ch in CHECADORES_ESP_SET:
                continue

            ent = row['Entrada']
            try:
                he = datetime.strptime(ent, "%H:%M").time()

                # Filtro 14:00: ignorar marcaciones diurnas de enfermeras de turno nocturno
                if nm in ENFERMERAS_NOCHE and he < HORA_CORTE_NOCHE:
                    continue

                lim = HORA_ENTRADA_NOCHE if nm in ENFERMERAS_NOCHE else HORA_ENTRADA_DIA

                if he > lim:
                    dt_ent = datetime.combine(datetime.today(), he)
                    dt_lim = datetime.combine(datetime.today(), lim)
                    min_tarde = int((dt_ent - dt_lim).total_seconds() / 60)
                    ret_list.append({
                        "FECHA": f"{anio_num}-{mes_num:02d}-{int(row['Día']):02d}",
                        "EMPLEADO": nm,
                        "INCIDENCIA": "Retardo Biométrico",
                        "OBSERVACION": f"Entro a las {ent} ({min_tarde} min tarde)"
                    })
            except Exception:
                pass

    df_ret = pd.DataFrame(ret_list)

    # 2. Procesar Kaizen (usando nombres de columnas en lugar de posición)
    COL_NOMBRE    = 'Colaborador'
    COL_PROPUESTA = 'Propuesta de mejora'
    COL_AREA      = 'Area de la propuesta'

    part, nopart, props = [], [], []
    stats_k = {'curr_si': 0, 'curr_no': 0, 'prev_si': 0, 'prev_no': 0, 'lista_no': []}

    if not df_kaizen.empty:
        df_kaizen['Marca temporal'] = pd.to_datetime(df_kaizen['Marca temporal'], dayfirst=True, errors='coerce')

        # Detectar nombre real de la columna Área (puede tener acento o no)
        col_area_real = COL_AREA
        for c in df_kaizen.columns:
            if 'rea' in c.lower() and 'propuesta' in c.lower():
                col_area_real = c
                break

        # Mes actual
        df_k_curr = df_kaizen[
            (df_kaizen['Marca temporal'].dt.month == mes_num) &
            (df_kaizen['Marca temporal'].dt.year  == anio_num)
        ]
        part   = df_k_curr[COL_NOMBRE].str.strip().unique().tolist() if COL_NOMBRE in df_k_curr.columns else []
        nopart = [e for e in ENFERMERAS_LISTA if e not in part and e not in EXCEPCIONES_KAIZEN]

        # Mes anterior (tendencia)
        m_prev = mes_num - 1 if mes_num > 1 else 12
        a_prev = anio_num  if mes_num > 1 else anio_num - 1
        df_k_prev = df_kaizen[
            (df_kaizen['Marca temporal'].dt.month == m_prev) &
            (df_kaizen['Marca temporal'].dt.year  == a_prev)
        ]
        part_p = df_k_prev[COL_NOMBRE].str.strip().unique().tolist() if COL_NOMBRE in df_k_prev.columns else []

        stats_k = {
            'curr_si': len([e for e in ENFERMERAS_LISTA if e in part]),
            'curr_no': len(nopart),
            'prev_si': len([e for e in ENFERMERAS_LISTA if e in part_p]),
            'prev_no': len([e for e in ENFERMERAS_LISTA if e not in part_p and e not in EXCEPCIONES_KAIZEN]),
            'lista_no': nopart
        }

        props = [{
            'nombre':    str(r.get(COL_NOMBRE, '')),
            'fecha':     r['Marca temporal'].strftime("%d/%m/%Y"),
            'area':      str(r.get(col_area_real, '')),
            'propuesta': str(r.get(COL_PROPUESTA, ''))
        } for _, r in df_k_curr.iterrows()]

    # Incidencias por NO participar en Kaizen
    df_admin = pd.DataFrame([{
        "FECHA": f"{anio_num}-{mes_num:02d}-28",
        "EMPLEADO": e,
        "INCIDENCIA": "Falla Admin/Kaizen",
        "OBSERVACION": "No presento propuesta de mejora Kaizen"
    } for e in nopart])

    # 3. Bitácora Manual
    df_bit = pd.DataFrame(columns=["FECHA", "EMPLEADO", "INCIDENCIA", "OBSERVACION"])
    if not df_bitacora.empty:
        df_bitacora_copy = df_bitacora.copy()
        df_bitacora_copy['FECHA'] = pd.to_datetime(df_bitacora_copy['FECHA'], errors='coerce')
        df_bit = df_bitacora_copy[
            (df_bitacora_copy['FECHA'].dt.month == mes_num) &
            (df_bitacora_copy['FECHA'].dt.year  == anio_num)
        ].copy()
        if not df_bit.empty:
            df_bit['FECHA'] = df_bit['FECHA'].dt.strftime('%Y-%m-%d')

    # 4. Consolidar
    df_todas = pd.concat([df_ret, df_bit, df_admin], ignore_index=True)

    # 5. Calcular Nómina Final
    nomina = []
    for emp in sorted(list(set(EMPLEADOS_DB.values()))):
        df_e   = df_todas[df_todas['EMPLEADO'] == emp]
        c_ret  = len(df_e[df_e['INCIDENCIA'] == 'Retardo Biométrico'])
        f_kz   = not df_e[df_e['INCIDENCIA'] == 'Falla Admin/Kaizen'].empty
        f_gr   = len(df_e[df_e['INCIDENCIA'].str.contains('Grave', case=False, na=False)])
        f_otras = len(df_e) - c_ret - (1 if f_kz else 0)

        bp = 500 if c_ret <= 3 else 0
        bu = 500 if f_otras == 0 else 0
        ba = 0   if f_kz    else 500

        if f_gr > 0:
            bp, bu, ba = 0, 0, 0

        nomina.append({
            "COLABORADOR": emp,
            "RETARDOS": c_ret,
            "INCIDENCIAS LEVES/GRAVES": f_otras,
            "$ PUNTUAL": bp,
            "$ UNIFORM": bu,
            "$ ADMIN": ba,
            "TOTAL A PAGAR": bp + bu + ba
        })

    return pd.DataFrame(nomina), df_todas, df_ret, stats_k, props, df_bio

# ==========================================
# 5. APLICACIÓN PRINCIPAL (ENRUTADOR)
# ==========================================
def main():
    with st.sidebar:
        st.markdown("### NAVEGADOR EMPRESARIAL")
        modulo_activo = st.radio("Seleccione el Módulo:", ["Dashboard de Operaciones", "Gestión de Nómina", "Turno Nocturno"], label_visibility="collapsed")
        st.divider()
        st.markdown("### FILTROS")
        
        fecha_inicio, fecha_fin, mes_eval, anio_eval, file_asis = None, None, None, None, None
        agrupacion_temporal = "Día"
        
        if modulo_activo in ["Dashboard de Operaciones", "Turno Nocturno"]:
            hoy = datetime.now()
            fechas = st.date_input("Rango de Análisis", [hoy - timedelta(days=30), hoy])
            if len(fechas) == 2: fecha_inicio, fecha_fin = fechas
            else: st.stop()
            
            if modulo_activo == "Dashboard de Operaciones":
                agrupacion_temporal = st.selectbox("Agrupación Gráficas (Evolución):", ["Día", "Semana", "Mes", "Año"])
        else:
            mes_eval = st.selectbox("Mes", range(1, 13), index=datetime.now().month-1)
            anio_eval = st.number_input("Año", min_value=2020, max_value=2050, value=datetime.now().year)
            file_asis = st.file_uploader("Archivo Biométrico (.xlsx)", type=['xlsx', 'csv'])
            
        st.divider()
        if st.button("Sincronizar Datos DB", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ---------------------------------------------------------
    # MÓDULO 1: DASHBOARD OPERATIVO
    # ---------------------------------------------------------
    if modulo_activo == "Dashboard de Operaciones":
        st.title("Dashboard de Operaciones")
        data = cargar_datos_operaciones()
        if data is None: st.stop()
        df_ron, df_rop, df_serv = data["n"].copy(), data["v"].copy(), data["s"].copy()

        ico = 0
        df_a, df_c, df_evol_base, df_plot, df_ranking = pd.DataFrame(columns=['index', 'V']), pd.DataFrame(columns=['index', 'V']), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        kpi = {}

        try:
            def traducir(s): return pd.to_numeric(s.astype(str).str.strip().str.lower().replace({'sí': 10, 'si': 10, 'no': 0, 'cumple': 10, 'no cumple': 0, 'separada': 10, 'bien': 10, 'ok': 10, 'limpio': 10, 'sucio': 0}), errors='coerce') * 10
            def find_col(df, keywords):
                for kw in keywords:
                    cols = [c for c in df.columns if kw.lower() in c.lower()]
                    if cols: return cols[0]
                return None

            c_5s, c_cam = find_col(df_rop, ["orden", "5s"]), find_col(df_rop, ["tendido", "cama"])
            col_enf = find_col(df_rop, ["asignado", "evaluad", "enfermera", "nombre"])
            c_uni, c_bas = find_col(df_serv, ["uniforme"]), find_col(df_serv, ["basura"])
            c_lav_r, c_lav_j = find_col(df_serv, ["ropa", "separad"]), find_col(df_serv, ["jabón", "jabon"])
            c_lim = find_col(df_serv, ["zonas asignadas", "limpieza"])

            if not all([c_5s, c_cam, col_enf, c_uni, c_bas, c_lav_r, c_lav_j, c_lim]):
                raise ValueError("Faltan columnas críticas en los Google Sheets.")

            for df in [df_ron, df_rop, df_serv]:
                df['Marca temporal'] = pd.to_datetime(df['Marca temporal'], dayfirst=True, errors='coerce')
                df['Fecha'] = df['Marca temporal'].dt.date
                
            df_ron = df_ron[(df_ron['Fecha'] >= fecha_inicio) & (df_ron['Fecha'] <= fecha_fin)]
            df_rop = df_rop[(df_rop['Fecha'] >= fecha_inicio) & (df_rop['Fecha'] <= fecha_fin)]
            df_serv = df_serv[(df_serv['Fecha'] >= fecha_inicio) & (df_serv['Fecha'] <= fecha_fin)]

            for c in [c_5s, c_cam]: df_rop[c] = traducir(df_rop[c])
            df_rop['Promedio'] = (df_rop[c_5s] + df_rop[c_cam]) / 2
            for c in [c_uni, c_bas, c_lav_r, c_lav_j, c_lim]: df_serv[c] = traducir(df_serv[c])

            t_A = sum(1 for d in pd.date_range(fecha_inicio, fecha_fin) if d.weekday() in [0, 2, 4])
            t_B = sum(1 for d in pd.date_range(fecha_inicio, fecha_fin) if d.weekday() in [1, 3, 5])
            df_ron['Hora'] = df_ron['Marca temporal'].dt.hour
            df_ron['Bloque'] = df_ron['Hora'].apply(lambda h: "B1" if 21<=h<=23 else "B2" if 0<=h<=3 else "B3" if 4<=h<=6 else None)
            
            rango_fechas = pd.date_range(fecha_inicio, fecha_fin)
            df_ron_val = df_ron[df_ron['Bloque'].notnull()].drop_duplicates(subset=['Fecha', 'Enfermera', 'Bloque'])
            conteo_noc = df_ron_val.groupby('Fecha').size()
            noc_diario = []
            for d in rango_fechas:
                exp = (len(ENFERMERAS_ROL_A)*3) if d.weekday() in [0,2,4] else (len(ENFERMERAS_ROL_B)*3 if d.weekday() in [1,3,5] else 0)
                noc_diario.append(min((conteo_noc.get(d.date(), 0)/exp)*100, 100) if exp>0 else None)
                
            df_evol_base = pd.DataFrame(index=rango_fechas.date)
            df_evol_base['Nocturno'] = noc_diario
            df_evol_base['Vespertino'] = df_evol_base.index.map(df_rop.groupby('Fecha')['Promedio'].mean())
            df_evol_base['Cocina'] = df_evol_base.index.map(df_serv.groupby('Fecha')[[c_uni, c_bas]].mean().mean(axis=1))
            df_evol_base['Lavandería'] = df_evol_base.index.map(df_serv.groupby('Fecha')[[c_lav_r, c_lav_j]].mean().mean(axis=1))
            df_evol_base['Limpieza'] = df_evol_base.index.map(df_serv.groupby('Fecha')[c_lim].mean())
            df_evol_base = df_evol_base.ffill().bfill().fillna(0)
            df_evol_base.index = pd.to_datetime(df_evol_base.index)

            if not df_evol_base.empty:
                if agrupacion_temporal == "Semana":
                    df_plot = df_evol_base.resample('W-MON').mean()
                    df_plot.index = df_plot.index.strftime('Semana %W - %Y')
                elif agrupacion_temporal == "Mes":
                    df_plot = df_evol_base.resample('ME').mean()
                    df_plot.index = df_plot.index.strftime('%Y-%m')
                elif agrupacion_temporal == "Año":
                    df_plot = df_evol_base.resample('YE').mean()
                    df_plot.index = df_plot.index.strftime('%Y')
                else:
                    df_plot = df_evol_base.copy()
                    df_plot.index = df_plot.index.strftime('%Y-%m-%d')

            p_noc = {enf: min((len(df_ron[(df_ron['Enfermera'] == enf) & (df_ron['Bloque'].notnull())][['Fecha', 'Bloque']].drop_duplicates()) / ((t_A if enf in ENFERMERAS_ROL_A else t_B)*3) * 100), 100) if ((t_A if enf in ENFERMERAS_ROL_A else t_B)*3) > 0 else 100 for enf in ENFERMERAS_NOCHE}
            v_noc = sum(p_noc.values()) / len(p_noc) if p_noc else 0

            kpi = {"Nocturno": v_noc, "Vespertino": df_rop['Promedio'].mean(), "Cocina": (df_serv[c_uni].mean() + df_serv[c_bas].mean()) / 2, "Lavandería": (df_serv[c_lav_r].mean() + df_serv[c_lav_j].mean()) / 2, "Limpieza": df_serv[c_lim].mean()}
            kpi = {k: (v if pd.notna(v) else 0) for k, v in kpi.items()}
            ico = sum(kpi.values()) / len(kpi) if kpi else 0
            
            df_a = pd.DataFrame.from_dict(kpi, orient='index', columns=['V']).sort_values('V', ascending=False).reset_index()
            df_c = pd.DataFrame.from_dict({"Uniforme": df_serv[c_uni].mean(), "Basura": df_serv[c_bas].mean(), "Ropa": df_serv[c_lav_r].mean(), "Jabon": df_serv[c_lav_j].mean(), "Zonas": df_serv[c_lim].mean(), "5S Roperos": df_rop[c_5s].mean(), "Tendido Camas": df_rop[c_cam].mean(), "Rondines Noct": v_noc}, orient='index', columns=['V']).sort_values('V', ascending=True).reset_index()

            personal_diurno = set(df_rop[col_enf].dropna().unique()) - set(ENFERMERAS_NOCHE)
            ranking_data = [{"Colaborador": e, "Turno": "Nocturno", "Puntaje (%)": round(p_noc.get(e,0),1)} for e in ENFERMERAS_NOCHE if p_noc.get(e) is not None] + [{"Colaborador": e, "Turno": "Vespertino", "Puntaje (%)": round(df_rop[df_rop[col_enf]==e]['Promedio'].mean(),1)} for e in personal_diurno if pd.notna(df_rop[df_rop[col_enf]==e]['Promedio'].mean())]
            df_ranking = pd.DataFrame(ranking_data)
            if not df_ranking.empty: df_ranking = df_ranking.sort_values("Puntaje (%)", ascending=False).reset_index(drop=True)

        except Exception as e:
            st.error(f"Error procesando operaciones: {e}")

        html_dictamen, pdf_dictamen = generar_dictamen_operativo(ico, df_a, df_c)

        st.markdown(f"""<div class='exec-header'>
            <div><p style='margin:0; font-weight:700; color:#64748b; font-size:12px; text-transform:uppercase;'>Estatus Institucional</p>
            <h2 style='margin:0; color:{HEX_GREEN if ico >= 90 else HEX_RED};'>{"ESTABLE" if ico >= 90 else "ATENCIÓN REQUERIDA"}</h2></div>
            <div style='text-align:right;'><p style='margin:0; font-weight:700; color:#64748b; font-size:12px; text-transform:uppercase;'>ICO Maestro</p>
            <h1 style='margin:0; font-size:48px;'>{ico:.1f}%</h1></div></div>""", unsafe_allow_html=True)

        st.markdown(f"""<div class='dictamen-box'>
                <h4 class='dictamen-title'>Dictamen y Recomendaciones Ejecutivas</h4>
                <p class='dictamen-text'>{html_dictamen}</p></div>""", unsafe_allow_html=True)

        tabs_op = st.tabs(["Tablero de Control", "Evolución Temporal", "Rendimiento Individual", "Blindaje Legal", "Data Cruda"])
        
        with tabs_op[0]:
            if st.button("Generar Reporte de Operaciones (PDF)", type="primary"):
                pdf_b = generar_pdf_dashboard_op(ico, "ESTABLE" if ico >= 90 else "ATENCIÓN REQUERIDA", df_a, df_c, df_plot, agrupacion_temporal, f"{fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}", pdf_dictamen)
                st.download_button("Descargar Archivo", data=pdf_b, file_name="Reporte_Operaciones.pdf", mime="application/pdf")
            
            if kpi:
                cols = st.columns(5)
                for i, (a, v) in enumerate(kpi.items()):
                    color, flecha = (HEX_GREEN, '↑') if v >= 90 else (HEX_RED, '↓')
                    with cols[i]: st.markdown(f"<div class='kpi-card'><p class='metric-label'>{a}</p><p class='metric-value' style='color:{color};'>{v:.1f}% {flecha}</p></div>", unsafe_allow_html=True)
            
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.write("### Pareto por Área")
                if not df_a.empty:
                    fig = px.bar(df_a, x='index', y='V', text_auto='.1f', color_discrete_sequence=[HEX_NAVY])
                    fig.add_hline(y=90, line_dash="dash", line_color="red")
                    st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.write("### Análisis de Causa Raíz")
                if not df_c.empty:
                    fig_c = px.bar(df_c, x='V', y='index', orientation='h', text_auto='.1f', color_discrete_sequence=[HEX_RED])
                    fig_c.add_vline(x=90, line_dash="dash", line_color="black")
                    st.plotly_chart(fig_c, use_container_width=True)

        with tabs_op[1]:
            st.write(f"### Evolución Histórica de Todos los Departamentos ({agrupacion_temporal})")
            if not df_plot.empty:
                fig_evol = px.line(df_plot, labels={"value": "Cumplimiento (%)", "index": "Periodo", "variable": "Área Operativa"}, markers=True)
                fig_evol.add_hline(y=90, line_dash="dot", line_color="red", annotation_text="Línea Base 90%")
                st.plotly_chart(fig_evol, use_container_width=True)

        with tabs_op[2]:
            st.write("### Rendimiento Detallado por Personal")
            if not df_ranking.empty: st.dataframe(df_ranking, use_container_width=True)

        with tabs_op[3]:
            st.write("### Auditoría y Blindaje Institucional")
            cats = {
                "REGULACIÓN SANITARIA Y OPERATIVA - COPRISJAL/SSA": [
                    "[CRÍTICO - Anual] Aviso de Funcionamiento: Verificar documento vigente y exhibido.",
                    "[CRÍTICO - Anual] Responsable Sanitario: Validar aviso y nombramiento registrado.",
                    "[CRÍTICO - Diario] Medicamentos controlados: Verificar resguardo y control foliado.",
                    "[ALTO - Mensual] Accesibilidad NOM-031: Verificar rampas y barandales.",
                    "[CRÍTICO - Mensual] Expedientes clínicos: Validar integración y resguardo.",
                    "[CRÍTICO - Semanal] Manejo RPBI: Verificar contenedores y bolsas.",
                    "[ALTO - Diario] Higiene alimentaria: Control de temperaturas y limpieza en cocina."
                ],
                "SEGURIDAD Y SALUD LABORAL - STPS": [
                    "[ALTO - Anual] RIT: Verificar Reglamento Interior de Trabajo firmado.",
                    "[ALTO - Anual] NOM-035: Aplicar guía preventiva de riesgos psicosociales.",
                    "[ALTO - Trimestral] Comisión Mixta: Validar actas y recorridos de seguridad.",
                    "[ALTO - Semestral] Ergonomía (Movilización pacientes): Verificar capacitación y DC-3."
                ],
                "PROTECCIÓN CIVIL Y ECOLOGÍA MUNICIPAL": [
                    "[CRÍTICO - Anual] Programa Interno PIPC: Validar autorización vigente.",
                    "[CRÍTICO - Anual] Responsabilidad Civil: Verificar póliza de seguro vigente.",
                    "[CRÍTICO - Anual] Dictamen estructural: Validar dictamen DRO.",
                    "[CRÍTICO - Mensual] Extintores: Revisar vigencia, señalización y recarga.",
                    "[CRÍTICO - Mensual] Detectores de humo: Validar funcionamiento.",
                    "[ALTO - Mensual] Evacuación: Verificar rutas, luces y señalética.",
                    "[ALTO - Anual] Brigadas: Validar constancias de capacitación (DC-3).",
                    "[CRÍTICO - Semestral] Simulacros: Revisar bitácoras y formatos de evacuación."
                ],
                "CUMPLIMIENTO LEGAL Y PRIVACIDAD": [
                    "[ALTO - Permanente] Aviso de privacidad INAI: Verificar exhibición y anexos.",
                    "[CRÍTICO - Permanente] Datos sensibles: Confirmar consentimientos en expedientes.",
                    "[ALTO - Permanente] Contratos de servicios: Verificar contratos firmados y vigentes.",
                    "[ALTO - Anual] Contrato adhesión PROFECO: Confirmar registro vigente."
                ]
            }
            if 'checks' not in st.session_state: st.session_state.checks = {i: False for sub in cats.values() for i in sub}
            c_l1, c_l2 = st.columns([0.7, 0.3])
            with c_l1:
                for cat, items in cats.items():
                    with st.expander(cat, expanded=True):
                        for item in items: st.session_state.checks[item] = st.checkbox(item, value=st.session_state.checks[item], key=item)
            pct = (sum(st.session_state.checks.values()) / len(st.session_state.checks)) * 100
            with c_l2:
                st.write(f"#### Índice: {int(pct)}%")
                st.progress(pct / 100)
                if st.button("Generar Reporte Legal"): st.session_state['pl'] = generar_pdf_legal_bytes(cats, st.session_state.checks, pct)
                if 'pl' in st.session_state: st.download_button("Descargar Auditoría PDF", data=st.session_state['pl'], file_name=f"Legal_{datetime.now().strftime('%d%m%Y')}.pdf", mime="application/pdf")

        with tabs_op[4]:
            st.write("### Tuberías de Datos Operativas (Data Cruda)")
            sub1, sub2, sub3 = st.tabs(["Servicios Generales", "Enfermería Vespertina", "Rondines Nocturnos"])
            with sub1: st.dataframe(df_serv, use_container_width=True)
            with sub2: st.dataframe(df_rop, use_container_width=True)
            with sub3: st.dataframe(df_ron, use_container_width=True)

    # ---------------------------------------------------------
    # MÓDULO 2: GESTIÓN DE NÓMINA (CON DESGLOSE POR EMPLEADO)
    # ---------------------------------------------------------
    elif modulo_activo == "Gestión de Nómina":
        st.title("Gestión de Nómina y Mejora Continua")
        df_bitacora = cargar_bitacora()
        tabs_nom = st.tabs(["Dictamen de Nómina", "Bitácora Digital", "Data Cruda"])

        with tabs_nom[1]:
            st.write("### Registro Manual de Supervisión")
            with st.form("form_incidencia"):
                c_f1, c_f2, c_f3 = st.columns(3)
                with c_f1: f_fecha = st.date_input("Fecha")
                with c_f2: f_emp = st.selectbox("Colaborador", sorted(list(set(EMPLEADOS_DB.values()))))
                with c_f3: f_inc = st.selectbox("Incidencia", TIPO_INCIDENCIAS)
                f_obs = st.text_input("Observaciones")
                if st.form_submit_button("Guardar en Bitácora"):
                    guardar_incidencia(f_fecha.strftime('%Y-%m-%d'), f_emp, f_inc, f_obs)
                    st.rerun()
            st.dataframe(df_bitacora, use_container_width=True)
            if not df_bitacora.empty:
                b_idx = st.number_input("ID a borrar", 0, len(df_bitacora)-1, 0)
                if st.button("Eliminar"): borrar_incidencia(b_idx); st.rerun()

        with tabs_nom[0]:
            if file_asis:
                if st.button("Procesar Nómina vs Kaizen", type="primary"):
                    with st.spinner("Procesando..."):
                        st.session_state['nom'] = procesar_super_nomina(limpiar_biometrico(file_asis.read()), df_bitacora, fetch_kaizen_data(), mes_eval, anio_eval)
            
            if 'nom' in st.session_state:
                df_n, df_i, df_r, s_k, p_k, df_bio_nom = st.session_state['nom']
                m_str = f"{mes_eval:02d}/{anio_eval}"
                st.markdown(f"<h1 style='color:{HEX_GREEN};'>Total a Dispersar: ${df_n['TOTAL A PAGAR'].sum():,}</h1>", unsafe_allow_html=True)

                html_dictamen, pdf_dictamen = generar_dictamen_nomina(s_k, df_r)

                st.markdown(f"""<div class='dictamen-box'>
                        <h4 class='dictamen-title'>Dictamen y Recomendaciones Ejecutivas</h4>
                        <p class='dictamen-text'>{html_dictamen}</p></div>""", unsafe_allow_html=True)

                pdf_b = generar_pdf_nomina(df_n, df_i, df_r, s_k, p_k, df_bio_nom, mes_eval, anio_eval, m_str, pdf_dictamen)
                st.download_button("Descargar Reporte de Nómina (PDF)", data=pdf_b, file_name=f"Nomina_{m_str.replace('/','_')}.pdf", mime="application/pdf")
                
                st.write("#### 1. Resumen General de Pagos por Rubro")
                st.dataframe(df_n, use_container_width=True, hide_index=True)
                
                st.divider()
                st.write("#### 2. Desglose Histórico e Individual de Incidencias")
                for emp in sorted(df_n['COLABORADOR'].unique()):
                    df_emp_inc = df_i[df_i['EMPLEADO'] == emp]
                    if not df_emp_inc.empty:
                        with st.expander(f"Ver incidencias de: {emp}"):
                            st.dataframe(df_emp_inc[['FECHA', 'INCIDENCIA', 'OBSERVACION']], use_container_width=True, hide_index=True)

        with tabs_nom[2]:
            if 'nom' in st.session_state:
                sub1, sub2 = st.tabs(["Retardos Biométricos", "Propuestas Kaizen"])
                with sub1: st.dataframe(st.session_state['nom'][2], use_container_width=True)
                with sub2: st.dataframe(fetch_kaizen_data(), use_container_width=True)

    # ---------------------------------------------------------
    # MÓDULO 3: TURNO NOCTURNO
    # ---------------------------------------------------------
    elif modulo_activo == "Turno Nocturno":
        st.title("Evaluación de Turno Nocturno")
        data = cargar_datos_operaciones()
        if data is None: st.stop()
        
        df_ron = data["n"].copy()
        df_ron['Marca temporal'] = pd.to_datetime(df_ron['Marca temporal'], dayfirst=True, errors='coerce')
        df_ron['Fecha'] = df_ron['Marca temporal'].dt.date
        df_ron = df_ron[(df_ron['Fecha'] >= fecha_inicio) & (df_ron['Fecha'] <= fecha_fin)]

        t_A = sum(1 for d in pd.date_range(fecha_inicio, fecha_fin) if d.weekday() in [0, 2, 4] and d.weekday() != 6)
        t_B = sum(1 for d in pd.date_range(fecha_inicio, fecha_fin) if d.weekday() in [1, 3, 5] and d.weekday() != 6)
        
        df_ron['Hora'] = df_ron['Marca temporal'].dt.hour
        df_ron['Bloque'] = df_ron['Hora'].apply(lambda h: "B1" if 21<=h<=23 else "B2" if 0<=h<=3 else "B3" if 4<=h<=6 else None)
        df_valido = df_ron[df_ron['Bloque'].notnull()].drop_duplicates(subset=['Fecha', 'Enfermera', 'Bloque'])

        df_ron_sort = df_ron.sort_values(by=['Enfermera', 'Marca temporal'])
        df_ron_sort['Diff'] = df_ron_sort.groupby('Enfermera')['Marca temporal'].diff().dt.total_seconds()
        alertas = len(df_ron_sort[df_ron_sort['Diff'] < 60])
        escaneos = len(df_ron)

        datos_noc = []
        for enf in ENFERMERAS_NOCHE:
            turnos_m = t_A if enf in ENFERMERAS_ROL_A else t_B
            rondas_m = turnos_m * 3
            rondas_r = len(df_valido[df_valido['Enfermera'] == enf])
            pct = min((rondas_r / rondas_m * 100), 100) if rondas_m > 0 else 100
            datos_noc.append({"Colaborador": enf, "Turnos Meta": turnos_m, "Meta Rondas": rondas_m, "Rondas Real.": rondas_r, "% Cumplimiento": pct})
        
        df_resumen = pd.DataFrame(datos_noc)
        v_noc = df_resumen['% Cumplimiento'].mean() if not df_resumen.empty else 0

        st.markdown(f"""<div class='exec-header'>
            <div><p style='margin:0; font-weight:700; color:#64748b; font-size:12px; text-transform:uppercase;'>Cumplimiento de Seguridad</p>
            <h2 style='margin:0; color:{HEX_GREEN if v_noc >= 90 else HEX_RED};'>{"ESTABLE" if v_noc >= 90 else "ALERTA"}</h2></div>
            <div style='text-align:right;'><p style='margin:0; font-weight:700; color:#64748b; font-size:12px; text-transform:uppercase;'>Promedio Global Nocturno</p>
            <h1 style='margin:0; font-size:48px;'>{v_noc:.1f}%</h1></div></div>""", unsafe_allow_html=True)

        html_dictamen, pdf_dictamen = generar_dictamen_rondines(alertas, df_resumen)
        st.markdown(f"""<div class='dictamen-box'>
                <h4 class='dictamen-title'>Dictamen y Recomendaciones Ejecutivas</h4>
                <p class='dictamen-text'>{html_dictamen}</p></div>""", unsafe_allow_html=True)

        tabs_noc = st.tabs(["Auditoría de Rondas", "Log Antifraude"])
        with tabs_noc[0]:
            if st.button("Generar Reporte Rondines (PDF)", type="primary"):
                pdf_b = generar_pdf_rondines(df_resumen, escaneos, alertas, f"{fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}", pdf_dictamen)
                st.download_button("Descargar Archivo", data=pdf_b, file_name="Reporte_Rondines.pdf", mime="application/pdf")
            st.dataframe(df_resumen, use_container_width=True, hide_index=True)
        with tabs_noc[1]:
            st.write(f"**Escaneos Totales:** {escaneos} | **Alertas Fraude (<60s):** {alertas}")
            st.dataframe(df_ron_sort[['Marca temporal', 'Enfermera', 'Diff']].sort_values(by="Marca temporal", ascending=False), use_container_width=True)

if __name__ == "__main__":
    main()