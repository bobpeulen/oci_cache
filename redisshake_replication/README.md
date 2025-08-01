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


- RedsShake
```
sudo ./bin/redis-shake shake.toml
```



