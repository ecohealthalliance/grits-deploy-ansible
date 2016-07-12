#!/bin/bash
#Purpose: This script is meant to run inside of a docker container in order to strip out sensitive info right before shipping off to digital infuzion

#Find grits home directory
export GRITS_HOME=$(grep grits /etc/passwd | awk -F":" '{print $6}')

#Remove AWS creds from grits-api/config.py
sed -i "s/aws_access_key \= '.*'//" $GRITS_HOME/grits-api/config.py
sed -i "s/aws_secret_key \= '.*'//" $GRITS_HOME/grits-api/config.py

#Remove our grits api key
sed -i "s/grits28754//" $GRITS_HOME/grits-api/config.py

#Remove BSVE creds/config info from grits-api/config.py
sed -i "s/bsve_endpoint \= '.*'/bsve_endpoint \= ''/" $GRITS_HOME/grits-api/config.py
sed -i "s/bsve_user_name \= '.*'/bsve_user_name = ''/" $GRITS_HOME/grits-api/config.py
sed -i "s/bsve_api_key \= '.*'/bsve_api_key = ''/" $GRITS_HOME/grits-api/config.py
sed -i "s/bsve_secret_key \= '.*'/bsve_secret_key = ''/" $GRITS_HOME/grits-api/config.py

#Remove girder admin password
sed -i "s/GIRDER_ADMIN_PASSWORD=\".*\"/GIRDER_ADMIN_PASSWORD=\"\"/" $GRITS_HOME/grits_config

#Remove CLASSIFIER_DATA access key and secret key from grits/grits_config
sed -i "s/CLASSIFIER_DATA_ACCESS_KEY\=".*"//" $GRITS_HOME/grits_config
sed -i "s/CLASSIFIER_DATA_SECRET_KEY\=".*"//" $GRITS_HOME/grits_config

#Remove GIRDER_DATA access key and scret key from grits/grits_config
sed -i "s/GIRDER_DATA_ACCESS_KEY\=".*"//" $GRITS_HOME/grits_config
sed -i "s/GIRDER_DATA_SECRET_KEY\=".*"//" $GRITS_HOME/grits_config

#Remove bash histories
rm /root/.bash_history || echo "/root/.bash_history not found"
ln -s /dev/null /root/.bash_history
rm $GRITS_HOME/.bash_history || echo "$GRITS_HOME/.bash_history not found"
ln -s /dev/null $GRITS_HOME/.bash_history

#Remove git revision histories
find $GRITS_HOME -name .git\* -exec rm -fr {} \;

#Get rid of SSH server and any keys (Must stay as last task)
rm -fr /root/.ssh || echo "/root/.ssh not found"
rm -fr $GRITS_HOME/.ssh || echo "$GRITS_HOME/.ssh not found"
apt-get -y purge openssh-server
pkill -9 ssh

