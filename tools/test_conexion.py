import streamlit as st
import gspread
import pandas as pd
import json

st.title("Diagnostico de Encabezados - Servicios")

try:
    # --- LA MAGIA PARA LA NUBE ---
    # En lugar de buscar un archivo físico, lee el texto del Secret de Streamlit
    credenciales_dict = json.loads(st.secrets["GOOGLE_JSON"])
    gc = gspread.service_account_from_dict(credenciales_dict)
    
    # URL de Servicios
    url_servicios = "https://docs.google.com/spreadsheets/d/1wdP3mbW_k4a90ubPG-ZQy8FvfAZiwKnhPjCj1BZHcBs/edit?usp=sharing"
    
    sh = gc.open_by_url(url_servicios)
    worksheet = sh.get_worksheet(0)
    
    df = pd.DataFrame(worksheet.get_all_records())
    
    st.write("Copia exactamente el texto que aparece aquí abajo para tus columnas de Servicios:")
    st.write(df.columns.tolist())
    
except Exception as e:
    st.error(f"Error de conexión: {e}")