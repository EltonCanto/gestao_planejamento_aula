import io
from xhtml2pdf import pisa

html = '''
<html><body>
<div style="transform: rotate(-90deg);">TEST VERTICAL</div>
</body></html>
'''
result = io.BytesIO()
pisa.CreatePDF(io.BytesIO(html.encode('utf-8')), result)
with open('test_vertical.pdf', 'wb') as f:
    f.write(result.getvalue())
