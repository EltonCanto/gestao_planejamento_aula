# Usa a versão leve oficial do Python
FROM python:3.11-slim

# Impede o Python de gravar arquivos .pyc e força os logs para stdout (bom para Docker)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Define o diretório de trabalho no container
WORKDIR /app

# Instala dependências nativas necessárias para algumas bibliotecas Python (ex: reportlab)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    tesseract-ocr \
    tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

# Copia apenas os requirements primeiro (para cachear a camada do pip se o código mudar)
COPY requirements-prod.txt /app/

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copia o restante do código da aplicação
COPY . /app/

# Garante permissões adequadas nos diretórios que precisam de escrita
RUN mkdir -p /app/staticfiles /app/media \
    && chmod -R 777 /app/media /app/staticfiles

# Cria um usuário não privilegiado para rodar a aplicação por segurança (best practice)
RUN adduser --disabled-password --no-create-home appuser \
    && chown -R appuser:appuser /app

# Troca para o usuário criado
USER appuser

# Expõe a porta que o Gunicorn vai rodar
EXPOSE 8000

# O comando para iniciar o servidor (pode ser sobrescrito pelo entrypoint)
# Gunicorn com 3 workers (boa prática = (2 x $num_cores) + 1)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "core.wsgi:application"]
