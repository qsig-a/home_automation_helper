FROM python:3.12.10-slim-bullseye

RUN apt-get update && apt-get install -y \
vim
RUN pip install --upgrade pip

ADD app /app
ADD requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade -r requirements.txt

CMD [ "fastapi", "run", "./app/main.py", "--port", "80" ]