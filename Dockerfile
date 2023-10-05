FROM python:3.9
WORKDIR .
COPY ./requirements.txt .
RUN pip install -r ./requirements.txt
COPY . .
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","80"]

