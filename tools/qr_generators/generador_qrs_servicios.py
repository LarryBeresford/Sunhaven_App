import qrcode
from PIL import Image, ImageDraw, ImageFont
import urllib.parse

# Tu enlace semilla
base_url = "https://docs.google.com/forms/d/e/1FAIpQLSf-uU63wGDWaRkU_KU_LDEL1k3c94QxhSFUvAzETuwNVqVBJQ/viewform?usp=pp_url&entry.857301786="

# Las áreas exactas
areas = ["Cocina", "Lavandería", "Limpieza"]

def generar_qrs_servicios():
    print("Iniciando generación de QRs para Servicios...")
    
    for area in areas:
        # Codificamos el texto para que Google Forms lea bien el acento de Lavandería
        area_url_encoded = urllib.parse.quote(area)
        url_final = base_url + area_url_encoded
        
        # Generar QR
        qr = qrcode.QRCode(box_size=20, border=2)
        qr.add_data(url_final)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        
        # Crear base con espacio extra para el texto
        img_w, img_h = img_qr.size
        fondo = Image.new('RGB', (img_w, img_h + 120), 'white')
        fondo.paste(img_qr, (0, 0))
        
        # Añadir el título debajo
        draw = ImageDraw.Draw(fondo)
        try:
            font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 80)
        except:
            font = ImageFont.load_default()
            
        text_bbox = draw.textbbox((0, 0), area, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        draw.text(((img_w - text_w) // 2, img_h + 20), area, fill="black", font=font)
        
        # Guardar la imagen (quitamos el acento solo para el nombre del archivo en tu Mac)
        nombre_archivo = f"QR_{area.replace('í', 'i')}_Sunhaven.png"
        fondo.save(nombre_archivo)
        print(f"✅ Listo: {nombre_archivo}")

generar_qrs_servicios()