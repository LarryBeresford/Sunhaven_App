import qrcode
import urllib.parse
import os

# Tu enlace base exacto (sin el nombre al final)
URL_BASE = "https://docs.google.com/forms/d/e/1FAIpQLScwNo875lTmDVgdWR0nk6Jx4tgf-H59pmpffoSipz-mPLE6Ow/viewform?usp=pp_url&entry.2042218305="

# La lista maestra y limpia de los 32 residentes
residentes = [
    "Ahumada Mercado Gloria",
    "Aveleyra y Sanchez Maria Cecilia",
    "Contreras Reynoso Francisco",
    "Erbesso y Alvarado Maria Guadalupe",
    "Garibay Reyes Esperanza",
    "Gonzalez Malagon Maria del Carmen",
    "Kobayashi Zamora Antonio",
    "Landa Gonzalez Consuelo",
    "Macias Rodriguez Refugio",
    "Malfabon Fernandez Josefina",
    "Mendez Gutierrez Maria de los Angeles",
    "Michel Esparza Marina",
    "Montijo Romo Eva",
    "Moreno Rodriguez Gabriel",
    "Navarro Torres Jose Rafael",
    "Neri Garcia Alicia",
    "Neri Gutierrez Hector Alejandro",
    "Orozco Espinoza Noemi",
    "Orozco Santoyo Adriana Isabel",
    "Parra Orendain Carmen Aida",
    "Perez Sahagun Rosa",
    "Quijas Beltran Maria de Jesus",
    "Ramos Mendoza Dora Delia",
    "Reynel Cruz Dora",
    "Rodriguez Rivera Guillermo Arturo",
    "Ruvalcaba Ramirez Irma Beatriz",
    "Sahagun Frias Alicia",
    "Simon Ochoa Amalia",
    "Tinoco Martinez Soledad",
    "Torres Cuevas Antonio",
    "Villalobos Marquez Cesar Andres",
    "Izaguirre Ramirez Ana Maria"
]

def generar_qrs():
    carpeta_salida = "QRs_Residentes"
    
    # Creamos la carpeta si no existe
    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)
        
    print(f"🚀 Generando {len(residentes)} QRs de Rondines Nocturnos")
    
    for residente in residentes:
        # quote_plus convierte los espacios en el signo '+' exacto que pide Google Forms
        nombre_url = urllib.parse.quote_plus(residente)
        
        # Unimos la base del form con el nombre formateado
        enlace_final = URL_BASE + nombre_url
        
        # Configuramos y creamos el QR
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(enlace_final)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Guardamos la imagen
        nombre_archivo = f"{residente}.png"
        ruta_completa = os.path.join(carpeta_salida, nombre_archivo)
        img.save(ruta_completa)
        print(f"Generado: {nombre_archivo}")

    print(f"\n¡Éxito Total! Todos los QRs están listos en la carpeta '{carpeta_salida}'.")

if __name__ == "__main__":
    generar_qrs()