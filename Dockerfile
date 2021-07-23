# Specify base image
FROM continuumio/miniconda3

# Specify image location of volume to store PDF and CSV files
VOLUME ["/EPBC_files"]

# Setup conda
COPY . /EPBC_src/
RUN conda env create -f /EPBC_src/epbc_docker.yml
RUN echo "conda activate epbc_docker" >> ~/.bashrc
SHELL ["/bin/bash", "--login", "-c"]

# Setup Chrome
RUN apt-get update
RUN apt update
ARG CHROME_VERSION="91.0.4472.114-1"
RUN wget --no-verbose -O /tmp/chrome.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}_amd64.deb
RUN apt install -y /tmp/chrome.deb
RUN rm /tmp/chrome.deb

# Setup Chromedriver
RUN apt-get install unzip
RUN wget --no-verbose -O /tmp/chromedriver_linux64.zip https://chromedriver.storage.googleapis.com/91.0.4472.101/chromedriver_linux64.zip
RUN unzip /tmp/chromedriver_linux64.zip -d /usr/bin

# Install Ghostscript
RUN apt-get install -y ghostscript-x

# Setup user for container
ARG USER_ID
ARG GROUP_ID
RUN groupadd -r -g $GROUP_ID EPBC_scrape
RUN useradd --no-log-init -r -g EPBC_scrape -u $USER_ID EPBC_scrape
USER EPBC_scrape

# Code to run when container initialised
ENTRYPOINT ["/EPBC_src/entrypoint.sh"]
