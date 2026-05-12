import streamlit as st
import pandas as pd
import gspread
import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
import plotly.graph_objects as go

# ==========================================
# 0. CONFIGURACION Y SEGURIDAD
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH_CREDS = os.path.join(BASE_DIR, 'config', 'sunhaven-credentials.json')

st.set_page_config(page_title="Sunhaven | Operational Intelligence", layout="wide", initial_sidebar_state="expanded")

# --- DISEÑO CORPORATIVO (MINIMALISTA) ---
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
    
    .metric-label { 
        font-size: 12px; color: #64748b; font-weight: 700; 
        margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;
    }
    
    .metric-value { font-size: 34px; font-weight: 800; color: #0f172a; margin: 0; }
    
    .footer-watermark { 
        text-align: center; margin-top: 80px; opacity: 0.3; 
        font-size: 11px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px; background-color: #f1f5f9; border-radius: 4px;
        padding: 10px 20px; font-weight: 600; color: #475569;
    }
    .stTabs [aria-selected="true"] { background-color: #1e293b !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

HEX_NAVY = "#1e293b"
HEX_SLATE = "#64748b"
HEX_RED = "#dc2626"
HEX_GREEN = "#16a34a"

# --- REGLAS DE NEGOCIO (ROLES NOCTURNOS) ---
ENFERMERAS_ROL_A = ["Consuelo Ceja Liborio", "Jaqueline Hernández Sosa"] # L-M-V
ENFERMERAS_ROL_B = ["Silvia Rodríguez Reynaga", "Guadalupe Georgia Lopez Ceja"] # M-J-S

# ==========================================
# 1. MOTOR DE DATOS
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
        st.error(f"Falla de conexion con el servidor de datos: {e}")
        st.stop()

# ==========================================
# 2. INTERFAZ Y PROCESAMIENTO
# ==========================================
def main():
    # Sidebar
    with st.sidebar:
        st.markdown("### SISTEMA OPERATIVO SUNHAVEN")
        st.divider()
        if st.button("Sincronizar Base de Datos", use_container_width=True):
            cargar_datos_maestros.clear()
            st.rerun()
            
        # Filtro de fechas maestro
        fechas = st.date_input("Periodo Analizado", [datetime.now() - timedelta(days=30), datetime.now()])
        if len(fechas) != 2:
            st.warning("Seleccione una fecha de inicio y fin válidas.")
            st.stop()
        fecha_inicio, fecha_fin = fechas
        
        st.divider()
        st.markdown("### GENERACION DE REPORTES")
        if st.button("Reporte de Operaciones (PDF)", use_container_width=True):
            st.info("Procesando script de operaciones...")
            try:
                subprocess.run([sys.executable, os.path.join(BASE_DIR, 'tools', 'bot_operaciones.py')], check=True)
                st.success("Reporte generado exitosamente.")
            except: st.error("Error al ejecutar bot_operaciones.py")
            
        if st.button("Reporte Kaizen (PDF)", use_container_width=True):
            try:
                subprocess.run([sys.executable, os.path.join(BASE_DIR, 'tools', 'bot_kaizen.py')], check=True)
                st.success("Reporte Kaizen generado.")
            except: st.error("Error al ejecutar bot_kaizen.py")
            
        if st.button("Reporte Rondines (PDF)", use_container_width=True):
            try:
                subprocess.run([sys.executable, os.path.join(BASE_DIR, 'tools', 'auditor_rondines.py')], check=True)
                st.success("Reporte Rondines generado.")
            except: st.error("Error al ejecutar auditor_rondines.py")

    # Carga de datos
    data = cargar_datos_maestros()
    df_ron, df_rop, df_serv, df_kaizen = data["n"].copy(), data["v"].copy(), data["s"].copy(), data["k"].copy()

    try:
        def traducir(serie):
            mapeo = {'sí': 10, 'si': 10, 'no': 0, 'cumple': 10, 'no cumple': 0, 'separada': 10, 'bien': 10, 'ok': 10, 'limpio': 10, 'sucio': 0}
            return pd.to_numeric(serie.astype(str).str.strip().str.lower().replace(mapeo), errors='coerce') * 10

        # --- PROCESAMIENTO VESPERTINO Y SERVICIOS ---
        c_5s = [c for c in df_rop.columns if "Orden" in c][0]
        c_cam = [c for c in df_rop.columns if "Tendido" in c][0]
        col_enf = [c for c in df_rop.columns if "enfermera" in c.lower()][0]

        c_uni = [c for c in df_serv.columns if "uniforme" in c.lower()][0]
        c_bas = [c for c in df_serv.columns if "basura" in c.lower()][0]
        c_lav_r = [c for c in df_serv.columns if "ropa" in c.lower() or "separad" in c.lower()][0]
        c_lav_j = [c for c in df_serv.columns if "jabón" in c.lower() or "jabon" in c.lower()][0]
        c_lim = [c for c in df_serv.columns if "zonas asignadas" in c.lower()][0]

        for c in [c_5s, c_cam]: df_rop[c] = traducir(df_rop[c])
        df_rop['Promedio_Total'] = (df_rop[c_5s] + df_rop[c_cam]) / 2

        for c in [c_uni, c_bas, c_lav_r, c_lav_j, c_lim]: df_serv[c] = traducir(df_serv[c])

        # --- PROCESAMIENTO INTELIGENTE DE RONDAS NOCTURNAS ---
        # 1. Calcular los turnos obligatorios en el rango de fechas seleccionado
        turnos_rol_A = 0
        turnos_rol_B = 0
        dia_actual = fecha_inicio
        while dia_actual <= fecha_fin:
            if dia_actual.weekday() in [0, 2, 4]: turnos_rol_A += 1
            elif dia_actual.weekday() in [1, 3, 5]: turnos_rol_B += 1
            dia_actual += timedelta(days=1)

        # 2. Limpiar y filtrar la base de datos de rondines
        df_ron['Marca temporal'] = pd.to_datetime(df_ron['Marca temporal'], dayfirst=True, errors='coerce')
        df_ron = df_ron.dropna(subset=['Marca temporal'])
        
        # Ajustar fecha del turno (los de madrugada pertenecen a la noche anterior)
        df_ron['Fecha_Turno'] = df_ron['Marca temporal'].apply(
            lambda x: x.date() if x.hour >= 12 else (x - pd.Timedelta(days=1)).date()
        )
        
        # Filtrar por el rango de fechas de la interfaz
        df_ron = df_ron[(df_ron['Fecha_Turno'] >= fecha_inicio) & (df_ron['Fecha_Turno'] <= fecha_fin)]
        
        # Clasificar bloques horarios validos
        def asignar_bloque(h):
            if 21 <= h <= 23: return "11 PM"
            elif 0 <= h <= 3: return "2 AM"
            elif 4 <= h <= 6: return "5 AM"
            return "Otro"
        
        df_ron['Bloque_Horario'] = df_ron['Marca temporal'].dt.hour.apply(asignar_bloque)
        
        # Excluir domingos (weekday=6) y bloques no válidos
        df_ron_valid = df_ron[(df_ron['Bloque_Horario'] != "Otro") & (df_ron['Fecha_Turno'].apply(lambda d: d.weekday()) != 6)]
        
        # Agrupar escaneos únicos
        if not df_ron_valid.empty and 'Enfermera' in df_ron_valid.columns:
            rondas_por_enf = df_ron_valid[['Enfermera', 'Fecha_Turno', 'Bloque_Horario']].drop_duplicates().groupby('Enfermera').size()
        else:
            rondas_por_enf = {}

        # Calcular cumplimiento individual nocturno
        porcentajes_nocturnos = {}
        ENFERMERAS_NOCHE = ENFERMERAS_ROL_A + ENFERMERAS_ROL_B
        
        for enf in ENFERMERAS_NOCHE:
            if enf in ENFERMERAS_ROL_A: turnos = turnos_rol_A
            elif enf in ENFERMERAS_ROL_B: turnos = turnos_rol_B
            else: turnos = 0
            
            meta_rondas = turnos * 3
            realizadas = rondas_por_enf.get(enf, 0)
            
            if meta_rondas == 0:
                pct = 100.0 # Si seleccionaron un solo día y no le tocaba turno, no se penaliza
            else:
                pct = min((realizadas / meta_rondas) * 100, 100.0)
                
            porcentajes_nocturnos[enf] = pct

        val_nocturno = sum(porcentajes_nocturnos.values()) / len(porcentajes_nocturnos) if porcentajes_nocturnos else 0

        # --- CALCULOS MAESTROS DE OEE ---
        val_vespertino = (df_rop[c_5s].mean() + df_rop[c_cam].mean()) / 2
        val_cocina = (df_serv[c_uni].mean() + df_serv[c_bas].mean()) / 2
        val_lavanderia = (df_serv[c_lav_r].mean() + df_serv[c_lav_j].mean()) / 2
        val_limpieza = df_serv[c_lim].mean()

        areas_kpi = {
            "Enfermería Nocturna": val_nocturno,
            "Enfermería Vespertina": val_vespertino,
            "Cocina": val_cocina,
            "Lavandería": val_lavanderia,
            "Limpieza General": val_limpieza
        }
        areas_kpi = {k: (v if pd.notna(v) else 0) for k, v in areas_kpi.items()}
        ico_master = sum(areas_kpi.values()) / len(areas_kpi) if areas_kpi else 0

        # Desglose para Pareto
        criterios_all = {
            "Uniforme (Cocina)": df_serv[c_uni].mean(),
            "Basura (Cocina)": df_serv[c_bas].mean(),
            "Ropa (Lavandería)": df_serv[c_lav_r].mean(),
            "Insumos (Lavandería)": df_serv[c_lav_j].mean(),
            "Zonas Comunes": df_serv[c_lim].mean(),
            "Orden de Roperos": df_rop[c_5s].mean(),
            "Calidad de Tendido": df_rop[c_cam].mean(),
            "Cumplimiento Rondines Nocturnos": val_nocturno # El KPI nocturno como causa raíz consolidada
        }
        criterios_all = {k: (v if pd.notna(v) else 0) for k, v in criterios_all.items()}

    except Exception as e:
        st.error(f"Error en el procesamiento de indicadores: {e}")
        ico_master = 0

    # --- ENCABEZADO ---
    status_color = HEX_GREEN if ico_master >= 90 else HEX_RED
    status_txt = "OPERACION DENTRO DE NORMA" if ico_master >= 90 else "ACCION CORRECTIVA REQUERIDA"

    st.markdown(f"""<div class='exec-header'>
        <div><p style='margin:0; font-weight:700; color:#64748b; font-size:12px; letter-spacing:1px; text-transform:uppercase;'>Estatus Institucional</p>
        <h2 style='margin:0; color:{status_color};'>{status_txt}</h2></div>
        <div style='text-align:right;'><p style='margin:0; font-weight:700; color:#64748b; font-size:12px; letter-spacing:1px; text-transform:uppercase;'>ICO Maestro</p>
        <h1 style='margin:0; font-size:48px;'>{ico_master:.1f}%</h1></div>
    </div>""", unsafe_allow_html=True)

    # --- TABS ---
    tabs = st.tabs(["Tablero de Control", "Rendimiento Individual", "Gestion Kaizen", "Cumplimiento Legal", "Auditoria de Datos"])

    with tabs[0]:
        cols = st.columns(5)
        for i, (area, valor) in enumerate(areas_kpi.items()):
            with cols[i]:
                st.markdown(f"""<div class='kpi-card'>
                    <p class='metric-label'>{area}</p>
                    <p class='metric-value'>{valor:.1f}%</p>
                </div>""", unsafe_allow_html=True)

        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("### Desempeño por Area")
            df_a = pd.DataFrame.from_dict(areas_kpi, orient='index', columns=['V']).sort_values('V', ascending=False).reset_index()
            fig_a = go.Figure()
            fig_a.add_trace(go.Bar(x=df_a['index'], y=df_a['V'], text=df_a['V'].round(1), textposition='outside', marker_color=HEX_NAVY))
            fig_a.add_hline(y=90, line_dash="dash", line_color="red", annotation_text="Meta 90%")
            fig_a.update_layout(yaxis_range=[0, 115], height=400, margin=dict(t=20, b=20, l=20, r=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_a, use_container_width=True)

        with c2:
            st.write("### Analisis de Causa Raiz")
            df_c = pd.DataFrame.from_dict(criterios_all, orient='index', columns=['V']).sort_values('V', ascending=True).reset_index()
            fig_c = go.Figure()
            fig_c.add_trace(go.Bar(x=df_c['V'], y=df_c['index'], orientation='h', text=df_c['V'].round(1), textposition='outside', marker_color=HEX_RED))
            fig_c.add_vline(x=90, line_dash="dash", line_color="black")
            fig_c.update_layout(xaxis_range=[0, 115], height=500, margin=dict(t=20, b=20, l=20, r=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_c, use_container_width=True)

        st.write("### Dictamen Ejecutivo")
        if ico_master < 90:
            peor_a = df_a.iloc[-1]['index']
            peor_c = df_c.iloc[0]['index']
            st.warning(f"La eficiencia global se encuentra comprometida principalmente por el area de {peor_a}. El analisis de causa raiz identifica que el criterio '{peor_c}' es la principal desviacion del sistema.")
        else:
            st.success("La infraestructura operativa de Sunhaven cumple con los estandares de alta direccion. Se recomienda mantener los ciclos de auditoria actuales.")

    with tabs[1]:
        st.write("### Evaluacion Integral de Staff (Diurno y Nocturno)")
        
        # Consolidar nombres de todas las bases de datos de enfermería
        nombres_dia = set(df_rop[col_enf].dropna().unique()) if not df_rop.empty else set()
        nombres_noche = set(df_ron_valid['Enfermera'].dropna().unique()) if not df_ron_valid.empty else set()
        todos_nombres = sorted(list(nombres_dia.union(nombres_noche).union(set(ENFERMERAS_NOCHE))))
        
        sel = st.selectbox("Seleccionar Colaborador(a):", todos_nombres)
        
        c_i1, c_i2 = st.columns(2)
        
        # --- DESEMPEÑO DE DÍA ---
        df_p_dia = df_rop[df_rop[col_enf] == sel] if not df_rop.empty else pd.DataFrame()
        if not df_p_dia.empty:
            c_i1.metric("Cumplimiento Vespertino (5S / Camas)", f"{df_p_dia['Promedio_Total'].mean():.1f}%")
            with c_i1.expander("Ver Historial Vespertino", expanded=False):
                st.dataframe(df_p_dia[[c_5s, c_cam, 'Promedio_Total']], use_container_width=True)
        else:
            c_i1.metric("Cumplimiento Vespertino", "No aplica")
            
        # --- DESEMPEÑO DE NOCHE ---
        if sel in porcentajes_nocturnos:
            c_i2.metric("Cumplimiento Nocturno (Rondines)", f"{porcentajes_nocturnos[sel]:.1f}%")
            with c_i2.expander("Ver Historial de Escaneos QR", expanded=False):
                df_p_noche = df_ron_valid[df_ron_valid['Enfermera'] == sel].copy()
                if not df_p_noche.empty:
                    df_p_noche['Hora_Escaneo'] = df_p_noche['Marca temporal'].dt.strftime('%H:%M:%S')
                    st.dataframe(df_p_noche[['Fecha_Turno', 'Hora_Escaneo', 'Bloque_Horario', 'Nombre del Residente']], use_container_width=True)
                else:
                    st.info("No hay registros de escaneo para este periodo.")
        else:
            c_i2.metric("Cumplimiento Nocturno", "No aplica")

    with tabs[2]:
        st.write("### Propuestas de Mejora Continua")
        st.dataframe(df_kaizen.tail(15), use_container_width=True)

    with tabs[3]:
        st.write("### Checklist Normativo")
        st.info("Estatus preventivo de blindaje institucional ante autoridades gubernamentales.")
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
        st.progress(porcentaje / 100)

    with tabs[4]:
        st.write("### Auditoria de Tuberias de Datos")
        st.info('Estas tablas muestran la información "cruda" extraída de Google Sheets.')
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.write("**Base: Servicios y Ropa**")
            st.dataframe(df_serv.head(10))
            st.write("**Base: Rondines Nocturnos (Cruda)**")
            st.dataframe(df_ron.head(10))
        with col_d2:
            st.write("**Base: Enfermeria (Dia)**")
            st.dataframe(df_rop.head(10))

    st.markdown("<div class='footer-watermark'>Sunhaven Intelligence Suite - Enterprise Edition</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()