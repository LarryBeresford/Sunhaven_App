import os
import datetime
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF

# --- COLORES PARA LA TERMINAL ---
class CTerm:
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

# --- CONFIGURACION DINÁMICA DE RUTAS ---
# Sube un nivel desde /bots hasta la raíz de SunHaven
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ARCHIVO_CREDENCIALES = os.path.join(BASE_DIR, 'config', 'credenciales.json')
CARPETA_OUTPUTS = os.path.join(BASE_DIR, 'data', 'outputs')
CARPETA_TEMP = os.path.join(BASE_DIR, 'tools', 'temp_images')

# --- IDs DE GOOGLE SHEETS ---
ID_ROPEROS = "1C1AVmNXG0ggRekB1HF4_IhX-NGiTkwzgvZn2Z31rCsc"
ID_SERVICIOS = "1wdP3mbW_k4a90ubPG-ZQy8FvfAZiwKnhPjCj1BZHcBs"

# --- PALETA EJECUTIVA SUNHAVEN ---
C_NAVY = (31, 58, 82)
C_SUN = (211, 84, 0)
C_DARK = (44, 62, 80)
C_LIGHT = (245, 247, 248)
HEX_NAVY = '#1F3A52'
HEX_SUN = '#D35400'
HEX_DARK = '#2C3E50'
HEX_RED = '#E74C3C'

class OperacionesPDF(FPDF):
    def header(self):
        if self.page_no() == 1: return
        self.set_fill_color(*C_NAVY)
        self.rect(0, 0, 210, 26, 'F')
        self.set_fill_color(*C_SUN)
        self.rect(0, 26, 210, 1.5, 'F')
        self.set_y(9)
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, 'REPORTE DE CALIDAD Y OPERACIONES (OEE)', 0, 1, 'C')
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

    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(*C_NAVY)
        self.cell(0, 8, title.upper(), 0, 1, 'L')
        self.set_draw_color(*C_SUN)
        self.set_line_width(0.5)
        self.line(self.get_x(), self.get_y(), 200, self.get_y())
        self.ln(4)

    def cover_page(self, mes_nombre, anio):
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
        self.cell(0, 12, 'OPERACIONES (CALIDAD E HIGIENE)', 0, 1, 'C')
        self.set_y(220)
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(*C_NAVY)
        self.cell(0, 8, f'PERIODO EVALUADO: {mes_nombre.upper()} {anio}', 0, 1, 'C')
        self.set_y(260)
        self.set_font('Helvetica', '', 11)
        self.set_text_color(*C_DARK)
        self.cell(0, 6, 'Elaborado por:', 0, 1, 'C')
        self.set_font('Helvetica', 'B', 11)
        self.cell(0, 6, 'Ing. Larry Beresford', 0, 1, 'C')

def generar_reporte():
    print(f"\n{CTerm.CYAN}{CTerm.BOLD}============================================================{CTerm.END}")
    print(f"{CTerm.CYAN}{CTerm.BOLD}   SISTEMA DE OPERACIONES - CÁLCULO DE OEE Y CAUSA RAÍZ{CTerm.END}")
    print(f"{CTerm.CYAN}{CTerm.BOLD}============================================================{CTerm.END}\n")
    
    # 1. PEDIR FECHA
    try:
        mes_actual = datetime.date.today().month
        anio_actual = datetime.date.today().year
        entrada_mes = input(f"{CTerm.YELLOW}Ingrese el MES a evaluar (1-12) [Enter para {mes_actual}]: {CTerm.END}").strip()
        mes = int(entrada_mes) if entrada_mes else mes_actual
        entrada_anio = input(f"{CTerm.YELLOW}Ingrese el AÑO (ej. 2026) [Enter para {anio_actual}]: {CTerm.END}").strip()
        anio = int(entrada_anio) if entrada_anio else anio_actual
    except ValueError:
        print(f"\n{CTerm.RED}[ERROR] Ingresa números válidos.{CTerm.END}")
        return

    meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    nombre_mes = meses_nombres[mes - 1]

    # 2. CONECTAR Y EXTRAER
    print(f"\n{CTerm.BLUE}[1/4] Sincronizando auditorías desde Google Sheets...{CTerm.END}")
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(ARCHIVO_CREDENCIALES, scope)
    cliente = gspread.authorize(creds)
    
    df_rop = pd.DataFrame(cliente.open_by_key(ID_ROPEROS).sheet1.get_all_records())
    df_serv = pd.DataFrame(cliente.open_by_key(ID_SERVICIOS).sheet1.get_all_records())
    
    df_rop.columns = df_rop.columns.str.strip().str.replace('\n', ' ')
    df_serv.columns = df_serv.columns.str.strip().str.replace('\n', ' ')
    
    print(f"{CTerm.BLUE}[2/4] Procesando Motor de Productividad (OEE)...{CTerm.END}")
    os.makedirs(CARPETA_TEMP, exist_ok=True)
    
    # --- PROCESAMIENTO ROPEROS ---
    col_5s = [c for c in df_rop.columns if "Orden" in c][0]
    col_camas = [c for c in df_rop.columns if "Tendido" in c][0]
    col_enf = [c for c in df_rop.columns if "enfermera" in c.lower()][0]
    
    df_rop[col_5s] = pd.to_numeric(df_rop[col_5s], errors='coerce') * 10
    df_rop[col_camas] = pd.to_numeric(df_rop[col_camas], errors='coerce') * 10
    df_rop['Promedio_Total'] = (df_rop[col_5s] + df_rop[col_camas]) / 2
    
    # --- PROCESAMIENTO SERVICIOS ---
    c_uni = [c for c in df_serv.columns if "uniforme" in c.lower()][0]
    c_bas = [c for c in df_serv.columns if "basura" in c.lower()][0]
    c_rop = [c for c in df_serv.columns if "ropa sucia" in c.lower()][0]
    c_jab = [c for c in df_serv.columns if "jabón" in c.lower() or "jabon" in c.lower()][0]
    c_lim = [c for c in df_serv.columns if "zonas asignadas" in c.lower()][0]

    for c in [c_uni, c_bas, c_rop, c_jab, c_lim]:
        df_serv[c] = pd.to_numeric(df_serv[c], errors='coerce') * 10

    # --- LÓGICA DEL OEE ---
    kpis_areas = {
        'Cocina': df_serv[[c_uni, c_bas]].mean().mean(),
        'Lavandería': df_serv[[c_rop, c_jab]].mean().mean(),
        'Limpieza General': df_serv[c_lim].mean(),
        'Roperos (Habitaciones)': df_rop['Promedio_Total'].mean()
    }
    kpis_areas_sorted = dict(sorted(kpis_areas.items(), key=lambda item: item[1]))
    oee_global = sum(kpis_areas.values()) / len(kpis_areas)

    metricas_detalle = {
        '5S (Orden Roperos)': df_rop[col_5s].mean(),
        'Estética (Tendido Camas)': df_rop[col_camas].mean(),
        'Uniforme (Cocina)': df_serv[c_uni].mean(),
        'Manejo Basura (Cocina)': df_serv[c_bas].mean(),
        'Separación (Lavandería)': df_serv[c_rop].mean(),
        'Dosificación Jabón (Lavandería)': df_serv[c_jab].mean(),
        'Limpieza Zonas (Intendencia)': df_serv[c_lim].mean()
    }
    metricas_detalle_sorted = dict(sorted(metricas_detalle.items(), key=lambda item: item[1]))
    ranking_enf = df_rop.groupby(col_enf)['Promedio_Total'].mean().sort_values(ascending=True)
    
    print(f"{CTerm.BLUE}[3/4] Generando Gráficos Top-Down...{CTerm.END}")
    
    ruta_pareto_areas = os.path.join(CARPETA_TEMP, 'pareto_areas.png')
    ruta_pareto_causa = os.path.join(CARPETA_TEMP, 'pareto_causa_raiz.png')
    ruta_ranking = os.path.join(CARPETA_TEMP, 'ranking_enfermeras.png')

    plt.figure(figsize=(9, 4.5))
    colores_areas = [HEX_RED if v < 90 else HEX_NAVY for v in kpis_areas_sorted.values()]
    barras_areas = plt.bar(list(kpis_areas_sorted.keys()), list(kpis_areas_sorted.values()), color=colores_areas)
    plt.axhline(y=90, color=HEX_SUN, linestyle='--', label='Meta (90%)')
    plt.title('Rendimiento por Área Operativa (Buscando Cuellos de Botella)', fontweight='bold', color=HEX_DARK)
    plt.ylim(0, 110)
    for barra in barras_areas:
        plt.text(barra.get_x() + barra.get_width()/2, barra.get_height() + 2, 
                 f'{barra.get_height():.1f}%', ha='center', fontsize=10, fontweight='bold', color=HEX_NAVY)
    plt.legend()
    plt.tight_layout()
    plt.savefig(ruta_pareto_areas, dpi=300)
    plt.close()

    plt.figure(figsize=(9, 4.5))
    nombres_crit = list(metricas_detalle_sorted.keys())
    valores_crit = list(metricas_detalle_sorted.values())
    colores_crit = [HEX_RED if v < 90 else HEX_DARK for v in valores_crit]
    barras_det = plt.barh(nombres_crit, valores_crit, color=colores_crit)
    plt.axvline(x=90, color=HEX_SUN, linestyle='--')
    plt.title('Análisis de Causa Raíz por Criterio Evaluado', fontweight='bold', color=HEX_NAVY)
    plt.xlim(0, 110)
    for barra in barras_det:
        plt.text(barra.get_width() + 2, barra.get_y() + barra.get_height()/2, 
                 f'{barra.get_width():.1f}%', va='center', fontsize=9, fontweight='bold')
    plt.tight_layout()
    plt.savefig(ruta_pareto_causa, dpi=300)
    plt.close()

    plt.figure(figsize=(9, 4))
    barras_enf = plt.barh(ranking_enf.index, ranking_enf.values, color=HEX_NAVY)
    plt.axvline(x=90, color=HEX_SUN, linestyle='--')
    plt.title('Ranking de Desempeño por Enfermera (%)', fontweight='bold', color=HEX_DARK)
    plt.xlim(0, 110)
    for barra in barras_enf:
        plt.text(barra.get_width() + 1, barra.get_y() + barra.get_height()/2, 
                 f'{barra.get_width():.1f}%', va='center', fontsize=9, fontweight='bold', color=HEX_NAVY)
    plt.tight_layout()
    plt.savefig(ruta_ranking, dpi=300)
    plt.close()

    # --- ENSAMBLAJE DEL PDF ---
    print(f"{CTerm.BLUE}[4/4] Ensamblando PDF (Estructura de Embudo)...{CTerm.END}")
    nombre_carpeta_mes = f"{mes:02d}_{nombre_mes}_{anio}"  
    ruta_carpeta_mes = os.path.join(CARPETA_OUTPUTS, nombre_carpeta_mes)
    os.makedirs(ruta_carpeta_mes, exist_ok=True)
    
    pdf = OperacionesPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.cover_page(nombre_mes, anio)
    
    pdf.add_page()
    pdf.chapter_title("1. DIAGNÓSTICO GLOBAL: OEE OPERATIVO")
    pdf.set_fill_color(*C_NAVY)
    pdf.rect(10, pdf.get_y(), 190, 25, 'F')
    pdf.set_y(pdf.get_y() + 5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, "EFECTIVIDAD GLOBAL DE OPERACIONES (OEE):", 0, 1, 'C')
    
    color_oee = (39, 174, 96) if oee_global >= 90 else (231, 76, 60)
    pdf.set_text_color(*color_oee)
    pdf.set_font('Helvetica', 'B', 22)
    pdf.cell(0, 8, f"{oee_global:.1f}%", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.chapter_title("2. IMPACTO POR ÁREA (MAYOR ÁREA DE OPORTUNIDAD)")
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 6, "El siguiente gráfico muestra el desempeño general de cada área, ordenado del nivel más crítico (menor cumplimiento) al de mayor excelencia, para identificar qué sector reduce el OEE general.")
    pdf.image(ruta_pareto_areas, x=10, w=190)

    pdf.add_page()
    pdf.chapter_title("3. ANÁLISIS DE CAUSA RAÍZ (CRITERIOS ESPECÍFICOS)")
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 6, "Desglose a nivel operativo. Muestra exactamente la desviación en los procesos evaluados. La métrica en la parte superior del gráfico indica la causa raíz principal que requiere acción preventiva/correctiva inmediata.")
    pdf.image(ruta_pareto_causa, x=10, w=190)
    
    peor_criterio = list(metricas_detalle_sorted.keys())[0]
    peor_valor_crit = list(metricas_detalle_sorted.values())[0]
    
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*C_SUN)
    pdf.cell(0, 8, "DICTAMEN DE CAUSA RAÍZ:", 0, 1)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 6, f"El factor que más está afectando la operación es: '{peor_criterio}' ({peor_valor_crit:.1f}%). Las capacitaciones de esta semana deben centrarse obligatoriamente en corregir esta métrica específica.")

    pdf.add_page()
    pdf.chapter_title("4. FACTOR HUMANO: DESEMPEÑO INDIVIDUAL")
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 6, "Rendimiento promedio de 5S y Calidad por cada elemento de enfermería/staff. Permite identificar necesidades de retroalimentación o reconocimiento.")
    pdf.image(ruta_ranking, x=10, w=190)

    nombre_pdf = f"Reporte_OEE_Operaciones_{mes:02d}_{anio}.pdf"
    ruta_guardado = os.path.join(ruta_carpeta_mes, nombre_pdf)
    pdf.output(ruta_guardado)
    
    # Limpieza de temporales
    for img in [ruta_pareto_areas, ruta_pareto_causa, ruta_ranking]:
        if os.path.exists(img): os.remove(img)
    
    print(f"\n{CTerm.GREEN}{CTerm.BOLD}[ÉXITO] PDF Generado: data/outputs/{nombre_carpeta_mes}/{nombre_pdf}{CTerm.END}\n")

if __name__ == "__main__":
    generar_reporte()