### GRITS installation

This project provides installation scripts for the GRITS suite, including the 
[diagnostic-dashboard](https://github.com/ecohealthalliance/diagnostic-dashboard) 
user interface, the [grits-api](https://github.com/ecohealthalliance/grits-api) 
backend, the [girder](https://github.com/girder/girder) database, and 
all dependencies.


**Note: This repository contains git submodules that you must initialize before
deployment.**
```
git submodule init && git submodule update
```

### Configuration

Before using this repository, use [ansible-vault](http://docs.ansible.com/playbooks_vault.html) to create a secure.yml file with sensitive passwords and other information. Copy the format in secure.yml.sample.

Also, change the domains in group_vars/dev and group_vars/prod to the domains you will deploy to, and
edit the inventory.ini file to add instance ip addresses you want to deploy to.

### Deploying inside of a docker container
`ansible-playbook prod-playbook.yml -i prod-inventory.ini -c local --ask-vault-pass`


### Deploying to an AWS instance

Once you have gone through all the configuration steps run a command like this:

```
ansible-playbook site.yml -i inventory.ini --vault-password-file ~/.grits_vault_password --private-key ~/.keys/grits-dev.pem
```

Add `--extra-vars "reindex=true"` to regenerate the elasticsearch index
if it gets messed up.

For production deployments use prod-playbook.yml instead of site.yml.

We recommend a c3.xlarge ubuntu instance. 

Ansible can also provision new instances, however we haven't used this feature yet.

Helpful links:
 * http://docs.ansible.com/guide_aws.html
 * http://docs.ansible.com/intro_dynamic_inventory.html#example-aws-ec2-external-inventory-script

### Deploying to a docker container

```
ansible-playbook prod-playbook.yml -i docker-inventory.ini --vault-password-file ~/vault-password  --private-key ~/ecohealth/keys/deployment-keys/docker-ansible-deploy
```  

### License
Copyright 2016 EcoHealth Alliance

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
