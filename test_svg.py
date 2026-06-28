import io
from xhtml2pdf import pisa

html = '''
<html><body>
<svg width="100" height="300">
    <text x="-200" y="50" transform="rotate(-90)" font-family="Helvetica" font-size="20">LINGUAGEM</text>
</svg>
</body></html>
'''
result = io.BytesIO()
pisa.CreatePDF(io.BytesIO(html.encode('utf-8')), result)
with open('test_svg.pdf', 'wb') as f:
    f.write(result.getvalue())
