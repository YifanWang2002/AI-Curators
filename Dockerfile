FROM python:3.10

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY Recommend/ /app/Recommend/

COPY data /app/data

COPY new_data /app/new_data

COPY app.py /app/

EXPOSE 5000

CMD ["python", "app.py"]
