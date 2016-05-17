FROM ubuntu:14.04.3

# Replace shell with bash so we can source files
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Set debconf to run non-interactively
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

#Install apt package dependencies
RUN apt-get update && apt-get -y install lsb-release &&\
    echo "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) main universe" >> /etc/apt/sources.list &&\
    echo "deb http://repo.mongodb.org/apt/ubuntu trusty/mongodb-org/3.2 multiverse" > /etc/apt/sources.list.d/mongodb-org-3.2.list &&\
    apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv EA312927 &&\
    apt-get update &&\
    apt-get -y install less vim python-pip python-dev git sudo mongodb-org-shell libffi-dev libssl-dev &&\
    apt-get clean all &&\
    pip install ansible markupsafe

EXPOSE 80
EXPOSE 25
ADD run.sh /run.sh
CMD /bin/bash /run.sh

