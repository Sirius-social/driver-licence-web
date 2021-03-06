FROM python:3.8

COPY app /app
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt && \
    chmod +x /app/wait-for-it.sh && \
    chmod +x /app/run_tests.sh

WORKDIR /app
ENV PYTHONPATH=/app:$PYTHONPATH

ENV DJANGO_SETTINGS_MODULE='settings.production'

HEALTHCHECK --interval=30s --timeout=15s --start-period=30s --retries=2 \
  CMD curl -f http://localhost/check_health || exit 1

# FIRE!!!
CMD echo "Wait database is ready" && /app/wait-for-it.sh ${DATABASE_HOST}:${DATABASE_PORT-5432} --timeout=60 && \
  cd /app && \
  echo "Database migration" && python manage.py migrate && \
  echo "Run services" && (python manage.py run_ssi_police & python manage.py run_ssi_carsharing & python manage.py run_ssi_gov & python manage.py run_ssi_driving_school & uvicorn settings.asgi:application --reload --port=80 --host=0.0.0.0)
