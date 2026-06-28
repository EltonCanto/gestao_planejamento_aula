import io
import base64
from PIL import Image, ImageDraw, ImageFont
from xhtml2pdf import pisa

def get_rotated_text_uri(text):
    # Create a temporary image to get text size
    font = ImageFont.load_default()
    
    # Calculate bounding box
    bbox = font.getbbox(text)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    
    # Add padding
    w += 4
    h += 4
    
    # Create actual image
    img = Image.new('RGBA', (w, h), (255, 255, 255, 0)) # transparent
    draw = ImageDraw.Draw(img)
    draw.text((2, 2), text, font=font, fill=(0, 0, 0))
    
    # Rotate 90 degrees
    img = img.rotate(90, expand=True)
    
    # Save to BytesIO
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    
    # Convert to base64
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

uri = get_rotated_text_uri("MATEMATICA")

html = f'''
<html><body>
<table border="1">
<tr><td><img src="{uri}" /></td><td>Some content</td></tr>
</table>
</body></html>
'''
result = io.BytesIO()
pisa.CreatePDF(io.BytesIO(html.encode('utf-8')), result)
with open('test_pil.pdf', 'wb') as f:
    f.write(result.getvalue())
