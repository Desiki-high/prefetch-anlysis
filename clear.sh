#! /bin/bash
#!/bin/bash

nerdctl ps -q | xargs -r nerdctl stop
nerdctl ps -a -q | xargs -r nerdctl rm
sudo nerdctl image prune --all -f
sudo rm -rf ~/logs/*
sudo rm -rf /var/lib/containerd-nydus/cache/*
sudo systemctl restart nydus-snapshotter
sudo systemctl restart containerd