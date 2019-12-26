FROM python:3.7.6-slim-stretch

WORKDIR /podsnatch
ADD podsnatch.py /podsnatch
ADD requirements.txt /podsnatch

VOLUME ["/input", "/output"]

RUN apt-get update && \
    apt-get install -y libxml2-dev libxslt-dev gcc && \
    pip install -r requirements.txt

ENTRYPOINT ["python", "podsnatch.py"]
CMD ["--opml", "/input.opml", "--output-dir", "/output"]
