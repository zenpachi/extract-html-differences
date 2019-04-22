FROM python:3.7.3-slim

RUN pip3 install --upgrade beautifulsoup4==4.6.3 \
    pandas==0.23.4 \
    html5lib==1.0.1

COPY ./app/app.py /app/app.py
COPY ./app/template_page.html /app/template_page.html
COPY ./app/template_index.html /app/template_index.html
WORKDIR /app

CMD ["python", "app.py"]
