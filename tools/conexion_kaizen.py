import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. Configurar los permisos
alcance = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

# 2. Conectar usando tu archivo .json
credenciales = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', alcance)
cliente = gspread.authorize(credenciales)

print("Intentando conectar con Google Sheets...")

try:
    # 3. PON AQUÍ EL NOMBRE EXACTO DE TU ARCHIVO EN GOOGLE SHEETS
    # Ejemplo: "Respuestas_Kaizen_Febrero"
    nombre_del_google_sheet = "SUNHAVEN_KAIZEN (Respuestas)"
    
    documento = cliente.open(nombre_del_google_sheet)
    hoja = documento.sheet1  # Abre la primera pestaña

    # 4. Leer todos los datos
    datos = hoja.get_all_records()
    
    print("[ÉXITO] ¡Conexión establecida con la nube de Sun Haven!")
    print(f"Se encontraron {len(datos)} respuestas de Kaizen.")
    
    if len(datos) > 0:
        print("\n--- EJEMPLO DE LA PRIMERA RESPUESTA ---")
        print(datos[0])

except Exception as e:
    print(f"[ERROR] Hubo un problema al conectar: {e}")