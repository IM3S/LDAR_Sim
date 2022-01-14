FROM soroushojagh/lds:base
# load customized base image from hub
ENV PYTHONUNBUFFERED 1
WORKDIR /code/
COPY . /code/
RUN echo "conda activate ldar_sim_env" >> ~/.bashrc
# COPY requirements.txt /code/
# RUN pip install -r /code/LDAR_Sim/install/requirements.txt
## COPY docker-entrypoint ##
COPY docker-entrypoint.sh /docker-entrypoint.sh
## set RUN permission to docker-entrypoint ##
RUN chmod +x /docker-entrypoint.sh