import streamlit as st
import pandas as pd
import gspread
import json
import os
from datetime import datetime, timedelta

# ==========================================
# 0. CONFIGURACIÓN DE RUTAS ABSOLUTAS
# ==========================================
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
.stCheckbox > label { font-weight: 500; color: #334155; }
</style>
""", unsafe_allow_html=True)

HEX_NAVY = "#1e293b"
HEX_GREEN = "#10b981"
HEX_RED = "#ef4444"

# ==========================================
# 2. MOTOR DE DATOS Y CONEXIÓN SEGURA
# ==========================================
@st.cache_data(ttl=3600)
def motor_bi_sunhaven():
    """Lógica de autenticación: Nube (Secrets) o Local (Archivo json)"""
    try:
        if "GOOGLE_JSON" in st.secrets:
            cred_info = json.loads(st.secrets["GOOGLE_JSON"])
            gc = gspread.service_account_from_dict(cred_info)
        else:
            if os.path.exists(PATH_CREDS):
                gc = gspread.service_account(filename=PATH_CREDS)
            else:
                st.error("Error: Archivo de credenciales no encontrado.")
                st.stop()
    except Exception as e:
        st.error(f"Error de Autenticación: Verifique sus credenciales. Detalle: {e}")
        st.stop()
        
    try:
        sh_n = gc.open_by_url("https://docs.google.com/spreadsheets/d/10wWKmjsyj501OXaFWs7Rd_XF_2R-H0YzV66B2K6HvPE/edit").get_worksheet(0)
        sh_v = gc.open_by_url("https://docs.google.com/spreadsheets/d/1C1AVmNXG0ggRekB1HF4_IhX-NGiTkwzgvZn2Z31rCsc/edit").get_worksheet(0)
        sh_s = gc.open_by_url("https://docs.google.com/spreadsheets/d/1wdP3mbW_k4a90ubPG-ZQy8FvfAZiwKnhPjCj1BZHcBs/edit").get_worksheet(0)
        sh_k = gc.open_by_url("https://docs.google.com/spreadsheets/d/17cfEItyso_x6dhNmMxK8XTM-psCFmk1XGYnie-Uvt68/edit").get_worksheet(0)
        
        df_n = pd.DataFrame(sh_n.get_all_records())
        df_v = pd.DataFrame(sh_v.get_all_records())
        df_s = pd.DataFrame(sh_s.get_all_records())
        df_k = pd.DataFrame(sh_k.get_all_records())
        
        # LIMPIEZA CRÍTICA DE ENCABEZADOS (Para evitar fallos de Pandas)
        for df in [df_n, df_v, df_s, df_k]:
            df.columns = df.columns.str.strip().str.replace('\n', ' ')
            
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

    data = motor_bi_sunhaven()
    df_rop = data["v"]
    df_serv = data["s"]
    df_kaizen = data["k"]

    # --- PROCESAMIENTO OEE DINÁMICO (Lógica de bot_operaciones.py) ---
    try:
        # Extraer columnas dinámicamente
        col_5s = [c for c in df_rop.columns if "Orden" in c][0]
        col_camas = [c for c in df_rop.columns if "Tendido" in c][0]
        col_enf = [c for c in df_rop.columns if "enfermera" in c.lower()][0]
        
        c_uni = [c for c in df_serv.columns if "uniforme" in c.lower()][0]
        c_bas = [c for c in df_serv.columns if "basura" in c.lower()][0]
        c_rop = [c for c in df_serv.columns if "ropa sucia" in c.lower()][0]
        c_jab = [c for c in df_serv.columns if "jabón" in c.lower() or "jabon" in c.lower()][0]
        c_lim = [c for c in df_serv.columns if "zonas asignadas" in c.lower()][0]

        # Estandarización a base 100
        df_rop[col_5s] = pd.to_numeric(df_rop[col_5s], errors='coerce') * 10
        df_rop[col_camas] = pd.to_numeric(df_rop[col_camas], errors='coerce') * 10
        df_rop['Promedio_Total'] = (df_rop[col_5s] + df_rop[col_camas]) / 2

        for c in [c_uni, c_bas, c_rop, c_jab, c_lim]:
            df_serv[c] = pd.to_numeric(df_serv[c], errors='coerce') * 10

        # Cálculos de KPI
        kpis_areas = {
            'Cocina': df_serv[[c_uni, c_bas]].mean().mean(),
            'Lavandería': df_serv[[c_rop, c_jab]].mean().mean(),
            'Limpieza General': df_serv[c_lim].mean(),
            'Roperos (Habitaciones)': df_rop['Promedio_Total'].mean()
        }
        kpis_areas = {k: (v if pd.notna(v) else 0) for k, v in kpis_areas.items()}
        oee_global = sum(kpis_areas.values()) / len(kpis_areas) if kpis_areas else 0

        metricas_detalle = {
            '5S (Orden Roperos)': df_rop[col_5s].mean(),
            'Estética (Tendido Camas)': df_rop[col_camas].mean(),
            'Uniforme (Cocina)': df_serv[c_uni].mean(),
            'Manejo Basura (Cocina)': df_serv[c_bas].mean(),
            'Separación (Lavandería)': df_serv[c_rop].mean(),
            'Dosificación Jabón (Lavandería)': df_serv[c_jab].mean(),
            'Limpieza Zonas (Intendencia)': df_serv[c_lim].mean()
        }
        metricas_detalle = {k: (v if pd.notna(v) else 0) for k, v in metricas_detalle.items()}
        metricas_detalle_sorted = dict(sorted(metricas_detalle.items(), key=lambda item: item[1]))

        nombres_enfermeras = sorted(df_rop[col_enf].dropna().unique().tolist())

    except Exception as e:
        st.error(f"Error procesando columnas para gráficos: {e}. Asegúrate de que las hojas tienen datos.")
        oee_global = 0
        kpis_areas = {}
        metricas_detalle_sorted = {}
        nombres_enfermeras = []

    # --- RENDERIZADO DEL HEADER DINÁMICO ---
    color_header = HEX_GREEN if oee_global >= 90 else HEX_RED
    estatus_texto = "OPERACIÓN ESTABLE" if oee_global >= 90 else "REQUIERE ATENCIÓN"

    st.markdown(f"""<div class='exec-header' style='border-left: 8px solid {color_header};'>
        <div><p style='margin:0; font-weight:600; color:#64748b;'>Estatus Global</p><h1>{estatus_texto}</h1></div>
        <div style='text-align:right;'><p style='margin:0; font-weight:600; color:#64748b;'>OEE / ICO Maestro</p><h1>{oee_global:.1f}%</h1></div>
    </div>""", unsafe_allow_html=True)

    t1, t2, t3, t4, t5 = st.tabs(["Rendimiento", "Causa Raíz", "Equipo", "Kaizen", "Normativa Legal"])

    with t1:
        st.write("### Desempeño Operativo por Área")
        if kpis_areas:
            df_chart_areas = pd.DataFrame.from_dict(kpis_areas, orient='index', columns=['Cumplimiento (%)'])
            st.bar_chart(df_chart_areas, color=HEX_NAVY)
        else:
            st.info("No hay datos suficientes para graficar.")

    with t2:
        st.write("### Análisis de Causa Raíz (Pareto de Desviaciones)")
        if metricas_detalle_sorted:
            # Gráfico horizontal nativo de Streamlit
            df_chart_causa = pd.DataFrame.from_dict(metricas_detalle_sorted, orient='index', columns=['Nivel de Cumplimiento (%)'])
            st.bar_chart(df_chart_causa, horizontal=True, color=HEX_RED)
            
            peor_criterio = list(metricas_detalle_sorted.keys())[0]
            peor_valor = list(metricas_detalle_sorted.values())[0]
            if peor_valor < 90:
                st.error(f"**Cuello de botella principal:** {peor_criterio} con un {peor_valor:.1f}%. Se recomienda capacitación inmediata en esta área.")
        else:
            st.info("No hay datos suficientes para graficar.")

    with t3:
        st.write("### Cumplimiento Individual y Asistencia")
        if nombres_enfermeras:
            colaborador = st.selectbox("Seleccionar Colaborador:", nombres_enfermeras)
            df_filtrado = df_rop[df_rop[col_enf] == colaborador]
            
            if not df_filtrado.empty:
                promedio_ind = df_filtrado['Promedio_Total'].mean()
                col1, col2 = st.columns(2)
                col1.metric(label="Calidad de Ejecución (OEE Individual)", value=f"{promedio_ind:.1f}%")
                col2.metric(label="Total de Auditorías Registradas", value=len(df_filtrado))
                st.dataframe(df_filtrado[[col_5s, col_camas, 'Promedio_Total']], use_container_width=True)
            else:
                st.warning("El colaborador seleccionado no tiene auditorías en este rango.")
        else:
            st.info("No se encontraron registros de colaboradores.")

    with t4:
        st.write("### Gestión de Mejora Continua (Buzón Kaizen)")
        if not df_kaizen.empty:
            st.dataframe(df_kaizen.tail(10), use_container_width=True)
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

        if 'checks_normas' not in st.session_state:
            st.session_state.checks_normas = {item: False for cat in categorias.values() for item in cat}

        c1, c2 = st.columns(2)
        idx = 0
        for cat, items in categorias.items():
            col = c1 if idx % 2 == 0 else c2
            with col.expander(cat, expanded=True):
                for item in items:
                    st.session_state.checks_normas[item] = st.checkbox(item, value=st.session_state.checks_normas[item], key=item)
            idx += 1
        
        total = len(st.session_state.checks_normas)
        actual = sum(st.session_state.checks_normas.values())
        porcentaje = (actual / total) * 100
        
        st.divider()
        st.write(f"### Nivel de Blindaje Institucional: {int(porcentaje)}%")
        
        if porcentaje < 50:
            st.markdown("""<style>.stProgress > div > div > div > div { background-color: #ef4444; }</style>""", unsafe_allow_html=True)
        elif porcentaje < 80:
             st.markdown("""<style>.stProgress > div > div > div > div { background-color: #f59e0b; }</style>""", unsafe_allow_html=True)
        else:
             st.markdown(f"""<style>.stProgress > div > div > div > div {{ background-color: {HEX_GREEN}; }}</style>""", unsafe_allow_html=True)
                
        st.progress(porcentaje / 100)
        
        if st.button("Guardar Diagnóstico de Auditoría", use_container_width=True):
            st.success("Estatus normativo actualizado correctamente en la sesión.")

    st.markdown("<div class='footer-watermark'>MASTER SUITE BUSINESS INTELLIGENCE - Ing. Larry Beresford</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()