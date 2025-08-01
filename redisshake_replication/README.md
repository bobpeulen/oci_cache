# Cross-cluster and region replication across OCI Cache using RedisShake


## Create Clusters and Jump Hosts in two regions

- Jump hosts in public subnet
- OCI Cache clusters in private subnet
- Open ports


# Set up Remote peering between two VCNs in the different regions


# Install redis-cli

```
sudo dnf module list nodejs
sudo dnf module enable nodejs:20
sudo dnf install nodejs -y
sudo npm i -g redis-cli
```

# Connect to cluster
```
rdcli --tls -h [Endpoint]
```


- Install and start Docker
```
sudo yum install -y yum-utils  
sudo yum-config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl start docker
```

- Open Redis ports, .. networking?

sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload 

