# Cross-cluster and region replication across OCI Cache using RedisShake

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

