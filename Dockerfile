FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

ARG PIP_INDEX_URL=https://pypi.org/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --prefer-binary --retries 20 --timeout 180 -r /app/requirements.txt

COPY . /app

RUN mkdir -p /app/log /app/temp

EXPOSE 9000

CMD ["python3", "www/app.py"]
