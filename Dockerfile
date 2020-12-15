FROM python:3.8

WORKDIR /wav2vec-infer

COPY requirements.txt .

RUN pip install -r requirements.txt

RUN mkdir wav2vec

RUN mkdir inference-client

COPY wav2vec/ wav2vec/

COPY inference-client/ inference-client/

COPY generate_model_dict.py .

COPY init.sh .

RUN sh init.sh

EXPOSE 9008




