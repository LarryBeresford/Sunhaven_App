import os
import datetime
import calendar
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import ListedColormap
from fpdf import FPDF
import gspread

# --- COLORES PARA LA TERMINAL (ESTÉTICA) ---
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

# Para las gráficas de este código, usar la misma carpeta donde vive el bot está bien como temporal
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__)) 

URL_GOOGLE_SHEET = "https://docs.google.com/spreadsheets/d/10wWKmjsyj501OXaFWs7Rd_XF_2R-H0YzV66B2K6HvPE/edit?usp=sharing"

# --- PALETA EJECUTIVA SUNHAVEN ---
C_NAVY = (31, 58, 82)
C_SUN = (211, 84, 0)
C_LIGHT_BG = (245, 247, 248)
C_DARK = (44, 62, 80)
C_SEC = (189, 195, 199)

# --- REGLAS DE NEGOCIO (ROLES) ---
ENFERMERAS_ROL_A = ["Consuelo Ceja Liborio", "Jaqueline Hernández Sosa"] # L-M-V
ENFERMERAS_ROL_B = ["Silvia Rodríguez Reynaga", "Guadalupe Georgia Lopez Ceja"] # M-J-S

def abreviar_nombre(nombre_completo):
    partes = str(nombre_completo).split()
    if len(partes) > 1:
        return f"{partes[0]} {partes[1][0]}."
    return partes[0] if partes else ""

# --- CLASE PARA EL PDF EJECUTIVO ---
class RondinesPDF(FPDF):
    def header(self):
        if self.page_no() == 1: return
        self.set_fill_color(*C_NAVY)
        self.rect(0, 0, 210, 26, 'F')
        self.set_fill_color(*C_SUN)
        self.rect(0, 26, 210, 1.5, 'F')
        self.set_y(9)
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, 'REPORTE EJECUTIVO DE RONDINES NOCTURNOS', 0, 1, 'C')
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
        self.set_font('Helvetica', 'B', 14)
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
        self.cell(0, 8, 'SUPERVISIÓN Y CUIDADO CONTINUO', 0, 1, 'C')
        self.set_y(140)
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(*C_DARK)
        self.cell(0, 10, 'REPORTE DE AUDITORÍA', 0, 1, 'C')
        self.set_font('Helvetica', 'B', 26)
        self.set_text_color(*C_SUN)
        self.cell(0, 12, 'RONDINES NOCTURNOS', 0, 1, 'C')
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

def conectar_google_sheets():
    print(f"{CTerm.BLUE}[1/5] Conectando a la nube de Google (API de Sheets)...{CTerm.END}")
    try:
        gc = gspread.service_account(filename=ARCHIVO_CREDENCIALES)
        sh = gc.open_by_url(URL_GOOGLE_SHEET)
        worksheet = sh.get_worksheet(0)
        datos = worksheet.get_all_records()
        df = pd.DataFrame(datos)
        print(f"      {CTerm.GREEN}Descargados {len(df)} registros totales del Formulario.{CTerm.END}")
        return df
    except Exception as e:
        print(f"{CTerm.RED}[ERROR] al conectar con Google Sheets: {e}{CTerm.END}")
        exit()

def procesar_datos(df, mes, anio):
    print(f"{CTerm.BLUE}[2/5] Limpiando y filtrando datos para el periodo seleccionado...{CTerm.END}")
    
    df['Marca temporal'] = pd.to_datetime(df['Marca temporal'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Marca temporal'])
    
    df['Fecha_Turno'] = pd.to_datetime(df['Marca temporal'].apply(
        lambda x: x.date() if x.hour >= 12 else (x - pd.Timedelta(days=1)).date()
    ))
    
    df = df[(df['Fecha_Turno'].dt.month == mes) & (df['Fecha_Turno'].dt.year == anio)].copy()
    
    if df.empty:
        print(f"{CTerm.YELLOW}[ADVERTENCIA] No hay registros válidos para el mes {mes} y año {anio} tras limpiar fechas.{CTerm.END}")
        exit()

    df = df.sort_values(by=['Enfermera', 'Marca temporal'])
    df['Diferencia_Segundos'] = df.groupby('Enfermera')['Marca temporal'].diff().dt.total_seconds()
    
    df['Dia'] = df['Fecha_Turno'].dt.day
    df['Hora'] = df['Marca temporal'].dt.hour
    
    def asignar_bloque(h):
        if 21 <= h <= 23: return "11 PM"
        elif 0 <= h <= 3: return "2 AM"
        elif 4 <= h <= 6: return "5 AM"
        return "Otro"
    
    df['Bloque_Horario'] = df['Hora'].apply(asignar_bloque)
    return df[df['Bloque_Horario'] != "Otro"].copy()

def generar_graficos(df):
    carpeta_temp = os.path.join(CARPETA_ACTUAL, "temp_charts")
    if not os.path.exists(carpeta_temp): os.makedirs(carpeta_temp)
    print(f"{CTerm.BLUE}[3/5] Generando Gráficos (Estética Sunhaven)...{CTerm.END}")
    
    plt.figure(figsize=(14, 14))
    conteo = df['Nombre del Residente'].value_counts().sort_values(ascending=False)
    sns.barplot(x=conteo.values, y=conteo.index, color='#1F3A52') 
    plt.title("Total de Escaneos QR por Residente", fontweight='bold', color='#1F3A52', fontsize=16)
    plt.xlabel("Total de Visitas")
    plt.tight_layout()
    plt.savefig(os.path.join(carpeta_temp, "g1_barras.png"))
    plt.close()

    plt.figure(figsize=(10, 12))
    pivot_bloques = df.pivot_table(index='Nombre del Residente', columns='Bloque_Horario', aggfunc='size', fill_value=0)
    cols_presentes = [c for c in ['11 PM', '2 AM', '5 AM'] if c in pivot_bloques.columns]
    if cols_presentes:
        sns.heatmap(pivot_bloques[cols_presentes], annot=True, cmap="RdYlGn", fmt="d")
        plt.title("Concentración por Bloques de Turno", fontweight='bold', color='#1F3A52')
        plt.tight_layout()
        plt.savefig(os.path.join(carpeta_temp, "g2_calor_bloques.png"))
    plt.close()

    plt.figure(figsize=(14, 10))
    pivot_dias = df.pivot_table(index='Nombre del Residente', columns='Dia', aggfunc='size', fill_value=0)
    cmap_estricto = ListedColormap(['#E74C3C', '#E74C3C', '#F39C12', '#2ECC71'])
    sns.heatmap(pivot_dias, cmap=cmap_estricto, annot=True, fmt="d", cbar=False, vmin=0, vmax=3)
    plt.title("Matriz de Cobertura Diaria", fontweight='bold', color='#1F3A52')
    plt.tight_layout()
    plt.savefig(os.path.join(carpeta_temp, "g3_calor_dias.png"))
    plt.close()

    plt.figure(figsize=(10, 6))
    df_vel = df[(df['Diferencia_Segundos'] > 0) & (df['Diferencia_Segundos'] < 300)]
    if not df_vel.empty:
        sns.boxplot(data=df_vel, x='Enfermera', y='Diferencia_Segundos', hue='Enfermera', palette="Pastel1", legend=False)
        plt.axhline(60, color='red', linestyle='--', label="Límite Trampa (<60s)")
        plt.title("Velocidad Promedio de Traslado entre Habitaciones", fontweight='bold', color='#1F3A52')
        plt.ylabel("Segundos")
        plt.tight_layout()
        plt.savefig(os.path.join(carpeta_temp, "g4_velocidad.png"))
    plt.close()

def crear_pdf(df, mes, anio, nombre_mes):
    print(f"{CTerm.BLUE}[4/5] Ensamblando PDF Ejecutivo (Dashboard Integral)...{CTerm.END}")
    pdf = RondinesPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    carpeta_temp = os.path.join(CARPETA_ACTUAL, "temp_charts")
    if not os.path.exists(carpeta_temp): os.makedirs(carpeta_temp)

    df_alertas = df[df['Diferencia_Segundos'] < 60].copy()
    alertas_totales = len(df_alertas)

    pdf.cover_page(nombre_mes, anio)
    
    _, dias_del_mes = calendar.monthrange(anio, mes)
    turnos_rol_A = 0 
    turnos_rol_B = 0 
    
    for dia in range(1, dias_del_mes + 1):
        dia_semana = datetime.date(anio, mes, dia).weekday()
        if dia_semana in [0, 2, 4]: turnos_rol_A += 1
        elif dia_semana in [1, 3, 5]: turnos_rol_B += 1
        
    pdf.add_page()
    pdf.chapter_title("1. CUMPLIMIENTO OPERATIVO MENSUAL")
    pdf.set_font("Helvetica", '', 11)
    
    pdf.multi_cell(0, 6, "Esquema: 3 rondines obligatorios por noche. La siguiente tabla evalúa el cumplimiento de lunes a sábado según el rol asignado (Los días domingo están excluidos del cálculo de desempeño):")
    pdf.ln(4)

    df_kpi = df[df['Fecha_Turno'].dt.weekday != 6].copy()
    rondas_por_enf = df_kpi[['Enfermera', 'Dia', 'Bloque_Horario']].drop_duplicates().groupby('Enfermera').size()
    
    pdf.set_fill_color(*C_NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 10)
    
    anchos = [45, 30, 35, 35, 40]
    headers = ['Colaborador', 'Turnos Meta', 'Meta Rondas', 'Rondas Real.', '% Cumplimiento']
    margen_izq = (210 - sum(anchos)) / 2
    
    pdf.set_x(margen_izq)
    for w, h in zip(anchos, headers):
        pdf.cell(w, 8, h, 1, 0, 'C', True)
    pdf.ln()
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*C_DARK)
    fill_row = False
    
    enfermeras_presentes = df['Enfermera'].unique()
    
    nombres_grafica = []
    porcentajes_grafica = []
    colores_grafica = []

    for enf in sorted(enfermeras_presentes):
        nombre_corto = abreviar_nombre(enf)
        
        if enf in ENFERMERAS_ROL_A: turnos = turnos_rol_A
        elif enf in ENFERMERAS_ROL_B: turnos = turnos_rol_B
        else: turnos = turnos_rol_A 
            
        meta_rondas = turnos * 3
        realizadas = rondas_por_enf.get(enf, 0)
        porcentaje = min((realizadas / meta_rondas) * 100, 100.0) if meta_rondas > 0 else 100.0
        
        nombres_grafica.append(nombre_corto)
        porcentajes_grafica.append(porcentaje)
        colores_grafica.append('#2ECC71' if porcentaje >= 90 else '#E74C3C')
        
        pdf.set_x(margen_izq)
        pdf.set_fill_color(*C_LIGHT_BG) if fill_row else pdf.set_fill_color(255, 255, 255)
        
        pdf.cell(anchos[0], 8, nombre_corto, 1, 0, 'C', fill_row)
        pdf.cell(anchos[1], 8, str(turnos), 1, 0, 'C', fill_row)
        pdf.cell(anchos[2], 8, str(meta_rondas), 1, 0, 'C', fill_row)
        pdf.cell(anchos[3], 8, str(realizadas), 1, 0, 'C', fill_row)
        
        if porcentaje >= 90:
            pdf.set_text_color(39, 174, 96)
            pdf.set_font('Helvetica', 'B', 10)
        else:
            pdf.set_text_color(211, 84, 0)
            pdf.set_font('Helvetica', 'B', 10)
        
        pdf.cell(anchos[4], 8, f"{porcentaje:.1f}%", 1, 1, 'C', fill_row)
        
        pdf.set_text_color(*C_DARK)
        pdf.set_font('Helvetica', '', 10)
        fill_row = not fill_row

    pdf.ln(8)

    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 6, "Resumen de Escaneos y Auditoría Antifraude:", ln=True)
    pdf.set_font("Helvetica", '', 11)
    
    pdf.cell(0, 6, f"Total de escaneos QR procesados en el periodo: {len(df)}", ln=True)
    
    if alertas_totales > 0:
        pdf.set_text_color(211, 84, 0)
        pdf.cell(0, 6, f"Alertas de velocidad detectadas (posible fraude): {alertas_totales}", ln=True)
    else:
        pdf.set_text_color(39, 174, 96)
        pdf.cell(0, 6, "Alertas de velocidad detectadas (posible fraude): 0 (Excelente)", ln=True)
        
    pdf.set_text_color(*C_DARK)
    pdf.ln(4)

    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    bars = plt.bar(nombres_grafica, porcentajes_grafica, color=colores_grafica)
    limite_y = max(110, max(porcentajes_grafica) + 10 if porcentajes_grafica else 110)
    plt.ylim(0, limite_y)
    plt.axhline(90, color='red', linestyle='--', alpha=0.5, label='Meta 90%')
    plt.title('% Cumplimiento por Colaborador', fontweight='bold', color='#1F3A52')
    plt.ylabel('Porcentaje (%)')
    for bar in bars:
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"{bar.get_height():.1f}%", 
                 ha='center', fontweight='bold', color='#1F3A52')

    plt.subplot(1, 2, 2)
    validos = len(df) - alertas_totales
    if alertas_totales > 0:
        wedges, texts, autotexts = plt.pie([validos, alertas_totales], labels=['Escaneos Válidos', 'Alertas (<60s)'],
                autopct='%1.1f%%', colors=['#1F3A52', '#E74C3C'], startangle=140)
    else:
        wedges, texts, autotexts = plt.pie([validos], labels=['Escaneos Válidos'],
                autopct='%1.1f%%', colors=['#1F3A52'], startangle=140)
        
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_weight('bold')
        
    plt.title('Proporción de Alertas vs Escaneos Válidos', fontweight='bold', color='#1F3A52')

    plt.tight_layout()
    ruta_dash = os.path.join(carpeta_temp, "g0_dashboard.png")
    plt.savefig(ruta_dash, transparent=True)
    plt.close()

    pdf.image(ruta_dash, x=10, w=190)
    os.remove(ruta_dash)

    graficos = [
        ("g1_barras.png", "2. VISITAS TOTALES POR RESIDENTE"),
        ("g2_calor_bloques.png", "3. PUNTOS CIEGOS: DESVIACIÓN DE HORARIOS"),
        ("g3_calor_dias.png", "4. EVOLUCIÓN DE COBERTURA DIARIA"),
        ("g4_velocidad.png", "5. PATRONES DE VELOCIDAD DE ESCANEO")
    ]
    
    for img_name, titulo in graficos:
        img_path = os.path.join(carpeta_temp, img_name)
        if os.path.exists(img_path):
            pdf.add_page()
            pdf.chapter_title(titulo)
            pdf.image(img_path, x=10, w=190)
            os.remove(img_path) 
            
    pdf.add_page()
    pdf.chapter_title("6. BITÁCORA DE INCIDENTES CRÍTICOS (EVIDENCIA)")
    
    if not df_alertas.empty:
        pdf.set_font("Helvetica", '', 10)
        pdf.multi_cell(0, 6, f"Evidencia para acta administrativa: {len(df_alertas)} eventos registrados con una diferencia de tiempo irreal entre escaneos (< 60 segundos).")
        pdf.ln(4)
        
        anchos_ev = [45, 25, 25, 60, 35]
        headers_ev = ['Colaborador', 'Fecha', 'Hora', 'Residente Visitado', 'Segundos vs Ant.']
        margen_ev = (210 - sum(anchos_ev)) / 2
        
        pdf.set_fill_color(*C_NAVY)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 9)
        
        pdf.set_x(margen_ev)
        for w, h in zip(anchos_ev, headers_ev):
            pdf.cell(w, 8, h, 1, 0, 'C', True)
        pdf.ln()
        
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(*C_DARK)
        fill_row = False
        
        for _, row in df_alertas.iterrows():
            if pdf.get_y() > 260: 
                pdf.add_page()
                pdf.set_x(margen_ev)
                pdf.set_fill_color(*C_NAVY)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font('Helvetica', 'B', 9)
                for w, h in zip(anchos_ev, headers_ev):
                    pdf.cell(w, 8, h, 1, 0, 'C', True)
                pdf.ln()
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(*C_DARK)
                
            nombre_corto = abreviar_nombre(row['Enfermera'])
            fecha_str = row['Marca temporal'].strftime('%d/%m/%Y')
            hora_str = row['Marca temporal'].strftime('%H:%M:%S')
            
            residente = str(row['Nombre del Residente'])
            if len(residente) > 30: residente = residente[:27] + "..."
            
            segundos = f"{int(row['Diferencia_Segundos'])} s"
            
            pdf.set_x(margen_ev)
            pdf.set_fill_color(*C_LIGHT_BG) if fill_row else pdf.set_fill_color(255, 255, 255)
            
            pdf.cell(anchos_ev[0], 6, nombre_corto, 1, 0, 'C', fill_row)
            pdf.cell(anchos_ev[1], 6, fecha_str, 1, 0, 'C', fill_row)
            pdf.cell(anchos_ev[2], 6, hora_str, 1, 0, 'C', fill_row)
            pdf.cell(anchos_ev[3], 6, residente, 1, 0, 'C', fill_row)
            
            pdf.set_text_color(211, 84, 0)
            pdf.set_font('Helvetica', 'B', 8)
            pdf.cell(anchos_ev[4], 6, segundos, 1, 1, 'C', fill_row)
            
            pdf.set_text_color(*C_DARK)
            pdf.set_font('Helvetica', '', 8)
            fill_row = not fill_row

    else:
        pdf.set_font("Helvetica", 'I', 11)
        pdf.cell(0, 10, "No se registraron alertas de fraude por velocidad en este periodo.", 0, 1)

    nombre_carpeta_mes = f"{mes:02d}_{nombre_mes}_{anio}"
    ruta_carpeta_mes = os.path.join(CARPETA_OUTPUTS, nombre_carpeta_mes)
    os.makedirs(ruta_carpeta_mes, exist_ok=True)

    nombre_pdf = f"Reporte_Rondines_{mes:02d}_{anio}.pdf"
    ruta_guardado = os.path.join(ruta_carpeta_mes, nombre_pdf)
    pdf.output(ruta_guardado)
    
    print(f"\n{CTerm.GREEN}{CTerm.BOLD}[5/5] 🚀 [ÉXITO TOTAL] Reporte guardado en: data/outputs/{nombre_carpeta_mes}/{nombre_pdf}{CTerm.END}\n")

def main():
    print(f"\n{CTerm.CYAN}{CTerm.BOLD}============================================================{CTerm.END}")
    print(f"{CTerm.CYAN}{CTerm.BOLD}   SISTEMA DE AUDITORÍA NOCTURNA - SUNHAVEN{CTerm.END}")
    print(f"{CTerm.CYAN}{CTerm.BOLD}============================================================{CTerm.END}\n")
    
    try:
        mes_actual = datetime.date.today().month
        anio_actual = datetime.date.today().year
        
        entrada_mes = input(f"{CTerm.YELLOW}Ingrese el número del MES a evaluar (1-12) [Enter para mes actual ({mes_actual})]: {CTerm.END}").strip()
        mes = int(entrada_mes) if entrada_mes else mes_actual
        
        entrada_anio = input(f"{CTerm.YELLOW}Ingrese el AÑO a evaluar (ej. 2026) [Enter para año actual ({anio_actual})]: {CTerm.END}").strip()
        anio = int(entrada_anio) if entrada_anio else anio_actual
        
        if not (1 <= mes <= 12):
            print(f"\n{CTerm.RED}[ERROR] El mes debe ser un número entre 1 y 12. Inténtalo de nuevo.{CTerm.END}")
            return
            
    except ValueError:
        print(f"\n{CTerm.RED}[ERROR] Entrada inválida. Por favor ingresa solo números.{CTerm.END}")
        return

    meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    nombre_mes = meses_nombres[mes - 1]
    
    print(f"\n{CTerm.BLUE}[INFO] Iniciando procesamiento estricto para: {nombre_mes.upper()} {anio}...{CTerm.END}")

    df_crudo = conectar_google_sheets()
    df_procesado = procesar_datos(df_crudo, mes, anio)
    generar_graficos(df_procesado)
    crear_pdf(df_procesado, mes, anio, nombre_mes)

if __name__ == "__main__":
    main()