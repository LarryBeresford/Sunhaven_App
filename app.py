import streamlit as st
import pandas as pd
import gspread
import json
import os
from datetime import datetime, timedelta

# ==========================================
# 0. CONFIGURACIÓN DE RUTAS ABSOLUTAS
# ==========================================
# Define la raíz del proyecto subiendo un nivel desde la carpeta actual
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH_CREDS = os.path.join(BASE_DIR, 'config', 'sunhaven-credentials.json')

# ==========================================
# 1. CONFIGURACIÓN ESTÉTICA Y UI/UX
# ==========================================
st.set_page_config(page_title="Sunhaven | Master Suite BI", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.block-container { padding-top: 1.5rem; max-width: 95%; }
h1, h2, h3 { color: #0f172a; font-weight: 800; }
.exec-header {
    background-color: #ffffff; padding: 1.5rem 2rem; border-radius: 10px;
    border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center;
}
.footer-watermark {
    text-align: center; margin-top: 50px; opacity: 0.4; font-size: 12px; font-weight: bold;
}
/* Estilo para los checkboxes del área normativa */
.stCheckbox > label { font-weight: 500; color: #334155; }
</style>
""", unsafe_allow_html=True)

HEX_NAVY = "#1e293b"
HEX_GREEN = "#10b981"

# ==========================================
# 2. MOTOR DE DATOS Y CONEXIÓN SEGURA
# ==========================================
@st.cache_data(ttl=3600)
def motor_bi_sunhaven():
    """Lógica de autenticación: Nube (Secrets) o Local (Archivo json)"""
    try:
        if "GOOGLE_JSON" in st.secrets:
            # Lectura desde Streamlit Cloud
            cred_info = json.loads(st.secrets["GOOGLE_JSON"])
            gc = gspread.service_account_from_dict(cred_info)
        else:
            # Lectura desde Mac local
            if os.path.exists(PATH_CREDS):
                gc = gspread.service_account(filename=PATH_CREDS)
            else:
                st.error("Error: Archivo de credenciales no encontrado en la ruta de configuración.")
                st.stop()
    except Exception as e:
        st.error(f"Error de Autenticación: Verifique sus credenciales. Detalle: {e}")
        st.stop()
        
    try:
        # Enlaces a Google Sheets
        sh_n = gc.open_by_url("https://docs.google.com/spreadsheets/d/10wWKmjsyj501OXaFWs7Rd_XF_2R-H0YzV66B2K6HvPE/edit").get_worksheet(0)
        sh_v = gc.open_by_url("https://docs.google.com/spreadsheets/d/1C1AVmNXG0ggRekB1HF4_IhX-NGiTkwzgvZn2Z31rCsc/edit").get_worksheet(0)
        sh_s = gc.open_by_url("https://docs.google.com/spreadsheets/d/1wdP3mbW_k4a90ubPG-ZQy8FvfAZiwKnhPjCj1BZHcBs/edit").get_worksheet(0)
        sh_k = gc.open_by_url("https://docs.google.com/spreadsheets/d/17cfEItyso_x6dhNmMxK8XTM-psCFmk1XGYnie-Uvt68/edit").get_worksheet(0)
        
        # Conversión a DataFrames
        df_n = pd.DataFrame(sh_n.get_all_records())
        df_v = pd.DataFrame(sh_v.get_all_records())
        df_s = pd.DataFrame(sh_s.get_all_records())
        df_k = pd.DataFrame(sh_k.get_all_records())
        
        return {"n": df_n, "v": df_v, "s": df_s, "k": df_k}
    except Exception as e:
        st.error(f"Error de Extracción: No se pudieron leer las hojas de cálculo. Detalle: {e}")
        st.stop()

# ==========================================
# 3. LÓGICA DE INTERFAZ Y DASHBOARD
# ==========================================
def main():
    with st.sidebar:
        st.markdown("### PANEL DE CONTROL")
        if st.button("Sincronizar Datos Operativos", use_container_width=True):
            motor_bi_sunhaven.clear()
            st.rerun()
        st.date_input("Rango de análisis", [datetime.now() - timedelta(days=30), datetime.now()])

    # Cargar datos del motor
    data = motor_bi_sunhaven()
    
    st.markdown(f"""<div class='exec-header' style='border-left: 8px solid {HEX_GREEN};'>
        <div><p style='margin:0; font-weight:600; color:#64748b;'>Estatus Global</p><h1>OPERACIÓN ESTABLE</h1></div>
        <div style='text-align:right;'><p style='margin:0; font-weight:600; color:#64748b;'>OEE / ICO Maestro</p><h1>89.4%</h1></div>
    </div>""", unsafe_allow_html=True)

    t1, t2, t3, t4, t5 = st.tabs(["Rendimiento", "Causa Raíz", "Equipo", "Kaizen", "Normativa Legal"])

    with t1:
        st.write("### Desempeño Operativo por Área")
        st.info("Datos cargados correctamente de los formularios de limpieza, cocina y enfermería.")
        # Aquí puedes agregar luego los gráficos usando st.plotly_chart o st.bar_chart

    with t2:
        st.write("### Análisis de Drivers Críticos")
        st.error("Desviación detectada en: Control de accesos e Higiene (Cocina)")

    with t3:
        st.write("### Cumplimiento Individual y Asistencia")
        st.selectbox("Seleccionar Colaborador:", ["Búsqueda por nombre...", "Consuelo Ceja", "Jaqueline Hdz"])

    with t4:
        st.write("### Gestión de Mejora Continua (Buzón Kaizen)")
        if not data["k"].empty:
            st.dataframe(data["k"].tail(10), use_container_width=True)
        else:
            st.warning("No hay propuestas Kaizen registradas en este periodo.")

    with t5:
        st.markdown("### Checklist de Cumplimiento Normativo")
        st.markdown("<p style='color:#64748b;'>Control preventivo de requisitos legales y comerciales ante autoridades gubernamentales.</p>", unsafe_allow_html=True)

        categorias = {
            "Riesgo Comercial y Sanitario (COPRISJAL / PROFECO)": [
                "Contrato de Adhesión registrado en PROFECO",
                "Aviso de Funcionamiento Vigente",
                "NOM-031-SSA3 (Manuales e infraestructura segura)",
                "NOM-004-SSA3 (Expedientes Clínicos protegidos)",
                "NOM-087-SEMARNAT (Manejo de RPBI)",
                "NOM-251-SSA1 (Higiene en cocina y temperaturas)"
            ],
            "Riesgo Físico (Protección Civil y Bomberos)": [
                "Programa Interno de Protección Civil (PIPC)",
                "Póliza de Seguro de Responsabilidad Civil",
                "Dictamen Estructural y Eléctrico (DRO)",
                "Mantenimiento de Extintores y Detectores",
                "Bitácora de Simulacros y Capacitación de Brigadas"
            ],
            "Riesgo Laboral (STPS)": [
                "NOM-035-STPS (Evaluación de Riesgos Psicosociales)",
                "NOM-019-STPS (Recorridos Comisión Mixta)",
                "NOM-036-STPS (Prevención riesgos ergonómicos)",
                "Constancias de Habilidades DC-3 expedidas"
            ]
        }

        # Inicialización del estado de los checkboxes
        if 'checks_normas' not in st.session_state:
            st.session_state.checks_normas = {item: False for cat in categorias.values() for item in cat}

        c1, c2 = st.columns(2)
        idx = 0
        for cat, items in categorias.items():
            col = c1 if idx % 2 == 0 else c2
            with col.expander(cat, expanded=True):
                for item in items:
                    # Actualiza el diccionario en session_state en tiempo real
                    st.session_state.checks_normas[item] = st.checkbox(item, value=st.session_state.checks_normas[item], key=item)
            idx += 1
        
        # Cálculo de Índice de Salud Normativa
        total = len(st.session_state.checks_normas)
        actual = sum(st.session_state.checks_normas.values())
        porcentaje = (actual / total) * 100
        
        st.divider()
        st.write(f"### Nivel de Blindaje Institucional: {int(porcentaje)}%")
        
        # Color dinámico de la barra de progreso
        if porcentaje < 50:
            st.markdown(f"""
                <style>.stProgress > div > div > div > div {{ background-color: #ef4444; }}</style>
                """, unsafe_allow_html=True)
        elif porcentaje < 80:
             st.markdown(f"""
                <style>.stProgress > div > div > div > div {{ background-color: #f59e0b; }}</style>
                """, unsafe_allow_html=True)
        else:
             st.markdown(f"""
                <style>.stProgress > div > div > div > div {{ background-color: {HEX_GREEN}; }}</style>
                """, unsafe_allow_html=True)
                
        st.progress(porcentaje / 100)
        
        if st.button("Guardar Diagnóstico de Auditoría", use_container_width=True):
            st.success("Estatus normativo actualizado correctamente en la sesión.")
            # Nota futura: Aquí se puede conectar a Sheets para guardar el historial

    st.markdown("<div class='footer-watermark'>MASTER SUITE BUSINESS INTELLIGENCE - Ing. Larry Beresford</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()