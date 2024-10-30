FROM python:3.10

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY Recommend/ /app/

COPY data /app/data
COPY new_data /app/new_data


EXPOSE 5000

# Run the application
CMD ["python", "artwork_recommend.py"]
