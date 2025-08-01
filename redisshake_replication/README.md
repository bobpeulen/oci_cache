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

```
sudo docker run --network host \
    -e SYNC=true \
    -e tls=true \
    -e SHAKE_SRC_ADDRESS=aaaeicj2tiaqtv65bofxw33pbz3wm45obua5dwtzol76o7zrx6dpaaq-p.redis.eu-frankfurt-1.oci.oraclecloud.com:6379 \
    -e SHAKE_DST_ADDRESS=aaaeicj2tiagiy4q3mxc6l5nufrc7nud3ldrflcjta5ce2zje4om33q-p.redis.eu-amsterdam-1.oci.oraclecloud.com:6379 \
    ghcr.io/tair-opensource/redisshake:latest
```



- Open Redis ports, .. networking?
```
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload 
```
