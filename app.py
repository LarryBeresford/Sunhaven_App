import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import gspread
import json
import os
import io
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
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

st.set_page_config(page_title="Sunhaven Command Center", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC; }
    .block-container { padding-top: 1.5rem; max-width: 96%; }
    
    /* Clean UI */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header [data-testid="stSidebarCollapsedControl"] {visibility: visible !important;} [data-testid="collapsedControl"] {visibility: visible !important;}
    
    
    /* Typography */
    h1, h2, h3 { color: #0F172A; font-weight: 800; letter-spacing: -0.025em; }
    .section-title { font-size: 1.15rem; font-weight: 700; color: #334155; border-bottom: 1px solid #E2E8F0; padding-bottom: 0.75rem; margin-bottom: 1.25rem; margin-top: 0.5rem; }
    
    /* Premium Cards */
    .premium-card { background-color: #ffffff; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03); border: 1px solid #E2E8F0; margin-bottom: 1.5rem; transition: transform 0.2s ease, box-shadow 0.2s ease; }
    .premium-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.08); }
    
    /* KPIs */
    .kpi-container { display: flex; flex-direction: column; justify-content: space-between; height: 100%; }
    .kpi-title { font-size: 0.8rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
    .kpi-value { font-size: 2.2rem; font-weight: 800; color: #0F172A; line-height: 1.1; }
    .kpi-trend-up { color: #10B981; font-size: 0.85rem; font-weight: 600; display: flex; align-items: center; gap: 0.25rem; margin-top: 8px; }
    .kpi-trend-down { color: #EF4444; font-size: 0.85rem; font-weight: 600; display: flex; align-items: center; gap: 0.25rem; margin-top: 8px; }
    
    /* Alerts */
    .dictamen-box { background: linear-gradient(135deg, #ffffff 0%, #FFF7ED 100%); border-left: 6px solid #F97316; padding: 24px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.04); margin-bottom: 2rem; border-top: 1px solid #F1F5F9; border-right: 1px solid #F1F5F9; border-bottom: 1px solid #F1F5F9; }
    .dictamen-title { color: #C2410C; font-size: 0.95rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0; margin-bottom: 10px;}
    .dictamen-text { color: #334155; font-size: 1rem; line-height: 1.6; margin: 0;}
    
    /* Tabs & Buttons */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 2px solid #E2E8F0; padding-bottom: 0; }
    .stTabs [data-baseweb="tab"] { height: 52px; background-color: transparent; border: none; padding: 0 22px; font-weight: 700; color: #64748B; font-size: 1.05rem; border-radius: 6px 6px 0 0; transition: all 0.2s; }
    .stTabs [aria-selected="true"] { color: #0F172A !important; border-bottom: 3px solid #F97316 !important; background-color: #ffffff !important; }
    
    .stButton > button, .stDownloadButton > button { border-radius: 6px !important; font-weight: 600 !important; transition: all 0.15s ease !important; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%) !important; border: none !important; color: white !important; }
    .stButton > button:hover, .stDownloadButton > button:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.15); filter: brightness(1.08); }
    .stButton > button:active, .stDownloadButton > button:active { transform: scale(0.97) !important; box-shadow: inset 0 2px 6px rgba(0,0,0,0.25) !important; filter: brightness(0.92) !important; }
</style>
""", unsafe_allow_html=True)

HEX_NAVY, HEX_RED, HEX_GREEN, HEX_SUN = "#1e293b", "#dc2626", "#10b981", "#d35400"
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
SUPERVISORAS_ENFERMERIA = ["Blanca Aracely Figueroa Marroquín", "Yareli Yamile Luquin Puga"]
ENFERMERAS_RETARDO      = set(ENFERMERAS_LISTA) - set(SUPERVISORAS_ENFERMERIA)  # Solo turno fijo, sin supervisoras
CHECADORES_ESPECIALES = ["CESAR", "MONI", "MARTHACASTRO", "HUGO"] 
HORA_ENTRADA_DIA, HORA_ENTRADA_NOCHE = datetime.strptime("08:15", "%H:%M").time(), datetime.strptime("20:15", "%H:%M").time()
HORA_SALIDA_DIA   = datetime.strptime("19:45", "%H:%M").time()
TIPO_INCIDENCIAS = ["Falta de uniforme (Leve)", "Uso de celular (Leve)", "No hacer entrega (Leve)", "No hacer ronda (Leve)", "Salida anticipada (Leve)", "AGRESIÓN / CONFLICTO (Grave)", "REGLA DE ORO (Grave)"]

# ==========================================
# 1. CLASE MAESTRA DE PDF Y HELPERS UI
# ==========================================
def render_kpi_card(title, value, threshold=90, suffix="%"):
    color = HEX_GREEN if float(value) >= threshold else HEX_RED
    icon = "↗" if float(value) >= threshold else "↘"
    css_class = "kpi-trend-up" if float(value) >= threshold else "kpi-trend-down"
    st.markdown(f"""
    <div class="premium-card" style="padding: 20px;">
        <div class="kpi-container">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{float(value):.1f}{suffix}</div>
            <div class="{css_class}" style="color: {color};">
                <span>{icon}</span> <span>{'Estado Óptimo' if float(value)>=threshold else 'Requiere Atención'}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def apply_plotly_theme(fig):
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_family="Inter",
        font_color="#475569", title_font_color="#0F172A", title_font_weight="bold",
        margin=dict(l=10, r=10, t=40, b=20),
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Inter", bordercolor="#E2E8F0")
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#CBD5E1")
    fig.update_yaxes(showgrid=True, gridcolor="#F1F5F9", zeroline=False)
    return fig

def sanitizar_texto(texto):
    return str(texto).replace('•', '-').replace('“', '"').replace('”', '"').replace('–', '-').replace('—', '-').encode('latin-1', 'replace').decode('latin-1')

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

def safe_add_section(pdf, titulo, min_space=70):
    """Salta de página si no hay espacio suficiente antes de un título de sección."""
    if pdf.get_y() > (297 - min_space):
        pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 8, sanitizar_texto(titulo), 0, 1, 'L')
    pdf.set_draw_color(*C_SUN)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

def img_centrada(pdf, path, w=185):
    """Inserta imagen centrada horizontalmente en página A4 (210mm)."""
    if path and os.path.exists(path):
        x = (210 - w) / 2
        pdf.image(path, x=x, w=w)

def bloque_conclusion(pdf, texto):
    """Bloque final de conclusiones con estilo premium."""
    if pdf.get_y() > 240:
        pdf.add_page()
    pdf.ln(6)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(240, 245, 250)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 9, sanitizar_texto("  CONCLUSIONES Y RECOMENDACIONES EJECUTIVAS"), 1, 1, 'L', True)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 6, sanitizar_texto(texto), 1, 'L')

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
        return "Sin datos suficientes para este periodo.", "Sin datos suficientes para este periodo."

    areas_bajas  = df_a[df_a['V'] < 90].sort_values('V', ascending=True)
    causas_bajas = df_c[df_c['V'] < 90].sort_values('V', ascending=True)
    top_areas    = [r['index'] for _, r in areas_bajas.head(2).iterrows()]
    top_causas   = [r['index'] for _, r in causas_bajas.head(2).iterrows()]

    if ico >= 90:
        label   = "Estado Óptimo"
        color   = "#10b981"
        html    = (f"<strong>{label}</strong> — El índice de cumplimiento operativo alcanzó el "
                   f"<strong>{ico:.1f}%</strong>, superando la línea base institucional. "
                   f"Todos los departamentos se encuentran dentro del rango esperado. "
                   f"Se recomienda mantener los protocolos vigentes y reconocer el desempeño del equipo.")
        pdf_txt = (f"El índice de cumplimiento operativo alcanzó el {ico:.1f}%, superando la meta institucional. "
                   f"Todos los departamentos operan dentro del rango esperado. "
                   f"Se recomienda mantener los protocolos vigentes y reconocer el desempeño del equipo.")
    elif ico >= 75:
        foco    = top_areas[0] if top_areas else "área general"
        causa   = top_causas[0] if top_causas else "criterio operativo"
        label   = "Alerta Preventiva"
        html    = (f"<strong>{label}</strong> — El índice alcanzó el <strong>{ico:.1f}%</strong>, "
                   f"con oportunidades de mejora identificadas. El área de <em>{foco}</em> presenta "
                   f"el mayor margen de mejora, siendo <em>{causa}</em> el criterio con mayor impacto. "
                   f"Se recomienda una sesión de calibración con el personal involucrado esta semana.")
        pdf_txt = (f"El índice de cumplimiento operativo se ubicó en {ico:.1f}%, con oportunidades de mejora "
                   f"identificadas. El área de {foco} presenta el mayor margen de desarrollo, "
                   f"siendo {causa} el criterio con mayor incidencia. "
                   f"Se recomienda agendar una sesión de retroalimentación con el equipo afectado.")
    else:
        foco    = top_areas[0] if top_areas else "área general"
        causa   = top_causas[0] if top_causas else "criterio operativo"
        label   = "Atención Requerida"
        html    = (f"<strong>{label}</strong> — El índice se situó en <strong>{ico:.1f}%</strong>, "
                   f"por debajo del estándar institucional. El área de <em>{foco}</em> requiere "
                   f"intervención inmediata; la principal causa raíz identificada es <em>{causa}</em>. "
                   f"Se exige implementar acciones correctivas esta semana.")
        pdf_txt = (f"El índice de cumplimiento operativo se situó en {ico:.1f}%, por debajo del estándar. "
                   f"El área de {foco} requiere intervención inmediata. "
                   f"La principal causa raíz identificada es {causa}. "
                   f"Se exige implementar acciones correctivas de forma urgente.")

    return html, pdf_txt

def generar_dictamen_nomina(stats_kaizen, df_retardos):
    t_kz   = stats_kaizen['curr_si'] + stats_kaizen['curr_no']
    pct_kz = (stats_kaizen['curr_si'] / t_kz * 100) if t_kz > 0 else 0

    # ── Kaizen ──────────────────────────────────────────────────────
    if pct_kz >= 85:
        kz_html = (f"<strong>Mejora Continua:</strong> La participación en el programa Kaizen "
                   f"alcanzó el <strong>{pct_kz:.0f}%</strong> — un resultado destacable. "
                   f"Se recomienda visibilizar las propuestas más innovadoras en la próxima reunión de equipo.")
        kz_pdf  = (f"La participación en el programa Kaizen alcanzó el {pct_kz:.0f}%, un resultado "
                   f"destacable para el periodo. Se recomienda visibilizar las propuestas más innovadoras "
                   f"en la próxima reunión de equipo y reconocer públicamente a los colaboradores más activos.")
    else:
        kz_html = (f"<strong>Mejora Continua:</strong> La participación en Kaizen se ubicó en "
                   f"<strong>{pct_kz:.0f}%</strong> este periodo. Hay margen de mejora en la adopción "
                   f"del programa. Se recomienda reforzar la comunicación sobre su importancia.")
        kz_pdf  = (f"La participación en el programa Kaizen se ubicó en {pct_kz:.0f}% este periodo, "
                   f"con margen de mejora en la adopción. Se recomienda reforzar la comunicación "
                   f"sobre la importancia del programa y dar seguimiento oportuno a los colaboradores omisos.")

    # ── Puntualidad ─────────────────────────────────────────────────
    if not df_retardos.empty:
        peor_emp  = df_retardos['EMPLEADO'].value_counts().index[0]
        ret_html  = (f"<strong>Puntualidad:</strong> Se registraron incidencias de asistencia en el periodo. "
                     f"El colaborador con mayor frecuencia de registros tardíos es <em>{peor_emp}</em>. "
                     f"Se recomienda agendar una conversación de seguimiento.")
        ret_pdf   = (f"Se registraron incidencias de asistencia durante el periodo. "
                     f"El colaborador con mayor frecuencia de registros tardíos es {peor_emp}. "
                     f"Se recomienda agendar una conversación de seguimiento para reforzar el compromiso con el horario.")
    else:
        ret_html  = ("<strong>Puntualidad:</strong> El equipo mantuvo una puntualidad ejemplar "
                     "durante todo el periodo. Sin incidencias relevantes que requieran atención.")
        ret_pdf   = ("El equipo mantuvo una puntualidad ejemplar durante el periodo evaluado, "
                     "sin incidencias relevantes que requieran atención inmediata.")

    html     = kz_html + "<br><br>" + ret_html
    pdf_text = kz_pdf  + "\n\n"   + ret_pdf
    return html, pdf_text
def generar_dictamen_rondines(alertas_fraude, df_resumen):
    partes_html, partes_pdf = [], []

    # ── Integridad ───────────────────────────────────────────────────
    if alertas_fraude > 0:
        partes_html.append(
            f"<strong>Integridad de Registros:</strong> El sistema detectó {alertas_fraude} "
            f"escaneo{'s' if alertas_fraude > 1 else ''} con intervalos de tiempo inconsistentes. "
            f"Se recomienda cruzar los horarios marcados con el sistema de cámaras de vigilancia "
            f"antes de tomar medidas disciplinarias.")
        partes_pdf.append(
            f"INTEGRIDAD: El sistema detectó {alertas_fraude} escaneo(s) con intervalos de tiempo "
            f"inconsistentes entre registros consecutivos del mismo colaborador. Se recomienda cruzar "
            f"los horarios con el sistema de videovigilancia antes de tomar medidas disciplinarias.")
    else:
        partes_html.append(
            "<strong>Integridad de Registros:</strong> No se detectaron inconsistencias en los "
            "patrones de escaneo durante el periodo. Los registros presentan una distribución "
            "temporal coherente con la operación presencial esperada.")
        partes_pdf.append(
            "INTEGRIDAD: No se detectaron inconsistencias en los patrones de escaneo durante "
            "el periodo. Los registros presentan una distribución temporal coherente con la "
            "operación presencial esperada.")

    # ── Desempeño ────────────────────────────────────────────────────
    bajos = df_resumen[df_resumen['% Cumplimiento'] < 90] if not df_resumen.empty else pd.DataFrame()
    if not bajos.empty:
        nombres = ", ".join(bajos['Colaborador'].tolist())
        partes_html.append(
            f"<strong>Desempeño Operativo:</strong> Se identificaron colaboradoras con cobertura "
            f"por debajo del estándar institucional: <em>{nombres}</em>. Se recomienda una "
            f"reunión de seguimiento para identificar las causas y establecer compromisos de mejora.")
        partes_pdf.append(
            f"DESEMPEÑO: Se identificaron colaboradoras con cobertura por debajo del estándar "
            f"institucional: {nombres}. Se recomienda una reunión de seguimiento para identificar "
            f"las causas y establecer compromisos de mejora concretos.")
    else:
        partes_html.append(
            "<strong>Desempeño Operativo:</strong> El equipo nocturno alcanzó los estándares de "
            "cobertura establecidos durante el periodo. Se reconoce el compromiso del personal "
            "con la seguridad y bienestar de los residentes.")
        partes_pdf.append(
            "DESEMPEÑO: El equipo nocturno alcanzó los estándares de cobertura establecidos. "
            "Se reconoce el compromiso del personal con la seguridad y bienestar de los residentes.")

    return "<br><br>".join(partes_html), "\n\n".join(partes_pdf)

# ==========================================
# 3. GENERADORES DE PDF POR MÓDULO
# ==========================================
def generar_pdf_dashboard_op(ico, estatus, df_a, df_c, df_evol, agrupacion, fecha_str, pdf_dictamen):
    temp_dir = os.path.join(os.path.dirname(__file__), f'temp_img_{uuid.uuid4().hex}')
    os.makedirs(temp_dir, exist_ok=True)

    # ── Pareto por área: mayor → menor ──────────────────────────────
    df_a_sorted = df_a.sort_values('V', ascending=False)
    fig1, ax1 = plt.subplots(figsize=(11, 5))
    bar_colors_a = ['#10b981' if v >= 90 else '#dc2626' for v in df_a_sorted['V']]
    bars = ax1.bar(df_a_sorted['index'], df_a_sorted['V'], color=bar_colors_a, zorder=3)
    ax1.axhline(90, color='#64748b', linestyle='--', linewidth=1.5, label='Meta 90%', zorder=2)
    ax1.set_ylim(0, 112)
    ax1.set_title('Índice de Cumplimiento por Área Operativa', fontsize=12, fontweight='bold', pad=12)
    ax1.set_ylabel('Cumplimiento (%)', fontsize=10)
    ax1.yaxis.grid(True, linestyle=':', alpha=0.6, zorder=0)
    ax1.set_axisbelow(True)
    ax1.legend(fontsize=9)
    for b, v in zip(bars, df_a_sorted['V']):
        ax1.text(b.get_x() + b.get_width() / 2, v + 1.2, f'{v:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
    fig1.tight_layout()
    p_pareto = os.path.join(temp_dir, 'pareto_op.png')
    fig1.savefig(p_pareto, dpi=150, bbox_inches='tight')
    plt.close(fig1)

    # ── Causa raíz: mayor → menor (barh invertido para leer de arriba abajo) ──
    df_c_sorted = df_c.sort_values('V', ascending=True)  # ascending=True → mayor queda arriba en barh
    fig2, ax2 = plt.subplots(figsize=(11, max(4, len(df_c_sorted) * 0.5)))
    bar_colors_c = ['#10b981' if v >= 90 else '#dc2626' for v in df_c_sorted['V']]
    bars2 = ax2.barh(df_c_sorted['index'], df_c_sorted['V'], color=bar_colors_c, zorder=3)
    ax2.axvline(90, color='#64748b', linestyle='--', linewidth=1.5, label='Meta 90%', zorder=2)
    ax2.set_xlim(0, 115)
    ax2.set_title('Análisis de Causa Raíz — Criterios por Impacto', fontsize=12, fontweight='bold', pad=12)
    ax2.set_xlabel('Cumplimiento (%)', fontsize=10)
    ax2.xaxis.grid(True, linestyle=':', alpha=0.6, zorder=0)
    ax2.set_axisbelow(True)
    ax2.legend(fontsize=9)
    for b, v in zip(bars2, df_c_sorted['V']):
        ax2.text(v + 0.8, b.get_y() + b.get_height() / 2, f'{v:.1f}%', va='center', fontsize=8, fontweight='bold')
    fig2.tight_layout()
    p_causa = os.path.join(temp_dir, 'causa_op.png')
    fig2.savefig(p_causa, dpi=150, bbox_inches='tight')
    plt.close(fig2)

    # ── Evolución histórica ──────────────────────────────────────────
    fig3, ax3 = plt.subplots(figsize=(13, 5))
    if not df_evol.empty:
        colors_ev = ['#1e293b', '#d35400', '#10b981', '#3b82f6', '#8b5cf6']
        for i, col in enumerate(df_evol.columns):
            ax3.plot(df_evol.index, df_evol[col], marker='o', linewidth=2.5,
                     label=col, color=colors_ev[i % len(colors_ev)])
        ax3.axhline(90, color='#ef4444', linestyle='--', linewidth=1.5, label='Línea base 90%')
        ax3.set_title(f'Evolución Histórica Sincronizada — Agrupación: {agrupacion}', fontsize=12, fontweight='bold', pad=12)
        ax3.set_ylabel('Cumplimiento (%)', fontsize=10)
        ax3.yaxis.grid(True, linestyle=':', alpha=0.5)
        ax3.set_axisbelow(True)
        plt.xticks(rotation=40, ha='right', fontsize=8)
        ax3.legend(loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=5, fontsize=9)
    fig3.tight_layout()
    p_evol = os.path.join(temp_dir, 'evol_op.png')
    fig3.savefig(p_evol, dpi=150, bbox_inches='tight')
    plt.close(fig3)

    # ── Construir PDF ────────────────────────────────────────────────
    pdf = SunhavenPDF()
    pdf.titulo_header = "REPORTE EJECUTIVO - OPERACIONES"
    pdf.cover_page("INDICADORES OPERATIVOS (KPI)", "Estado de las Infraestructuras y Servicios", fecha_str)

    # S1 — Estatus global
    pdf.add_page()
    safe_add_section(pdf, "1. ESTATUS GLOBAL INSTITUCIONAL", min_space=80)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*C_DARK)
    pdf.cell(0, 8, sanitizar_texto(f"Índice de Cumplimiento Operativo (ICO Maestro): {ico:.1f}%"), 0, 1)
    pdf.cell(0, 8, sanitizar_texto(f"Dictamen del Sistema: {estatus}"), 0, 1)
    pdf.ln(4)

    # S2 — Pareto por área
    safe_add_section(pdf, "2. DESEMPEÑO POR ÁREA OPERATIVA", min_space=120)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    # Texto explicativo: áreas que requieren atención
    areas_criticas = df_a_sorted[df_a_sorted['V'] < 90]
    if not areas_criticas.empty:
        lista_ac = ", ".join(areas_criticas['index'].tolist())
        pdf.multi_cell(0, 5, sanitizar_texto(
            f"El siguiente pareto muestra el cumplimiento de cada área de mayor a menor. "
            f"Las barras en rojo no alcanzan el estándar institucional. "
            f"Áreas que requieren atención prioritaria: {lista_ac}."
        ), 0, 'J')
    else:
        pdf.multi_cell(0, 5, sanitizar_texto(
            "Todas las áreas superan el estándar institucional en este periodo. "
            "Las barras verdes confirman el cumplimiento generalizado de la operación."
        ), 0, 'J')
    pdf.ln(3)
    img_centrada(pdf, p_pareto, w=188)
    pdf.ln(5)

    # S3 — Causa raíz
    safe_add_section(pdf, "3. ANÁLISIS DE CAUSA RAÍZ", min_space=120)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    causas_criticas = df_c_sorted[df_c_sorted['V'] < 90].sort_values('V', ascending=True)
    if not causas_criticas.empty:
        top2 = causas_criticas.head(2)['index'].tolist()
        pdf.multi_cell(0, 5, sanitizar_texto(
            f"Los criterios con mayor impacto negativo en el desempeño operativo son: "
            f"{', '.join(top2)}. Atender estos puntos generará la mejora más significativa en el ICO Maestro."
        ), 0, 'J')
    else:
        pdf.multi_cell(0, 5, sanitizar_texto(
            "Todos los criterios operativos se encuentran dentro del rango esperado. "
            "No se identifican causas raíz críticas en este periodo."
        ), 0, 'J')
    pdf.ln(3)
    img_centrada(pdf, p_causa, w=188)
    pdf.ln(5)

    # S4 — Evolución
    pdf.add_page()
    safe_add_section(pdf, "4. EVOLUCIÓN HISTÓRICA Y TENDENCIAS", min_space=100)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 5, sanitizar_texto(
        f"Tendencia histórica de cada área operativa agrupada por {agrupacion.lower()}. "
        f"La línea punteada roja marca el estándar del 90%. "
        f"Periodos consistentemente por debajo de la línea indican un patrón crónico que requiere intervención estructural."
    ), 0, 'J')
    pdf.ln(3)
    img_centrada(pdf, p_evol, w=188)

    # Conclusiones
    bloque_conclusion(pdf, pdf_dictamen)

    shutil.rmtree(temp_dir, ignore_errors=True)
    return pdf.output(dest='S').encode('latin-1', 'replace')


def generar_pdf_nomina(df_nomina, df_incidencias, df_retardos, stats_kaizen, propuestas,
                       df_bio, mes_num, anio_num, mes_str, pdf_dictamen):
    temp_dir = os.path.join(os.path.dirname(__file__), f'temp_img_{uuid.uuid4().hex}')
    os.makedirs(temp_dir, exist_ok=True)

    # ================================================================
    # FIGURA 1: Pareto + Ranking lado a lado (figura combinada)
    # ================================================================
    fig1, (ax_par, ax_ret) = plt.subplots(1, 2, figsize=(14, 6.5))

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
    fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.5))
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
    safe_add_section(pdf, "1. ANÁLISIS DE INCIDENCIAS DEL PERIODO", min_space=120)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 5, sanitizar_texto(
        "El gráfico izquierdo muestra la frecuencia de cada tipo de incidencia de mayor a menor. "
        "El gráfico derecho es el ranking de colaboradores con registros tardíos, ordenados por frecuencia. "
        "Las incidencias marcadas en rojo representan los puntos de mayor impacto en el periodo."
    ), 0, 'J')
    pdf.ln(3)
    img_centrada(pdf, p_chart1, w=188)
    pdf.ln(5)

    # ---- SECCION 2: Tabla total a pagar ----
    pdf.add_page()
    safe_add_section(pdf, "2. TOTAL A PAGAR POR RUBRO", min_space=80)
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
    safe_add_section(pdf, "3. JUSTIFICACIÓN DE RETENCIONES Y ADVERTENCIAS", min_space=80)
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
        safe_add_section(pdf, "4. CONTROL DE HORAS SEMANALES — PERSONAL ADMINISTRATIVO", min_space=80)
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
    safe_add_section(pdf, f"{sec_base}. PROGRAMA KAIZEN — MEJORA CONTINUA", min_space=100)
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
    img_centrada(pdf, p_kz, w=175)
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

    bloque_conclusion(pdf, pdf_dictamen)

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

def generar_pdf_rondines(df_resumen, df_ron_raw, escaneos_totales, alertas_fraude, fecha_str, pdf_dictamen):
    import seaborn as sns
    import matplotlib.colors as mcolors
    temp_dir = os.path.join(os.path.dirname(__file__), f'temp_img_{uuid.uuid4().hex}')
    os.makedirs(temp_dir, exist_ok=True)

    def find_col(df, candidates):
        for c in candidates:
            if c in df.columns:
                return c
        return None

    col_enf = find_col(df_ron_raw, ["Enfermera", "Colaborador", "Nombre"])
    col_res = find_col(df_ron_raw, ["Residente Visitado", "Nombre del Residente", "Residente", "Paciente", "Habitacion"])
    col_ts  = find_col(df_ron_raw, ["Marca temporal", "Timestamp", "Fecha"])

    # ── S1: Barras de cumplimiento (verde>=90) + Pie antifraude ──
    fig1, (ax_bar, ax_pie) = plt.subplots(1, 2, figsize=(14, 5.5))
    if not df_resumen.empty:
        bar_colors = ['#10b981' if v >= 90 else '#dc2626' for v in df_resumen['% Cumplimiento']]
        ax_bar.barh(df_resumen['Colaborador'], df_resumen['% Cumplimiento'], color=bar_colors)
        ax_bar.axvline(90, color='gray', linestyle='--', linewidth=1.2, label='Meta 90%')
        ax_bar.set_xlim(0, 108)
        ax_bar.set_title('% Cumplimiento por Colaborador', fontsize=10, fontweight='bold')
        ax_bar.set_xlabel('Cumplimiento %')
        ax_bar.legend(fontsize=8)
        for i, v in enumerate(df_resumen['% Cumplimiento']):
            ax_bar.text(v + 0.5, i, f'{v:.1f}%', va='center', fontsize=8)
    val_ok   = max(escaneos_totales - alertas_fraude, 0)
    pie_vals = [val_ok, alertas_fraude] if (val_ok + alertas_fraude) > 0 else [1, 0]
    wedge_c  = ['#10b981', '#dc2626']
    ax_pie.pie(pie_vals, labels=['Escaneos Validos', 'Alertas Fraude'],
               autopct='%1.1f%%', colors=wedge_c, startangle=90,
               wedgeprops={'width': 0.60})
    ax_pie.set_title(f'Auditoria Antifraude\nTotal: {escaneos_totales} escaneos', fontsize=10, fontweight='bold')
    fig1.tight_layout()
    p_s1 = os.path.join(temp_dir, 's1_cum.png')
    fig1.savefig(p_s1, dpi=140, bbox_inches='tight')
    plt.close(fig1)

    # ── S2: Barras horizontales escaneos por residente ────────────
    p_s2 = None
    if col_res and not df_ron_raw.empty:
        try:
            vc = df_ron_raw[col_res].value_counts().head(20)
            fig2, ax2 = plt.subplots(figsize=(10, max(4, len(vc) * 0.38)))
            ax2.barh(vc.index[::-1], vc.values[::-1], color='#1e293b')
            for i, v in enumerate(vc.values[::-1]):
                ax2.text(v + 0.1, i, str(v), va='center', fontsize=8)
            ax2.set_title('Total de Escaneos QR por Residente', fontsize=10, fontweight='bold')
            ax2.set_xlabel('Escaneos')
            fig2.tight_layout()
            p_s2 = os.path.join(temp_dir, 's2_res.png')
            fig2.savefig(p_s2, dpi=140, bbox_inches='tight')
            plt.close(fig2)
        except Exception:
            pass

    # ── S3: Heatmap residente x bloque horario (seaborn) ─────────
    p_s3 = None
    if col_res and col_ts and not df_ron_raw.empty:
        try:
            df_h = df_ron_raw.copy()
            df_h[col_ts] = pd.to_datetime(df_h[col_ts], dayfirst=True, errors='coerce')
            df_h['Bloque'] = df_h[col_ts].dt.hour.apply(
                lambda h: 'B1 (23h)' if 21 <= h <= 23 else (
                    'B2 (02h)' if 0 <= h <= 3 else (
                        'B3 (05h)' if 4 <= h <= 6 else None)))
            df_hb = (df_h[df_h['Bloque'].notnull()]
                     .groupby([col_res, 'Bloque']).size()
                     .unstack(fill_value=0))
            for b in ['B1 (23h)', 'B2 (02h)', 'B3 (05h)']:
                if b not in df_hb.columns:
                    df_hb[b] = 0
            df_hb = df_hb[['B1 (23h)', 'B2 (02h)', 'B3 (05h)']]
            fig3, ax3 = plt.subplots(figsize=(7, max(4, len(df_hb) * 0.38)))
            sns.heatmap(df_hb, annot=True, fmt='d', cmap='RdYlGn',
                        ax=ax3, linewidths=0.5, linecolor='#E2E8F0')
            ax3.set_title('Intensidad de Visitas por Residente y Bloque Horario',
                          fontsize=9, fontweight='bold')
            ax3.set_xlabel('')
            fig3.tight_layout()
            p_s3 = os.path.join(temp_dir, 's3_heat.png')
            fig3.savefig(p_s3, dpi=140, bbox_inches='tight')
            plt.close(fig3)
        except Exception:
            pass

    # ── S4: Heatmap residente x dias (cobertura diaria) ──────────
    p_s4 = None
    if col_res and col_ts and not df_ron_raw.empty:
        try:
            df_d = df_ron_raw.copy()
            df_d[col_ts] = pd.to_datetime(df_d[col_ts], dayfirst=True, errors='coerce')
            df_d['Fecha'] = df_d[col_ts].dt.date
            pivot      = df_d.groupby([col_res, 'Fecha']).size().unstack(fill_value=0)
            pivot_clip = pivot.clip(upper=3)
            cmap4 = mcolors.ListedColormap(['#dc2626', '#f97316', '#fbbf24', '#10b981'])
            fig4, ax4 = plt.subplots(
                figsize=(max(8, len(pivot_clip.columns) * 0.42),
                         max(4, len(pivot_clip) * 0.38)))
            im = ax4.imshow(pivot_clip.values, aspect='auto', cmap=cmap4, vmin=0, vmax=3)
            ax4.set_xticks(range(len(pivot_clip.columns)))
            ax4.set_xticklabels([str(c) for c in pivot_clip.columns],
                                rotation=45, ha='right', fontsize=7)
            ax4.set_yticks(range(len(pivot_clip.index)))
            ax4.set_yticklabels(pivot_clip.index, fontsize=7)
            ax4.set_title('Cobertura Diaria por Residente  (0=rojo, 1=naranja, 2=amarillo, 3+=verde)',
                          fontsize=8, fontweight='bold')
            cbar = fig4.colorbar(im, ax=ax4, ticks=[0, 1, 2, 3])
            cbar.ax.set_yticklabels(['0', '1', '2', '3+'])
            fig4.tight_layout()
            p_s4 = os.path.join(temp_dir, 's4_dias.png')
            fig4.savefig(p_s4, dpi=110, bbox_inches='tight')
            plt.close(fig4)
        except Exception:
            pass

    # ── S5: Box plot tiempo entre escaneos por enfermera ─────────
    p_s5 = None
    if col_enf and col_ts and not df_ron_raw.empty:
        try:
            df_s = df_ron_raw.copy()
            df_s[col_ts] = pd.to_datetime(df_s[col_ts], dayfirst=True, errors='coerce')
            df_s = df_s.sort_values([col_enf, col_ts])
            df_s['Diff'] = df_s.groupby(col_enf)[col_ts].diff().dt.total_seconds()
            df_s2 = df_s[df_s['Diff'].notnull() & (df_s['Diff'] < 600)]
            if not df_s2.empty:
                groups = [g['Diff'].values for _, g in df_s2.groupby(col_enf)]
                labels = [k for k, _ in df_s2.groupby(col_enf)]
                fig5, ax5 = plt.subplots(figsize=(9, 4))
                bp = ax5.boxplot(groups, labels=labels, patch_artist=True,
                                 boxprops=dict(facecolor='#bfdbfe'),
                                 medianprops=dict(color='#1e293b', linewidth=2))
                ax5.axhline(60, color='#dc2626', linestyle='--',
                            linewidth=1.5, label='Limite fraude (60s)')
                ax5.set_ylabel('Segundos entre escaneos')
                ax5.set_title('Distribucion de Tiempo entre Escaneos por Enfermera',
                              fontsize=9, fontweight='bold')
                ax5.legend(fontsize=8)
                ax5.tick_params(axis='x', rotation=15, labelsize=8)
                fig5.tight_layout()
                p_s5 = os.path.join(temp_dir, 's5_box.png')
                fig5.savefig(p_s5, dpi=140, bbox_inches='tight')
                plt.close(fig5)
        except Exception:
            pass

    # ── Construir PDF ─────────────────────────────────────────────
    pdf = SunhavenPDF()
    pdf.titulo_header = "REPORTE DE AUDITORIA - RONDINES NOCTURNOS"
    pdf.cover_page("SUPERVISION Y CUIDADO CONTINUO", "Auditoria Operativa y Antifraude", fecha_str)

    # S1 — Cumplimiento + Pie
    pdf.add_page()
    safe_add_section(pdf, "1. CUMPLIMIENTO OPERATIVO", min_space=100)
    pdf.ln(3)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 5, sanitizar_texto(
        "Esquema: 3 rondines obligatorios por noche en 3 bloques horarios (B1: 21-23h, B2: 0-3h, B3: 4-6h). "
        "Verde = cumplimiento >= 90%. Los domingos estan excluidos del calculo de desempeno."), 0, 'J')
    pdf.ln(2)
    datos_tabla = [
        [r['Colaborador'], str(r['Turnos Meta']), str(r['Meta Rondas']),
         str(r['Rondas Real.']), f"{r['% Cumplimiento']:.1f}%"]
        for _, r in df_resumen.iterrows()
    ]
    tabla_centrada(pdf,
        ["Colaborador", "Turnos Meta", "Meta Rondas", "Rondas Real.", "% Cumplimiento"],
        datos_tabla, [60, 28, 28, 28, 38])
    pdf.ln(4)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 5, sanitizar_texto(f"Escaneos QR totales procesados en el periodo: {escaneos_totales}"), 0, 1)
    pdf.cell(0, 5, sanitizar_texto(f"Alertas de velocidad detectadas (posible fraude < 60 s): {alertas_fraude}"), 0, 1)
    pdf.ln(3)
    img_centrada(pdf, p_s1, w=188)

    # S2 — Escaneos por residente
    if p_s2 and os.path.exists(p_s2):
        pdf.add_page()
        safe_add_section(pdf, "2. FRECUENCIA DE VISITAS POR RESIDENTE", min_space=100)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*C_DARK)
        pdf.multi_cell(0, 5, sanitizar_texto(
            "Frecuencia total de escaneos QR por residente en el periodo, ordenados de mayor a menor. "
            "Los residentes con menor cobertura pueden indicar puntos ciegos de supervisión que requieren atención."), 0, 'J')
        pdf.ln(3)
        img_centrada(pdf, p_s2, w=188)

    # S3 — Heatmap bloques horarios
    if p_s3 and os.path.exists(p_s3):
        pdf.add_page()
        safe_add_section(pdf, "3. MAPA DE CALOR — RESIDENTE × BLOQUE HORARIO", min_space=100)
        pdf.ln(3)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*C_DARK)
        pdf.multi_cell(0, 5, sanitizar_texto(
            "Cada celda muestra cuantas veces fue visitado ese residente en ese bloque horario. "
            "Celdas en rojo/amarillo indican bloques con cobertura deficiente (posibles puntos ciegos nocturnos)."), 0, 'J')
        pdf.ln(3)
        img_centrada(pdf, p_s3, w=188)

    # S4 — Heatmap cobertura diaria
    if p_s4 and os.path.exists(p_s4):
        pdf.add_page()
        safe_add_section(pdf, "4. COBERTURA DIARIA POR RESIDENTE", min_space=100)
        pdf.ln(3)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*C_DARK)
        pdf.multi_cell(0, 5, sanitizar_texto(
            "Mapa de cobertura dia a dia. Verde = 3 o mas rondines ese dia. "
            "Rojo = ningun escaneo. Los dias sin color representan dias fuera del rango evaluado."), 0, 'J')
        pdf.ln(3)
        img_centrada(pdf, p_s4, w=188)

    # S5 — Box plot velocidad de escaneo
    if p_s5 and os.path.exists(p_s5):
        pdf.add_page()
        safe_add_section(pdf, "5. ANÁLISIS DE VELOCIDAD DE ESCANEO — DETECCIÓN DE FRAUDE", min_space=100)
        pdf.ln(3)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*C_DARK)
        pdf.multi_cell(0, 5, sanitizar_texto(
            "Distribucion del tiempo transcurrido entre escaneos consecutivos por enfermera. "
            "La linea roja punteada marca el umbral de 60 segundos: cualquier escaneo realizado "
            "en menos tiempo es fisicamente imposible si implica desplazarse a otra habitacion "
            "y se considera un indicador fuerte de registro fraudulento."), 0, 'J')
        pdf.ln(3)
        img_centrada(pdf, p_s5, w=188)

    # S6 — Tabla de evidencia de fraude
    pdf.add_page()
    safe_add_section(pdf, "6. EVIDENCIA DE ALERTAS — REGISTROS CON INTERVALO ANÓMALO", min_space=80)
    pdf.ln(3)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 5, sanitizar_texto(
        "Registro completo de los escaneos que presentaron un intervalo menor a 60 segundos respecto "
        "al escaneo inmediatamente anterior del mismo colaborador. Esta evidencia debe cruzarse con "
        "el sistema de camaras de vigilancia para confirmar o descartar irregularidades."), 0, 'J')
    pdf.ln(3)

    if col_enf and col_ts and not df_ron_raw.empty:
        try:
            df_fr = df_ron_raw.copy()
            df_fr[col_ts] = pd.to_datetime(df_fr[col_ts], dayfirst=True, errors='coerce')
            df_fr = df_fr.sort_values([col_enf, col_ts])
            df_fr['Diff_s'] = df_fr.groupby(col_enf)[col_ts].diff().dt.total_seconds()
            df_fraud = df_fr[df_fr['Diff_s'] < 60].copy()
            if not df_fraud.empty:
                df_fraud['Diff_s'] = df_fraud['Diff_s'].apply(lambda x: f"{x:.0f}s")
                cols_sel    = [col_enf, col_ts] + ([col_res] if col_res else []) + ['Diff_s']
                labels_show = ['Colaborador', 'Fecha / Hora'] + (['Residente Visitado'] if col_res else []) + ['Seg vs Ant.']
                widths_show = [45, 45] + ([60] if col_res else []) + [22]
                datos_fr    = [[sanitizar_texto(str(r[c])[:38]) for c in cols_sel]
                               for _, r in df_fraud.iterrows()]
                tabla_centrada(pdf, labels_show, datos_fr, widths_show)
            else:
                pdf.set_font('Helvetica', 'I', 11)
                pdf.set_text_color(16, 185, 129)
                pdf.cell(0, 8, sanitizar_texto("Sin alertas de fraude en el periodo evaluado.  Auditoria limpia."), 0, 1)
        except Exception as ex:
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_text_color(*C_DARK)
            pdf.cell(0, 8, sanitizar_texto(f"(No se pudo generar la tabla de evidencia: {ex})"), 0, 1)
    else:
        pdf.set_font('Helvetica', 'I', 10)
        pdf.set_text_color(*C_DARK)
        pdf.cell(0, 8, sanitizar_texto("No hay datos de rondines disponibles para el periodo seleccionado."), 0, 1)

    bloque_conclusion(pdf, pdf_dictamen)

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
            creds_dict = json.loads(st.secrets["GOOGLE_JSON"])
            gc = gspread.service_account_from_dict(creds_dict)
        elif os.path.exists(PATH_CREDS):
            gc = gspread.service_account(filename=PATH_CREDS)
        else:
            st.error("No se encontraron credenciales de Google.")
            return None

        sheet_n = gc.open_by_url("https://docs.google.com/spreadsheets/d/10wWKmjsyj501OXaFWs7Rd_XF_2R-H0YzV66B2K6HvPE/edit")
        sheet_v = gc.open_by_url("https://docs.google.com/spreadsheets/d/1C1AVmNXG0ggRekB1HF4_IhX-NGiTkwzgvZn2Z31rCsc/edit")
        sheet_s = gc.open_by_url("https://docs.google.com/spreadsheets/d/1wdP3mbW_k4a90ubPG-ZQy8FvfAZiwKnhPjCj1BZHcBs/edit")

        dfs = {
            "n": pd.DataFrame(sheet_n.get_worksheet(0).get_all_records()),
            "v": pd.DataFrame(sheet_v.get_worksheet(0).get_all_records()),
            "s": pd.DataFrame(sheet_s.get_worksheet(0).get_all_records())
        }
        
        for k in dfs:
            if not dfs[k].empty:
                dfs[k].columns = dfs[k].columns.str.strip().str.replace('\n', ' ')
        return dfs
    except Exception as e:
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
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active
    datos = []
    emp = None
    
    for row in ws.iter_rows(values_only=True):
        row_str = [str(cell) if cell is not None else "" for cell in row]
        
        if any("ID:" in str(c) for c in row_str):
            for i, c in enumerate(row_str):
                if "Nombre:" in str(c):
                    try:
                        emp = " ".join(row_str[i+2].split())  
                    except IndexError:
                        pass
                    break
        
        elif emp and any(":" in str(cell) for cell in row_str):
            for dia, celda in enumerate(row_str, 1):
                celda = str(celda).strip()
                if len(celda) >= 5 and ":" in celda:
                    datos.append({
                        "Checador": emp,
                        "Día": dia,
                        "Entrada": celda[:5],
                        "Salida": celda[-5:] if len(celda) >= 10 else ""
                    })
            emp = None
            
    return pd.DataFrame(datos)

def procesar_super_nomina(df_bio, df_bitacora, df_kaizen, mes_num, anio_num):
    EMPLEADOS_DB_UPPER = {" ".join(k.upper().split()): v for k, v in EMPLEADOS_DB.items()}
    CHECADORES_ESP_SET = {" ".join(c.upper().split()) for c in CHECADORES_ESPECIALES}
    HORA_CORTE_NOCHE   = datetime.strptime("14:00", "%H:%M").time()

    ret_list = []

    if not df_bio.empty:
        for _, row in df_bio.iterrows():
            ch = " ".join(str(row['Checador']).upper().split())
            if ch not in EMPLEADOS_DB_UPPER:
                continue
            nm  = EMPLEADOS_DB_UPPER[ch]


            # Solo enfermeras con turno fijo reciben retardo (sin supervisoras)
            if nm not in ENFERMERAS_RETARDO:
                continue
            if ch in CHECADORES_ESP_SET:
                continue

            ent = row['Entrada']
            try:
                he = datetime.strptime(ent, "%H:%M").time()

                if nm in ENFERMERAS_NOCHE and he < HORA_CORTE_NOCHE:
                    continue

                lim = HORA_ENTRADA_NOCHE if nm in ENFERMERAS_NOCHE else HORA_ENTRADA_DIA

                if he > lim:
                    dt_ent = datetime.combine(datetime.today(), he)
                    dt_lim = datetime.combine(datetime.today(), lim)
                    min_tarde = int((dt_ent - dt_lim).total_seconds() / 60)
                    turno_lbl = "turno noche" if nm in ENFERMERAS_NOCHE else "turno día"
                    ret_list.append({
                        "FECHA": f"{anio_num}-{mes_num:02d}-{int(row['Día']):02d}",
                        "EMPLEADO": nm,
                        "INCIDENCIA": "Retardo Biométrico",
                        "OBSERVACION": f"Entró a las {ent} (Cubrió {turno_lbl})"
                    })
            except Exception:
                pass

            # Salida Anticipada (solo turno día)
            if nm not in ENFERMERAS_NOCHE:
                sal = str(row.get('Salida', '')).strip()
                if sal and len(sal) == 5 and ':' in sal:
                    try:
                        hs = datetime.strptime(sal, "%H:%M").time()
                        if hs < HORA_SALIDA_DIA:
                            ret_list.append({
                                "FECHA": f"{anio_num}-{mes_num:02d}-{int(row['Día']):02d}",
                                "EMPLEADO": nm,
                                "INCIDENCIA": "Salida Anticipada",
                                "OBSERVACION": f"Salió a las {sal} (Cubrió turno día)"
                            })
                    except Exception:
                        pass

    df_ret = pd.DataFrame(ret_list)

    COL_NOMBRE    = 'Colaborador'
    COL_PROPUESTA = 'Propuesta de mejora'
    COL_AREA      = 'Area de la propuesta'

    part, nopart, props = [], [], []
    stats_k = {'curr_si': 0, 'curr_no': 0, 'prev_si': 0, 'prev_no': 0, 'lista_no': []}

    if not df_kaizen.empty:
        df_kaizen['Marca temporal'] = pd.to_datetime(df_kaizen['Marca temporal'], dayfirst=True, errors='coerce')

        col_area_real = COL_AREA
        for c in df_kaizen.columns:
            if 'rea' in c.lower() and 'propuesta' in c.lower():
                col_area_real = c
                break

        df_k_curr = df_kaizen[
            (df_kaizen['Marca temporal'].dt.month == mes_num) &
            (df_kaizen['Marca temporal'].dt.year  == anio_num)
        ]
        part   = df_k_curr[COL_NOMBRE].str.strip().unique().tolist() if COL_NOMBRE in df_k_curr.columns else []
        nopart = [e for e in ENFERMERAS_LISTA if e not in part and e not in EXCEPCIONES_KAIZEN]

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
            'fecha':     r['Marca temporal'].strftime("%d/%m/%Y") if pd.notna(r['Marca temporal']) else "",
            'area':      str(r.get(col_area_real, '')),
            'propuesta': str(r.get(COL_PROPUESTA, ''))
        } for _, r in df_k_curr.iterrows()]

    df_admin = pd.DataFrame([{
        "FECHA": f"{anio_num}-{mes_num:02d}-28",
        "EMPLEADO": e,
        "INCIDENCIA": "Falla Admin/Kaizen",
        "OBSERVACION": "No presento propuesta de mejora Kaizen"
    } for e in nopart])

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

    df_todas = pd.concat([df_ret, df_bit, df_admin], ignore_index=True)

    nomina = []
    for emp in sorted(list(set(EMPLEADOS_DB.values()))):
        df_e   = df_todas[df_todas['EMPLEADO'] == emp]
        c_ret  = len(df_e[df_e['INCIDENCIA'] == 'Retardo Biométrico'])
        c_sal  = len(df_e[df_e['INCIDENCIA'] == 'Salida Anticipada'])
        f_kz   = not df_e[df_e['INCIDENCIA'] == 'Falla Admin/Kaizen'].empty
        f_gr   = len(df_e[df_e['INCIDENCIA'].str.contains('Grave', case=False, na=False)])
        f_otras = len(df_e) - c_ret - c_sal - (1 if f_kz else 0)

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
# 5. APLICACIÓN PRINCIPAL (ENRUTADOR ENTERPRISE)
# ==========================================
def main():
    with st.sidebar:
        st.markdown("<h2 style='text-align:center; color:#1E293B; margin-bottom: 2rem;'>SUNHAVEN<br><span style='font-size: 1rem; font-weight:400; color:#64748B;'>Operations Platform</span></h2>", unsafe_allow_html=True)
        
        modulo_activo = option_menu(
            menu_title=None,
            options=["Dashboard de Operaciones", "Gestión de Nómina", "Turno Nocturno"],
            icons=["clipboard-data", "wallet2", "moon-stars"],
            menu_icon="cast", default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#D35400", "font-size": "1.2rem"},
                "nav-link": {"font-size": "0.95rem", "text-align": "left", "margin":"0px", "font-family": "Inter", "color": "#475569", "font-weight": "600", "border-radius": "8px"},
                "nav-link-selected": {"background-color": "#ffffff", "color": "#0F172A", "box-shadow": "0 1px 3px rgba(0,0,0,0.1)"},
            }
        )
        
        st.markdown("<hr style='margin: 1.5rem 0; border-color: #E2E8F0;'>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 0.8rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;'>Filtros Globales</p>", unsafe_allow_html=True)
        
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
            file_asis = st.file_uploader("Archivo Biométrico (.xlsx, .csv)", type=['xlsx', 'csv'])

            # ── Auto-detect mes desde nombre del archivo ──────────────────
            if file_asis:
                _MESES_MAP = {
                    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
                    "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12,
                    "ene":1,"feb":2,"mar":3,"abr":4,"jun":6,"jul":7,"ago":8,
                    "sep":9,"oct":10,"nov":11,"dic":12,
                }
                _fn = file_asis.name.lower().replace('-','').replace('_','').replace(' ','')
                for _nm, _num in sorted(_MESES_MAP.items(), key=lambda x: -len(x[0])):
                    if _nm in _fn:
                        mes_eval = _num
                        break
            # ─────────────────────────────────────────────────────────────
            
        st.markdown("<hr style='margin: 1.5rem 0; border-color: #E2E8F0;'>", unsafe_allow_html=True)
        if st.button("🔄 Sincronizar Datos DB", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ---------------------------------------------------------
    # MÓDULO 1: DASHBOARD OPERATIVO
    # ---------------------------------------------------------
    if modulo_activo == "Dashboard de Operaciones":
        st.title("Monitoreo e Inteligencia Operativa")
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
            df_c = pd.DataFrame.from_dict({"Uniforme Cocina": df_serv[c_uni].mean(), "Limpieza de Cocina": df_serv[c_bas].mean(), "Separación de Ropa": df_serv[c_lav_r].mean(), "Consumo de Detergente": df_serv[c_lav_j].mean(), "Limpieza de Zonas": df_serv[c_lim].mean(), "Orden en Roperos": df_rop[c_5s].mean(), "Tendido Camas": df_rop[c_cam].mean(), "Rondas Nocturnas": v_noc}, orient='index', columns=['V']).sort_values('V', ascending=True).reset_index()

            personal_diurno = set(df_rop[col_enf].dropna().unique()) - set(ENFERMERAS_NOCHE)
            ranking_data = [{"Colaborador": e, "Turno": "Nocturno", "Puntaje (%)": round(p_noc.get(e,0),1)} for e in ENFERMERAS_NOCHE if p_noc.get(e) is not None] + [{"Colaborador": e, "Turno": "Vespertino", "Puntaje (%)": round(df_rop[df_rop[col_enf]==e]['Promedio'].mean(),1)} for e in personal_diurno if pd.notna(df_rop[df_rop[col_enf]==e]['Promedio'].mean())]
            df_ranking = pd.DataFrame(ranking_data)
            if not df_ranking.empty: df_ranking = df_ranking.sort_values("Puntaje (%)", ascending=False).reset_index(drop=True)

        except Exception as e:
            st.error(f"Error procesando operaciones: {e}")

        html_dictamen, pdf_dictamen = generar_dictamen_operativo(ico, df_a, df_c)

        # Enterprise Layout
        top_col1, top_col2 = st.columns([3, 1])
        with top_col1:
            st.markdown(f"<div class='dictamen-box'><h4 class='dictamen-title'>Insights Ejecutivos</h4><p class='dictamen-text'>{html_dictamen}</p></div>", unsafe_allow_html=True)
            if kpi:
                kpi_cols = st.columns(len(kpi))
                for i, (a, v) in enumerate(kpi.items()):
                    with kpi_cols[i]: render_kpi_card(a, v)
        with top_col2:
            fig_gauge = go.Figure(go.Indicator(mode="gauge+number", value=ico, number={'suffix': "%", 'font': {'size': 36, 'color': '#0F172A', 'family': 'Inter'}}, title={'text': "ICO MAESTRO", 'font': {'size': 14, 'color': '#64748B', 'family': 'Inter'}}, gauge={'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#CBD5E1"}, 'bar': {'color': HEX_GREEN if ico>=90 else HEX_RED}, 'bgcolor': "white", 'borderwidth': 0, 'steps': [{'range': [0, 90], 'color': '#FEE2E2'}, {'range': [90, 100], 'color': '#D1FAE5'}]}))
            fig_gauge.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=230, paper_bgcolor='rgba(0,0,0,0)', font_family="Inter")
            st.markdown("<div class='premium-card' style='height: 90%; display:flex; align-items:center;'>", unsafe_allow_html=True)
            st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})
            st.markdown("</div>", unsafe_allow_html=True)

        tabs_op = st.tabs(["Tablero Analítico", "Tendencias Base", "Evaluación RRHH", "Auditoría Legal", "Raw Data"])
        
        with tabs_op[0]:
            if st.button("📄 Exportar Reporte Ejecutivo (PDF)", type="primary"):
                pdf_b = generar_pdf_dashboard_op(ico, "ESTABLE" if ico >= 90 else "ATENCIÓN REQUERIDA", df_a, df_c, df_plot, agrupacion_temporal, f"{fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}", pdf_dictamen)
                st.download_button("Descargar Documento Operaciones", data=pdf_b, file_name="Reporte_Operaciones.pdf", mime="application/pdf")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("<div class='premium-card'><h3 class='section-title'>Análisis de Pareto Operativo</h3>", unsafe_allow_html=True)
                if not df_a.empty:
                    fig = px.bar(df_a, x='index', y='V', text_auto='.1f', color_discrete_sequence=[HEX_NAVY])
                    fig.add_hline(y=90, line_dash="dash", line_color=HEX_RED, annotation_text="Meta 90%")
                    st.plotly_chart(apply_plotly_theme(fig), use_container_width=True, config={'displayModeBar': False})
                st.markdown("</div>", unsafe_allow_html=True)
            with c2:
                st.markdown("<div class='premium-card'><h3 class='section-title'>Análisis de Causa Raíz (Ishikawa)</h3>", unsafe_allow_html=True)
                if not df_c.empty:
                    fig_c = px.bar(df_c, x='V', y='index', orientation='h', text_auto='.1f', color_discrete_sequence=[HEX_SUN])
                    fig_c.add_vline(x=90, line_dash="dash", line_color=HEX_NAVY)
                    st.plotly_chart(apply_plotly_theme(fig_c), use_container_width=True, config={'displayModeBar': False})
                st.markdown("</div>", unsafe_allow_html=True)

        with tabs_op[1]:
            st.markdown("<div class='premium-card'><h3 class='section-title'>Tendencias Históricas</h3>", unsafe_allow_html=True)
            if not df_plot.empty:
                fig_evol = px.line(df_plot, labels={"value": "Cumplimiento (%)", "index": "Periodo", "variable": "Área Operativa"}, markers=True)
                fig_evol.update_traces(line_shape='spline')
                fig_evol.add_hline(y=90, line_dash="dot", line_color=HEX_RED, annotation_text="Línea Base 90%")
                st.plotly_chart(apply_plotly_theme(fig_evol), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with tabs_op[2]:
            st.markdown("<div class='premium-card'><h3 class='section-title'>Rendimiento Individual Consolidado</h3>", unsafe_allow_html=True)
            if not df_ranking.empty: st.dataframe(df_ranking, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with tabs_op[3]:
            cats = {
                "REGULACIÓN SANITARIA Y OPERATIVA - COPRISJAL/SSA": ["[CRÍTICO - Anual] Aviso de Funcionamiento: Verificar documento vigente y exhibido.", "[CRÍTICO - Anual] Responsable Sanitario: Validar aviso y nombramiento registrado.", "[CRÍTICO - Diario] Medicamentos controlados: Verificar resguardo y control foliado.", "[ALTO - Mensual] Accesibilidad NOM-031: Verificar rampas y barandales.", "[CRÍTICO - Mensual] Expedientes clínicos: Validar integración y resguardo.", "[CRÍTICO - Semanal] Manejo RPBI: Verificar contenedores y bolsas.", "[ALTO - Diario] Higiene alimentaria: Control de temperaturas y limpieza en cocina."],
                "SEGURIDAD Y SALUD LABORAL - STPS": ["[ALTO - Anual] RIT: Verificar Reglamento Interior de Trabajo firmado.", "[ALTO - Anual] NOM-035: Aplicar guía preventiva de riesgos psicosociales.", "[ALTO - Trimestral] Comisión Mixta: Validar actas y recorridos de seguridad.", "[ALTO - Semestral] Ergonomía (Movilización pacientes): Verificar capacitación y DC-3."],
                "PROTECCIÓN CIVIL Y ECOLOGÍA MUNICIPAL": ["[CRÍTICO - Anual] Programa Interno PIPC: Validar autorización vigente.", "[CRÍTICO - Anual] Responsabilidad Civil: Verificar póliza de seguro vigente.", "[CRÍTICO - Anual] Dictamen estructural: Validar dictamen DRO.", "[CRÍTICO - Mensual] Extintores: Revisar vigencia, señalización y recarga.", "[CRÍTICO - Mensual] Detectores de humo: Validar funcionamiento.", "[ALTO - Mensual] Evacuación: Verificar rutas, luces y señalética.", "[ALTO - Anual] Brigadas: Validar constancias de capacitación (DC-3).", "[CRÍTICO - Semestral] Simulacros: Revisar bitácoras y formatos de evacuación."],
                "CUMPLIMIENTO LEGAL Y PRIVACIDAD": ["[ALTO - Permanente] Aviso de privacidad INAI: Verificar exhibición y anexos.", "[CRÍTICO - Permanente] Datos sensibles: Confirmar consentimientos en expedientes.", "[ALTO - Permanente] Contratos de servicios: Verificar contratos firmados y vigentes.", "[ALTO - Anual] Contrato adhesión PROFECO: Confirmar registro vigente."]
            }
            if 'checks' not in st.session_state: st.session_state.checks = {i: False for sub in cats.values() for i in sub}
            c_l1, c_l2 = st.columns([0.7, 0.3])
            with c_l1:
                for cat, items in cats.items():
                    with st.expander(cat, expanded=True):
                        for item in items: st.session_state.checks[item] = st.checkbox(item, value=st.session_state.checks[item], key=item)
            pct = (sum(st.session_state.checks.values()) / len(st.session_state.checks)) * 100
            with c_l2:
                st.markdown(f"<div class='premium-card'><h3 class='section-title'>Índice de Protección: {int(pct)}%</h3>", unsafe_allow_html=True)
                st.progress(pct / 100)
                if st.button("Generar Reporte Legal", type="primary"): st.session_state['pl'] = generar_pdf_legal_bytes(cats, st.session_state.checks, pct)
                if 'pl' in st.session_state: st.download_button("Descargar Auditoría PDF", data=st.session_state['pl'], file_name=f"Legal_{datetime.now().strftime('%d%m%Y')}.pdf", mime="application/pdf")
                st.markdown("</div>", unsafe_allow_html=True)

        with tabs_op[4]:
            st.info("Visualización de tuberías de ingesta bruta conectadas a Google Sheets.")
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
        tabs_nom = st.tabs(["Ejecución Financiera", "Bitácora Digital", "Data Cruda"])

        with tabs_nom[1]:
            st.markdown("<div class='premium-card'><h3 class='section-title'>Nueva Incidencia Operativa</h3>", unsafe_allow_html=True)
            with st.form("form_incidencia"):
                c_f1, c_f2, c_f3 = st.columns(3)
                with c_f1: f_fecha = st.date_input("Fecha")
                with c_f2: f_emp = st.selectbox("Colaborador", sorted(list(set(EMPLEADOS_DB.values()))))
                with c_f3: f_inc = st.selectbox("Incidencia", TIPO_INCIDENCIAS)
                f_obs = st.text_input("Observaciones")
                if st.form_submit_button("Guardar en Bitácora"):
                    guardar_incidencia(f_fecha.strftime('%Y-%m-%d'), f_emp, f_inc, f_obs)
                    st.rerun()
            st.markdown("</div><div class='premium-card'><h3 class='section-title'>Historial de Bitácora Digital</h3>", unsafe_allow_html=True)
            st.dataframe(df_bitacora, use_container_width=True)
            if not df_bitacora.empty:
                col_b1, col_b2 = st.columns([1,4])
                with col_b1:
                    b_idx = st.number_input("ID a borrar", 0, len(df_bitacora)-1, 0)
                    if st.button("Eliminar Registro Permanentemente"): borrar_incidencia(b_idx); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with tabs_nom[0]:
            if file_asis:
                _MESES_LABELS = ["","Enero","Febrero","Marzo","Abril","Mayo","Junio",
                                 "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
                _mes_nombre = _MESES_LABELS[mes_eval] if 1 <= mes_eval <= 12 else str(mes_eval)
                st.markdown(
                    f"<div style='background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;"
                    f"padding:10px 14px;margin-bottom:10px;font-size:0.9rem;color:#166534;'>"
                    f"<strong>Periodo detectado:</strong> {_mes_nombre} {anio_eval} &nbsp;&middot;&nbsp; "
                    f"<span style='color:#6B7280;'>{file_asis.name}</span></div>",
                    unsafe_allow_html=True
                )
                if st.button("Ejecutar Algoritmo de Nómina y Bonos", type="primary"):
                    with st.spinner("Procesando..."):
                        st.session_state['nom'] = procesar_super_nomina(limpiar_biometrico(file_asis.read()), df_bitacora, fetch_kaizen_data(), mes_eval, anio_eval)
            
            if 'nom' in st.session_state:
                df_n, df_i, df_r, s_k, p_k, df_bio_nom = st.session_state['nom']
                m_str = f"{mes_eval:02d}/{anio_eval}"
                html_dictamen, pdf_dictamen = generar_dictamen_nomina(s_k, df_r)

                st.markdown(f"""
                <div class='premium-card' style='background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); color: white; border:none;'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <div style='width: 65%;'>
                            <p style='color:#94A3B8; font-size:12px; font-weight:800; text-transform:uppercase; margin:0;'>Insights Analíticos de Recursos Humanos</p>
                            <div style='margin-top: 8px; font-size: 0.95rem; line-height: 1.5; color: #E2E8F0;'>{html_dictamen}</div>
                        </div>
                        <div style='text-align: right;'>
                            <p style='color:#94A3B8; font-size:12px; font-weight:800; text-transform:uppercase; margin:0;'>Gran Total a Dispersar</p>
                            <h1 style='color:#10B981; font-size:48px; margin:0;'>${df_n['TOTAL A PAGAR'].sum():,}</h1>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("📄 Exportar Reporte de Nómina Oficial (PDF Unificado)"):
                    pdf_b = generar_pdf_nomina(df_n, df_i, df_r, s_k, p_k, df_bio_nom, mes_eval, anio_eval, m_str, pdf_dictamen)
                    st.download_button("Descargar Nómina Oficial", data=pdf_b, file_name=f"Nomina_{m_str.replace('/','_')}.pdf", mime="application/pdf")
                
                c_nom1, c_nom2 = st.columns([1.5, 1])
                with c_nom1:
                    st.markdown("<div class='premium-card'><h3 class='section-title'>Matriz de Dispersión Financiera</h3>", unsafe_allow_html=True)
                    st.dataframe(df_n, use_container_width=True, hide_index=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with c_nom2:
                    st.markdown("<div class='premium-card'><h3 class='section-title'>Métricas Clave</h3>", unsafe_allow_html=True)
                    fig_k = go.Figure(data=[go.Pie(labels=['Entregaron', 'Omitieron'], values=[s_k['curr_si'], s_k['curr_no']], hole=.5, marker_colors=[HEX_NAVY, HEX_SUN])])
                    fig_k.update_layout(title_text="Adopción Kaizen (Mes Actual)", showlegend=True, margin=dict(t=30, b=10, l=10, r=10), height=250)
                    st.plotly_chart(fig_k, use_container_width=True, config={'displayModeBar': False})
                    
                    if not df_r.empty:
                        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                        ret_counts = df_r['EMPLEADO'].value_counts().head(5).reset_index()
                        ret_counts.columns = ['Empleado', 'Retardos']
                        fig_r = px.bar(ret_counts, y='Empleado', x='Retardos', orientation='h', color_discrete_sequence=[HEX_RED], title="Top 5 Reincidentes (Biométrico)")
                        fig_r.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=30, b=10, l=10, r=10), height=250)
                        st.plotly_chart(fig_r, use_container_width=True, config={'displayModeBar': False})
                    st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<div class='premium-card'><h3 class='section-title'>Desglose Histórico e Individual de Incidencias</h3>", unsafe_allow_html=True)
                for emp in sorted(df_n['COLABORADOR'].unique()):
                    df_emp_inc = df_i[df_i['EMPLEADO'] == emp]
                    if not df_emp_inc.empty:
                        with st.expander(f"Expediente de: {emp}"):
                            st.dataframe(df_emp_inc[['FECHA', 'INCIDENCIA', 'OBSERVACION']], use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)

        with tabs_nom[2]:
            if 'nom' in st.session_state:
                sub1, sub2 = st.tabs(["Retardos Biométricos", "Propuestas Kaizen"])
                with sub1: st.dataframe(st.session_state['nom'][2], use_container_width=True)
                with sub2: st.dataframe(fetch_kaizen_data(), use_container_width=True)

    # ---------------------------------------------------------
    # MÓDULO 3: TURNO NOCTURNO
    # ---------------------------------------------------------
    elif modulo_activo == "Turno Nocturno":
        st.title("Auditoría de Turno Nocturno")
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

        html_dictamen, pdf_dictamen = generar_dictamen_rondines(alertas, df_resumen)
        
        t_col1, t_col2, t_col3 = st.columns([2,1,1])
        with t_col1: st.markdown(f"<div class='dictamen-box' style='border-left-color:{HEX_RED if alertas>0 else HEX_GREEN};'><h4 class='dictamen-title' style='color:{HEX_RED if alertas>0 else HEX_GREEN};'>Auditoría de Integridad</h4><p class='dictamen-text'>{html_dictamen}</p></div>", unsafe_allow_html=True)
        with t_col2: render_kpi_card("Cobertura Global", v_noc)
        with t_col3: render_kpi_card("Alertas de Fraude", alertas, threshold=0.1, suffix="") 

        tabs_noc = st.tabs(["Control de Rondas e Integridad", "Log Forense (Trazabilidad)"])
        with tabs_noc[0]:
            if st.button("📄 Exportar Reporte de Rondines (PDF)", type="primary"):
                pdf_b = generar_pdf_rondines(df_resumen, df_ron_sort, escaneos, alertas, f"{fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}", pdf_dictamen)
                st.download_button("Descargar Archivo Oficial", data=pdf_b, file_name="Reporte_Rondines.pdf", mime="application/pdf")
            
            c_r1, c_r2 = st.columns([1, 1.5])
            with c_r1:
                st.markdown("<div class='premium-card'><h3 class='section-title'>Matriz de Cumplimiento</h3>", unsafe_allow_html=True)
                st.dataframe(df_resumen, use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with c_r2:
                st.markdown("<div class='premium-card'><h3 class='section-title'>Análisis de Puntos Ciegos (Heatmap)</h3>", unsafe_allow_html=True)
                if not df_ron.empty:
                    _col_r = next((c for c in ['Residente Visitado','Nombre del Residente','Residente','Paciente'] if c in df_ron.columns), None)
                    if _col_r and 'Bloque' in df_ron.columns:
                        heat_data = df_ron[df_ron['Bloque'].notnull()].pivot_table(index=_col_r, columns='Bloque', aggfunc='size', fill_value=0)
                        fig_heat = px.imshow(heat_data, color_continuous_scale='RdYlGn', text_auto=True)
                        fig_heat.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
                        st.plotly_chart(apply_plotly_theme(fig_heat), use_container_width=True, config={'displayModeBar': False})
                    else:
                        st.info('El heatmap requiere la columna Residente Visitado en los datos.')
                st.markdown("</div>", unsafe_allow_html=True)

        with tabs_noc[1]:
            st.markdown("<div class='premium-card'><h3 class='section-title'>Trazabilidad en Tiempo Real</h3>", unsafe_allow_html=True)
            st.dataframe(df_ron_sort[['Marca temporal', 'Enfermera', 'Diff']].sort_values(by="Marca temporal", ascending=False), use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()