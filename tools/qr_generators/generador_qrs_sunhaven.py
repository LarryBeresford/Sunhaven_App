import qrcode
from PIL import Image, ImageDraw, ImageFont
import os

enlace_semilla = "https://docs.google.com/forms/d/e/1FAIpQLScfT7XBjHsb96zMU16TLIi19W0-oOnBb5RnEC897yraS7UaaA/viewform?usp=pp_url&entry.1093011749=ID_AQUI"
total_roperos = 28
PAGE_W, PAGE_H = 2550, 3300
COLS, ROWS = 2, 4 
CELL_W, CELL_H = PAGE_W // COLS, PAGE_H // ROWS
QR_SIZE = 600 

def generar_planillas():
    pages = []
    current_page = Image.new('RGB', (PAGE_W, PAGE_H), 'white')
    draw = ImageDraw.Draw(current_page)
    
    for i in range(1, total_roperos + 1):
        idx_in_page = (i - 1) % (COLS * ROWS)
        if idx_in_page == 0 and i > 1:
            pages.append(current_page)
            current_page = Image.new('RGB', (PAGE_W, PAGE_H), 'white')
            draw = ImageDraw.Draw(current_page)
            
        id_rop = f"ROP-{i:02d}"
        url_final = enlace_semilla.replace("ID_AQUI", id_rop)
        
        qr = qrcode.QRCode(box_size=15, border=2)
        qr.add_data(url_final)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        img_qr = img_qr.resize((QR_SIZE, QR_SIZE))
        
        col = idx_in_page % COLS
        row = idx_in_page // COLS
        x = col * CELL_W + (CELL_W - QR_SIZE) // 2
        y = row * CELL_H + (CELL_H - QR_SIZE) // 2 - 50
        
        current_page.paste(img_qr, (x, y))
        try:
            font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 60)
        except:
            font = ImageFont.load_default()
            
        text_bbox = draw.textbbox((0, 0), id_rop, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        draw.text((x + (QR_SIZE - text_w) // 2, y + QR_SIZE + 20), id_rop, fill="black", font=font)
        
    pages.append(current_page)
    
    # --- LA SOLUCIÓN ANTI-ERRORES ---
    for idx, page in enumerate(pages):
        nombre_archivo = f"Planilla_Pagina_{idx+1}.png"
        page.save(nombre_archivo, "PNG")
        
    print(f"¡Éxito total! Se generaron {len(pages)} páginas listas para imprimir.")

generar_planillas()