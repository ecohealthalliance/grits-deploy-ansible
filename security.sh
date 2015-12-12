#!/bin/bash
#Purpose: This script is meant to run inside of a docker container in order to strip out sensitive info right before shipping off to digital infuzion

#Get rid of SSH server and any keys
rm -fr /root/.ssh
rm -fr /home/grits/.ssh
apt-get -y purge openssh-server

