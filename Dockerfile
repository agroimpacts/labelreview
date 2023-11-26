FROM continuumio/miniconda3:22.11.1

# Install pip, pip-tools, and setuptools
RUN pip install --no-cache-dir --upgrade pip pip-tools setuptools
RUN pip install "psycopg[binary,pool]"

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN apt-get --allow-releaseinfo-change update
RUN apt-get --allow-releaseinfo-change-suite update
RUN apt-get update
RUN mkdir /home/workdir
WORKDIR /home/workdir

EXPOSE 8888

ENTRYPOINT ["jupyter", "lab", "--ip='0.0.0.0'", "--port=8888", "--no-browser", "--allow-root"]
