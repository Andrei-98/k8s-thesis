FROM python:3.10.6

# create a working directory to make following commands simpler
WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

CMD ["python3", "-m", "test-app"] 