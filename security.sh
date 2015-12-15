#!/bin/bash
#Purpose: This script is meant to run inside of a docker container in order to strip out sensitive info right before shipping off to digital infuzion

#Remove AWS creds from grits-api/config.py
sed -i "s/aws_access_key \= '.*'//" /home/grits/grits-api/config.py
sed -i "s/aws_secret_key \= '.*'//" /home/grits/grits-api/config.py

#Remove BSVE creds/config info from grits-api/config.py
sed -i "s/bsve_endpoint \= '.*'/bsve_endpoint \= ''/" /home/grits/grits-api/config.py
sed -i "s/bsve_user_name \= '.*'/bsve_user_name = ''/" /home/grits/grits-api/config.py
sed -i "s/bsve_api_key \= '.*'/bsve_api_key = ''/" /home/grits/grits-api/config.py
sed -i "s/bsve_secret_key \= '.*'/bsve_secret_key = ''/" /home/grits/grits-api/config.py









#Get rid of SSH server and any keys (Must stay as last task)
rm -fr /root/.ssh
rm -fr /home/grits/.ssh
apt-get -y purge openssh-server

