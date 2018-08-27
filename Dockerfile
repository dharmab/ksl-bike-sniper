FROM python:3.7-alpine

WORKDIR /app

ADD requirements.txt /app/
RUN pip install -r requirements.txt

ADD templates /app/templates
ADD sniper.py /app/
CMD python3 sniper.py
