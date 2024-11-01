# oci_cache
Redis/Valkey

Ideas
- PubSub to automate new writes to PostgreSQL
- VAL/Script



# Connect to OCI Cache from VM

- Create VM in public subnet
- Create OCI Cache in private subnet, same vcn. Add port 6379

Run to connect
```
redis-cli --tls -h <endpoint>
```

Connect with Python
- Install Pip: sudo yum install python3-pip
- sudo pip3 install redis

Test with Python
```
python3
import redis
r = redis.Redis(host='aaaeicj2tiavwiftrvoi22hfqc7encrzjwgwt4vbe5etwbbmhbwjsia-p.redis.us-ashburn-1.oci.oraclecloud.com', port=6379, ssl=True)
r.set('testx', 'textxxx')
```
