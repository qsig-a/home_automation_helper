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

CMD [ "python", "./main.py" ]