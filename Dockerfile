FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PORT=8080 HOST=0.0.0.0
WORKDIR /srv/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY combined.py .
COPY firewall-1-osint ./firewall-1-osint
COPY firewall-2-web ./firewall-2-web
RUN useradd --system --uid 10001 --gid 0 --no-create-home app \
 && chown -R 10001:0 /srv/app/firewall-1-osint/static/img
USER 10001
EXPOSE 8080
CMD ["python", "combined.py"]
