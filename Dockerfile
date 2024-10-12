FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir setuptools
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -U "ell-ai[all]"

COPY . .

CMD ["python", "gmail_categorizer.py"]
