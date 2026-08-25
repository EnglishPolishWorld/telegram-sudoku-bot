FROM python:3.13-slim

WORKDIR /app
COPY . .

ENV PYTHONUNBUFFERED=1
CMD ["python", "bot.py"]

