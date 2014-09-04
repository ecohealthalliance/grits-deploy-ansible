# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "ubuntu/trusty64"

  config.vm.provider "virtualbox" do |v|
    v.memory = 4096
    v.cpus = 2
  end

  config.vm.network "private_network", ip: "192.168.15.10"
  config.vm.hostname = "grits.vm"

  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "site.yml"
    ansible.vault_password_file = "~/.grits_vault_password"
    ansible.verbose = "v"
  end
end
