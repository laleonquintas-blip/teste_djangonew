# Usa uma versão leve do Python Linux
FROM python:3.13-slim

# Evita que o Python gere arquivos de cache (.pyc)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Define a pasta de trabalho dentro do container
WORKDIR /app

# Instala as dependências do sistema necessárias para o Postgres
RUN apt-get update && apt-get install -y libpq-dev gcc

# Copia o arquivo de requisitos e instala
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o projeto para dentro do container
COPY . /app/

# Libera a porta 8000
EXPOSE 8000

# Comando para rodar o servidor Gunicorn
CMD ["gunicorn", "teste_django.wsgi:application", "--bind", "0.0.0.0:8000"]