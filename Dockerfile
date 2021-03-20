FROM python:3.8-slim-buster

RUN apt-get update && apt-get install -y \
vim
RUN pip install --upgrade pip

ADD games /games
ADD sayings /sayings
ADD board.py board.py
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
    SAYING_DB_PORT=3306

CMD [ "python", "./main.py" ]