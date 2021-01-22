FROM python:3.8

WORKDIR /wav2vec-infer

COPY requirements.txt .

RUN pip install -r requirements.txt

RUN mkdir wav2vec

RUN mkdir inference-client

COPY wav2vec/ wav2vec/

COPY inference-client/ inference-client/

COPY generate_model_dict.py .

COPY monitor_and_upload_to_bucket.py .

COPY upload_to_google.py .

COPY start_inference_service.py .

COPY init.sh .

COPY deployed_models/ deployed_models/

RUN sh init.sh

EXPOSE 9008




