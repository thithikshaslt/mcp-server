FROM python:3.11


WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . /app/

CMD ["sh", "-c", "python auth_server.py & python seller_server.py & python buyer_server.py"]