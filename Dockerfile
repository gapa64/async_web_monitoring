FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app
RUN pip3 install -r /app/requirements.txt --no-cache-dir
COPY . ./

CMD ["python3", "main.py"]