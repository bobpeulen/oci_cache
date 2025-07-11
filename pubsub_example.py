
# OCI Cache
# Add keyspace notifcation to cluster

#########
######### Publisher / Appending Redis


import redis
import time
from redis import StrictRedis

primary_endpoint = ""
port = 6379

primary_pool = redis.ConnectionPool(
host=primary_endpoint,
port=port,
db=0,
connection_class=redis.SSLConnection,
ssl_cert_reqs="none"
)
 
# Write to the master (primary)
with redis.StrictRedis(connection_pool=primary_pool) as primary_connection:
    #primary_connection.set("key6", "20")
    primary_connection.append("key6", "50")


#########
######### Subscriber
import redis
import time
from redis import StrictRedis

replica_endpoint = ""

redis = StrictRedis(host=replica_endpoint, port=6379, db=0, ssl=True)

pubsub = redis.pubsub()  
pubsub.psubscribe('__keyspace@0__:*')

print('Starting message loop')
while True:
    message = pubsub.get_message()
    if message:
        print(message)
    else:
        time.sleep(1)
