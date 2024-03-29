FROM python:3.11-slim-buster

RUN apt-get update && apt-get install -y \
vim
RUN pip install --upgrade pip

ADD games /games
ADD sayings /sayings
ADD connectors /connectors
ADD main.py main.py
ADD requirements.txt requirements.txt

RUN pip install -r requirements.txt

ENV PORT=8323 \
    VESTABOARD_API_KEY=changeme \
    VESTABOARD_API_SECRET=changeme \
    SAYING_DB_ENABLE=0 \
    SAYING_DB_USER=changeme \
    SAYING_DB_PASS=changeme \
    SAYING_DB_HOST=changeme \
    SAYING_DB_NAME=changeme \
    SAYING_DB_PORT=3306 \
    OC_ENABLE=0 \
    OCTRANSPO_APIKEY=changeme \
    OCTRANSPO_APPID=changeme

CMD [ "python", "./main.py" ]