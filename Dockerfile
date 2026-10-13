FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir --no-deps basic-pitch==0.4.0
COPY riffforge riffforge
COPY tests/fixtures tests/fixtures
RUN useradd --uid 10001 --create-home riff && mkdir /data && chown riff:riff /data
ENV RIFFFORGE_DATA=/data
USER riff
CMD ["uvicorn", "riffforge.api:app", "--host", "0.0.0.0", "--port", "8400"]
