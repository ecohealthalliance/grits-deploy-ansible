### GRITS installation

This project provides installation scripts for the GRITS suite, including the 
[diagnostic-dashboard](https://github.com/ecohealthalliance/diagnostic-dashboard) 
user interface, the [grits-api](https://github.com/ecohealthalliance/grits-api) 
backend, the [girder](https://github.com/girder/girder) database, and 
all dependencies.

### Deploying to a virtual machine

Included in this repository is everything you need to deploy the entire
grits application into a virtual machine using vagrant.  All you need
is to install [vagrant](https://www.vagrantup.com/),
[VirtualBox](https://www.virtualbox.org/), and [Ansible](http://www.ansible.com/).
The ansible apt-get package may be too out of date to run this playbook,
so the suggested method for installation is to install pip and run:
`sudo pip install paramiko PyYAML jinja2 httplib2 ansible`
Sensitive passwords and api keys are encrypted with [ansible-vault](http://docs.ansible.com/playbooks_vault.html).
You will need to obtain the vault password and put it in a file called
`~/.grits_vault_password` to run the vagrant installation.

Note: This repository contains git submodules that you must initialize before
deployment. 
```
git submodule init && git submodule update
```

To set up the virtual machine and run the deployment, just run the following
in this directory.
```
vagrant up
```

Once this is finished, you should be able to access the dashboard locally at
https://192.168.15.10/.  The girder database will be hosted at https://192.168.15.10/gritsdb/.
You can access the VM using `vagrant ssh`.  All of the grits components are
installed as user `grits`.  So to inspect the install try `sudo su - grits` inside the
VM.  Cron logs go in `/home/grits/cron/logs` by default and supervisor logs are in
`/var/log/supervisor/`.

### Deploying to an AWS instance

Create a [host inventory file](http://docs.ansible.com/intro_inventory.html)
in `/etc/ansible/hosts` with the instance's ip address.
Next run the playbook using a command like this:

```
ansible-playbook site.yml --vault-password-file ~/.grits_vault_password --private-key ~/.keys/grits-dev.pem
```

Ansible can also provision new instances, however we haven't used this feature yet.

Helpful links:
 * http://docs.ansible.com/guide_aws.html
 * http://docs.ansible.com/intro_dynamic_inventory.html#example-aws-ec2-external-inventory-script
