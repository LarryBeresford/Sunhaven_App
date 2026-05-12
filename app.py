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
# 0. CONFIGURACIÓN Y SEGURIDAD
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH_CREDS = os.path.join(BASE_DIR, 'config', 'sunhaven-credentials.json')

st.set_page_config(page_title="Sunhaven | Master Suite BI", layout="wide", initial_sidebar_state="expanded")

# --- DISEÑO ESTÉTICO EXQUISITO ---
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; max-width: 95%; }
    h1, h2, h3 { color: #0f172a; font-weight: 800; }
    .exec-header {
        background-color: #ffffff; padding: 1.5rem 2rem; border-radius: 10px;
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center;
    }
    .kpi-card {
        background-color: #f8fafc; padding: 20px; border-radius: 10px;
        border-left: 6px solid #1e293b; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        text-align: center;
        transition: transform 0.2s ease-in-out;
    }
    .kpi-card:hover { transform: translateY(-5px); }
    .metric-label { font-size: 15px; color: #64748b; font-weight: 700; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px;}
    .metric-value { font-size: 32px; font-weight: 900; color: #0f172a; margin: 0;}
    .footer-watermark { text-align: center; margin-top: 60px; opacity: 0.5; font-size: 13px; font-weight: bold; letter-spacing: 1px; }
    .stCheckbox > label { font-weight: 500; color: #334155; }
</style>
""", unsafe_allow_html=True)

HEX_GREEN = "#10b981"
HEX_RED = "#ef4444"
HEX_NAVY = "#1e293b"
HEX_SUN = "#f59e0b"

# ==========================================
# 1. MOTOR DE DATOS (CONEXIÓN EN VIVO)
# ==========================================
@st.cache_data(ttl=600)
def cargar_datos_sunhaven():
    try:
        if "GOOGLE_JSON" in st.secrets:
            gc = gspread.service_account_from_dict(json.loads(st.secrets["GOOGLE_JSON"]))
        else:
            gc = gspread.service_account(filename=PATH_CREDS)
            
        sh_n = gc.open_by_url("https://docs.google.com/spreadsheets/d/10wWKmjsyj501OXaFWs7Rd_XF_2R-H0YzV66B2K6HvPE/edit").get_worksheet(0)
        sh_v = gc.open_by_url("https://docs.google.com/spreadsheets/d/1C1AVmNXG0ggRekB1HF4_IhX-NGiTkwzgvZn2Z31rCsc/edit").get_worksheet(0)
        sh_s = gc.open_by_url("https://docs.google.com/spreadsheets/d/1wdP3mbW_k4a90ubPG-ZQy8FvfAZiwKnhPjCj1BZHcBs/edit").get_worksheet(0)
        sh_k = gc.open_by_url("https://docs.google.com/spreadsheets/d/17cfEItyso_x6dhNmMxK8XTM-psCFmk1XGYnie-Uvt68/edit").get_worksheet(0)
        
        dfs = {
            "n": pd.DataFrame(sh_n.get_all_records()),
            "v": pd.DataFrame(sh_v.get_all_records()),
            "s": pd.DataFrame(sh_s.get_all_records()),
            "k": pd.DataFrame(sh_k.get_all_records())
        }
        for k in dfs:
            dfs[k].columns = dfs[k].columns.str.strip().str.replace('\n', ' ')
        return dfs
    except Exception as e:
        st.error(f"Error crítico de conexión: {e}")
        st.stop()

# ==========================================
# 2. LÓGICA PRINCIPAL DEL SISTEMA
# ==========================================
def main():
    # --- PANEL LATERAL (SIDEBAR Y BOTS PDF) ---
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/dashboard-layout.png", width=60)
        st.markdown("## SUNHAVEN OS")
        
        st.divider()
        st.markdown("### ⚙️ CONTROL DE DATOS")
        if st.button("🔄 Sincronizar en Vivo", use_container_width=True):
            cargar_datos_sunhaven.clear()
            st.rerun()
        st.date_input("Periodo Analizado", [datetime.now() - timedelta(days=30), datetime.now()])
        
        st.divider()
        st.markdown("### 📄 MOTOR DE REPORTES PDF")
        st.caption("Central de ejecución de scripts automatizados")
        
        if st.button("📊 Generar PDF Operaciones", use_container_width=True):
            st.info("Ejecutando bot_operaciones.py...")
            try:
                subprocess.run([sys.executable, os.path.join(BASE_DIR, 'tools', 'bot_operaciones.py')], check=True)
                st.success("Reporte generado en data/outputs")
            except Exception as e:
                st.error("Error al ejecutar el script.")
                
        if st.button("💡 Generar PDF Kaizen", use_container_width=True):
             st.info("Ejecutando bot_kaizen.py...")
             try:
                subprocess.run([sys.executable, os.path.join(BASE_DIR, 'tools', 'bot_kaizen.py')], check=True)
                st.success("Reporte generado.")
             except: st.warning("Asegúrate de que el archivo exista.")
             
        if st.button("🕒 Generar PDF Retardos", use_container_width=True):
             st.info("Ejecutando bot_retardos.py...")
             try:
                subprocess.run([sys.executable, os.path.join(BASE_DIR, 'tools', 'bot_retardos.py')], check=True)
                st.success("Reporte generado.")
             except: st.warning("Asegúrate de que el archivo exista.")

    # --- PROCESAMIENTO MATEMÁTICO ---
    data = cargar_datos_sunhaven()
    df_ron, df_rop, df_serv, df_kaizen = data["n"], data["v"], data["s"], data["k"]

    try:
        # Traductor Maestro
        def clean(serie):
            mapeo = {
                'sí': 10, 'si': 10, 'no': 0, 'cumple': 10, 'no cumple': 0, 
                'separada': 10, 'bien': 10, 'ok': 10, 'limpio': 10, 'sucio': 0,
                'verdadero': 10, 'falso': 0
            }
            return pd.to_numeric(serie.astype(str).str.strip().str.lower().replace(mapeo), errors='coerce') * 10

        # Identificación de columnas
        c_5s = [c for c in df_rop.columns if "Orden" in c][0]
        c_cam = [c for c in df_rop.columns if "Tendido" in c][0]
        col_enf = [c for c in df_rop.columns if "enfermera" in c.lower()][0]

        c_uni = [c for c in df_serv.columns if "uniforme" in c.lower()][0]
        c_bas = [c for c in df_serv.columns if "basura" in c.lower()][0]
        c_lav_r = [c for c in df_serv.columns if "ropa" in c.lower() or "separad" in c.lower()][0]
        c_lav_j = [c for c in df_serv.columns if "jabón" in c.lower() or "jabon" in c.lower()][0]
        c_lim = [c for c in df_serv.columns if "zonas asignadas" in c.lower()][0]
        
        metadata_cols = ['marca temporal', 'nombre', 'turno', 'area', 'área', 'sección']
        c_ron_list = [c for c in df_ron.columns if not any(m in c.lower() for m in metadata_cols)]

        # Limpieza e integración
        for c in [c_5s, c_cam]: df_rop[c] = clean(df_rop[c])
        df_rop['Promedio_Total'] = (df_rop[c_5s] + df_rop[c_cam]) / 2

        for c in [c_uni, c_bas, c_lav_r, c_lav_j, c_lim]: df_serv[c] = clean(df_serv[c])
        for c in c_ron_list: df_ron[c] = clean(df_ron[c])

        # Construcción de KPIs de Área (Promedios combinados)
        areas_dict = {
            "Enfermería Nocturna": df_ron[c_ron_list].mean().mean() if not df_ron.empty else 0,
            "Enfermería Vespertina": (df_rop[c_5s].mean() + df_rop[c_cam].mean()) / 2,
            "Cocina": (df_serv[c_uni].mean() + df_serv[c_bas].mean()) / 2,
            "Lavandería": (df_serv[c_lav_r].mean() + df_serv[c_lav_j].mean()) / 2,
            "Limpieza General": df_serv[c_lim].mean()
        }
        areas_dict = {k: (v if pd.notna(v) else 0) for k, v in areas_dict.items()}
        ico_master = sum(areas_dict.values()) / len(areas_dict) if areas_dict else 0

        # Construcción de Causa Raíz (Criterios aislados)
        criterios = {
            "Uniforme (Cocina)": df_serv[c_uni].mean(), 
            "Basura (Cocina)": df_serv[c_bas].mean(),
            "Ropa Separada (Lavandería)": df_serv[c_lav_r].mean(), 
            "Uso Jabón (Lavandería)": df_serv[c_lav_j].mean(),
            "Limpieza de Zonas": df_serv[c_lim].mean(), 
            "5S (Roperos)": df_rop[c_5s].mean(),
            "Estética (Camas)": df_rop[c_cam].mean()
        }
        for c in c_ron_list:
            nombre_corto = c[:30] + "..." if len(c) > 30 else c
            criterios[f"Nocturno: {nombre_corto}"] = df_ron[c].mean()
            
        criterios = {k: (v if pd.notna(v) else 0) for k, v in criterios.items()}

    except Exception as e:
        st.error(f"Error procesando el tejido de datos: {e}")
        ico_master = 0

    # --- ENCABEZADO EJECUTIVO ---
    color_header = HEX_GREEN if ico_master >= 90 else HEX_RED
    estatus = "OPERACIÓN ESTABLE" if ico_master >= 90 else "REQUIERE INTERVENCIÓN"

    st.markdown(f"""<div class='exec-header' style='border-left: 8px solid {color_header};'>
        <div><p style='margin:0; font-weight:600; color:#64748b; letter-spacing: 1px;'>Estatus Institucional</p><h1>{estatus}</h1></div>
        <div style='text-align:right;'><p style='margin:0; font-weight:600; color:#64748b; letter-spacing: 1px;'>Índice de Calidad Operativa (ICO)</p>
        <h1 style='color:{color_header}; font-size: 42px;'>{ico_master:.1f}%</h1></div>
    </div>""", unsafe_allow_html=True)

    # --- LAS 5 PESTAÑAS ESTRATÉGICAS ---
    t1, t2, t3, t4, t5 = st.tabs(["📊 Tablero Directivo", "👥 Desempeño Individual", "💡 Buzón Kaizen", "⚖️ Blindaje Normativo", "🔍 Auditoría de Datos"])

    with t1:
        st.write("### Tarjetas de Rendimiento por Departamento")
        cols = st.columns(5)
        for i, (area, valor) in enumerate(areas_dict.items()):
            with cols[i]:
                c_kpi = HEX_GREEN if valor >= 90 else HEX_RED
                st.markdown(f"""<div class='kpi-card' style='border-left-color: {c_kpi};'>
                    <p class='metric-label'>{area}</p>
                    <p class='metric-value'>{valor:.1f}%</p>
                </div>""", unsafe_allow_html=True)

        st.divider()

        # Análisis Gráfico con Línea del 90%
        c1, c2 = st.columns(2)
        with c1:
            st.write("#### 1. Evaluación General (Pareto de Áreas)")
            df_p_area = pd.DataFrame.from_dict(areas_dict, orient='index', columns=['Valor']).sort_values('Valor', ascending=False).reset_index()
            fig_a = go.Figure()
            fig_a.add_trace(go.Bar(x=df_p_area['index'], y=df_p_area['Valor'], text=df_p_area['Valor'].round(1), textposition='outside', marker_color=HEX_NAVY))
            fig_a.add_hline(y=90, line_dash="dash", line_color=HEX_RED, annotation_text="Línea Base (90%)", annotation_position="top right")
            fig_a.update_layout(yaxis_range=[0, 115], height=400, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_a, use_container_width=True)

        with c2:
            st.write("#### 2. Causa Raíz (Pareto por Criterios)")
            df_p_crit = pd.DataFrame.from_dict(criterios, orient='index', columns=['Valor']).sort_values('Valor', ascending=False).reset_index()
            # Invertimos para que el peor criterio quede en la parte superior del gráfico horizontal
            df_p_crit_h = df_p_crit.sort_values('Valor', ascending=True)
            
            fig_c = go.Figure()
            fig_c.add_trace(go.Bar(x=df_p_crit_h['Valor'], y=df_p_crit_h['index'], orientation='h', text=df_p_crit_h['Valor'].round(1), textposition='outside', marker_color=HEX_RED))
            fig_c.add_vline(x=90, line_dash="dash", line_color="black", annotation_text="Meta 90%", annotation_position="top right")
            fig_c.update_layout(xaxis_range=[0, 115], height=400, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_c, use_container_width=True)

        # Interpretador Lógico (Inteligencia del sistema)
        st.write("### 🤖 Dictamen Operativo Automatizado")
        peor_area = df_p_area.iloc[-1]['index']
        peor_valor = df_p_area.iloc[-1]['Valor']
        peor_crit = df_p_crit.iloc[-1]['index']
        
        if ico_master >= 90:
            st.success(f"**Operación Certificada:** El Índice Maestro se encuentra en {ico_master:.1f}%. Todos los departamentos están operando por encima de la línea base estipulada.")
        else:
            st.warning(f"**Alerta de Desviación:** El sistema requiere intervención. El departamento que presenta el mayor cuello de botella es **{peor_area}** con un cumplimiento del {peor_valor:.1f}%.")
            
        st.info(f"**Recomendación Consultiva:** Basado en el análisis de causa raíz, el indicador crítico que está arrastrando la métrica global hacia abajo es **'{peor_crit}'**. Se recomienda enfocar los recursos de capacitación o supervisión inmediata exclusivamente sobre este factor.")

    with t2:
        st.write("### Auditoría Individual de Calidad")
        st.markdown("Busca a un colaborador de enfermería para revisar su cumplimiento histórico en 5S y Tendido de Camas.")
        try:
            nombres = sorted(df_rop[col_enf].dropna().unique().tolist())
            sel = st.selectbox("Seleccionar Perfil:", nombres)
            df_p = df_rop[df_rop[col_enf] == sel]
            if not df_p.empty:
                col1, col2 = st.columns(2)
                col1.metric("OEE Individual (Promedio)", f"{df_p['Promedio_Total'].mean():.1f}%")
                col2.metric("Auditorías en el Registro", len(df_p))
                st.dataframe(df_p[[col_5s, col_camas, 'Promedio_Total']], use_container_width=True)
        except:
            st.warning("Historial no disponible.")

    with t3:
        st.write("### Historial de Proyectos Kaizen")
        st.markdown("Ideas de mejora continua captadas directamente de la operación.")
        st.dataframe(df_kaizen.tail(15), use_container_width=True)

    with t4:
        st.write("### Protocolo de Blindaje Legal")
        st.markdown("Checklist preventivo para auditorías de STPS, COPRISJAL y Protección Civil.")
        categorias = {
            "Riesgo Comercial y Sanitario": ["Contrato PROFECO", "Aviso Funcionamiento", "NOM-087 (RPBI)", "NOM-251 (Cocina)"],
            "Protección Civil": ["PIPC Activo", "Póliza RC", "Dictamen Estructural", "Simulacros"],
            "Riesgo Laboral (STPS)": ["NOM-035 (Psicosocial)", "NOM-019 (Comisión)", "DC-3 Habilidades"]
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
            
        porcentaje = (sum(st.session_state.checks_normas.values()) / len(st.session_state.checks_normas)) * 100
        st.write(f"#### Integridad Institucional: {int(porcentaje)}%")
        
        if porcentaje < 50:
            st.markdown("""<style>.stProgress > div > div > div > div { background-color: #ef4444; }</style>""", unsafe_allow_html=True)
        elif porcentaje < 80:
             st.markdown("""<style>.stProgress > div > div > div > div { background-color: #f59e0b; }</style>""", unsafe_allow_html=True)
        else:
             st.markdown(f"""<style>.stProgress > div > div > div > div {{ background-color: {HEX_GREEN}; }}</style>""", unsafe_allow_html=True)
        st.progress(porcentaje / 100)

    with t5:
        st.write("### Consola de Verificación de Datos")
        st.info("Estas tablas muestran la información "cruda" extraída de Google Sheets una vez que el traductor ha convertido los textos a números.")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.write("**Base de Datos: Servicios Generales**")
            st.dataframe(df_serv[[c_uni, c_bas, c_lav_r, c_lav_j, c_lim]].head(5))
            st.write("**Base de Datos: Rondas Nocturnas**")
            st.dataframe(df_ron[c_ron_list].head(5))
        with col_d2:
            st.write("**Base de Datos: Enfermería Vespertina**")
            st.dataframe(df_rop[[col_enf, c_5s, c_cam, 'Promedio_Total']].head(5))

    st.markdown("<div class='footer-watermark'>SUNHAVEN OS - MASTER SUITE BUSINESS INTELLIGENCE<br>Ing. Larry Beresford Díaz</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()