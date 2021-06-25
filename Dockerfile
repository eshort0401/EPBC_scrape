FROM continuumio/miniconda3
COPY epbc_docker.yml /
RUN conda env create -f epbc_docker.yml
# Pull the environment name out of the environment.yml
RUN echo "source activate epbc" > ~/.bashrc
ENV PATH /opt/miniconda/envs/epbc_docker/bin:$PATH
