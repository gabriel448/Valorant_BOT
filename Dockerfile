# 1. Pega uma versão oficial do Python 3.11
FROM python:3.11-slim

# 2. Define a pasta principal dentro do servidor
WORKDIR /app

#pra ver os prints do python
ENV PYTHONUNBUFFERED=1

# 3.Instala fontes de texto no Linux
RUN apt-get update && apt-get install -y fonts-liberation && rm -rf /var/lib/apt/lists/*

# 4. Copia a lista de bibliotecas para dentro do container
COPY requirements.txt .

# 5. Manda o Python instalar tudo que o bot precisa
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copia todos os códigos (main.py, banco.py, .env, etc) para lá
COPY . .

CMD ["python", "main.py"]