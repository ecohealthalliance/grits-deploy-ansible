#!/bin/bash
# Purpose: This shell script will eventually be called in the container running the full grits api
# The logic in this script is intneded to ensure supervisor and all of its processes run correctly

#Fork supervisord to the background for now
supervisord --nodaemon --config /etc/supervisor/supervisord.conf &

#Check to see if mongo is loaded yet
mongo --eval "db.local.findOne()"
return_code=$?

#While loop to wait for mongo to come up
while [[ $return_code != 0 ]]; do
  echo "Sleeping for an additional 30 seconds to allow mongo to finish loading"
  sleep 30
  mongo --eval "db.local.findOne()"
  return_code=$?
done

#Start gritsapi services only after mongo is up
supervisorctl start gritsapigroup:

#Bring supervisor back to the foreground. We need this here for the docker container to run properly
fg
