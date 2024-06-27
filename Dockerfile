FROM python:3.12-alpine

ARG TARGETARCH

RUN if [ $TARGETARCH = "arm64" ]; then \
      apk add --update --no-cache gcc libc-dev libffi-dev \
    ; fi

WORKDIR /usr/src/app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./bot.py"]
