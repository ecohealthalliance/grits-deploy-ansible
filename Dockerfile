FROM ubuntu:14.04.3

# Replace shell with bash so we can source files
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Set debconf to run non-interactively
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

#Install apt package dependencies
RUN echo "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) main universe" >> /etc/apt/sources.list
RUN apt-get update
RUN apt-get -y install openssh-server less vim
RUN apt-get clean all

#First time setup for ssh
RUN service ssh start
RUN ssh-keygen -b 2048 -f /root/.ssh/id_rsa -N ""
RUN echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDl5pZaFTdRGUn/QeJ5i3Doxho3q78nAHOcT0r+yAQUoqeKTpWehaXS4kDlVRd+wsUzoPBL1ufeCRSM7aYx4xUfmjyHZxlMrMVfErQGN8m4ygEBGF3w8LzN54sDcRkc4xLsMPSl++svxUSU8Jr651Poi1GlSItFSr/IV7ZWhzxC2Qq5t7/7gDrXMMIBq5+iptGWw2RWM2OwmS8dIsGZhJV1uLoO2Vlx/b3AMDG3I9g0CoFbvFW7qGJdoK+i7FfFrGgqMellQmOoZnimpi3DDw7IldMl/oS288Ya61aty7tW6S6LEZwTEh7bf+0LtEmeH54OLYrmzmHSNso4yOZBG3rAK5I6JN8YmmaP4xlGFSo/5Kr0DhfrhsZjMOVAcZEL8CU1tnVCoLp0lN/J/haUY9YGfvogATEM6mdHvVGrcvDPgsU+PvnFjcGHKWVnC5xTjvNSK28lfyrRXljlF2s+RjytVfD00njs95QeU0vIOOe+goksdjAC/s5/4JPana5P6pxVw1oGj+6ae162lFsIKbW6c+8Nm7j1zbVPx3z6rZ55XP/79XFkIsA8cNVFHf4jmYb+D5B4Dybvrh1E8+fytyIsLp99tzTXuxLkiiOLSb3JfiQtMzg+Rf1iZxRNhMCsY7qfKMiJaycYMXg9JgHXMNsY4OmAPE+f6dp+uzukUwITZQ== root@localhost" > /root/.ssh/authorized_keys


CMD /usr/sbin/sshd -f /etc/ssh/sshd_config -D


