import streamlit as st
import gspread
import json

st.title("Prueba de Conexión: Kaizen")

try:
    # --- LA MAGIA PARA LA NUBE ---
    credenciales_dict = json.loads(st.secrets["GOOGLE_JSON"])
    cliente = gspread.service_account_from_dict(credenciales_dict)

    # NOMBRE EXACTO DE TU ARCHIVO EN GOOGLE SHEETS
    nombre_del_google_sheet = "SUNHAVEN_KAIZEN (Respuestas)"
    
    documento = cliente.open(nombre_del_google_sheet)
    hoja = documento.sheet1  # Abre la primera pestaña

    # Leer todos los datos
    datos = hoja.get_all_records()
    
    st.success("[ÉXITO] ¡Conexión establecida con la nube de Sun Haven!")
    st.info(f"Se encontraron {len(datos)} respuestas de Kaizen.")
    
    if len(datos) > 0:
        st.write("--- EJEMPLO DE LA PRIMERA RESPUESTA ---")
        st.json(datos[0])

except Exception as e:
    st.error(f"[ERROR] Hubo un problema al conectar: {e}")