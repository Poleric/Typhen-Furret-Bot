FROM python:3.12-alpine

RUN apk add --update --no-cache gcc libc-dev libffi-dev  # build wheel for cffi

WORKDIR /usr/src/app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./bot.py"]
