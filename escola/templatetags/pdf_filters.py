from django import template
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import os

register = template.Library()

@register.filter
def vertical_text_image(text):
    """
    Retorna uma tag <img> com o texto rotacionado e as dimensões corretas.
    Isso evita que o xhtml2pdf estique a imagem na tabela.
    """
    try:
        # Tenta carregar a fonte Arial no Windows
        font_path = "C:\\Windows\\Fonts\\arialbd.ttf" # Arial Bold para ficar igual o original
        if not os.path.exists(font_path):
            font_path = "C:\\Windows\\Fonts\\arial.ttf"
        
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, 18) # Aumentado para 18
        else:
            font = ImageFont.load_default()
            
        # Limpar o texto de <br> se houver
        text = text.replace("<br>", "\n")
        text = text.replace("\\n", "\n")  # Caso venha como literal do Django
        
        # O getbbox as vezes não lida perfeitamente com \n, melhor usar multiline_textbbox
        draw_temp = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        bbox = draw_temp.multiline_textbbox((0, 0), text, font=font, spacing=4)
        
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        # Adicionar padding
        w += 8
        h += 8
        
        # Criar a imagem com fundo transparente
        img = Image.new('RGBA', (w, h), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # Desenhar o texto (ancorado em 4, 4 por causa do padding)
        draw.multiline_text((4, 4), text, font=font, fill=(0, 0, 0), align="center", spacing=4)
        
        # Rotacionar 90 graus (positivo no PIL gira no sentido anti-horário, então o texto fica lendo de baixo pra cima)
        img = img.rotate(90, expand=True)
        
        # Salvar para base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        uri = f"data:image/png;base64,{img_str}"
        
        # A imagem foi rotacionada, então width e height invertem para a tag HTML
        from django.utils.safestring import mark_safe
        return mark_safe(f'<img src="{uri}" width="{img.width}" height="{img.height}">')
        
    except Exception as e:
        print(f"Erro ao gerar imagem vertical: {e}")
        return ""
