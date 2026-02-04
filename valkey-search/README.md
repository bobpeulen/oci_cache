# Example of using valkey-search (Vector similarity) using OCI Cache (Valkey)

```
import valkey
VALKEY_CLUSTER_ENDPOINT = "xx"

valkey_client = valkey.Valkey(
    host=VALKEY_CLUSTER_ENDPOINT,
    port=6379,
    ssl=True,
    ssl_cert_reqs="none",
)
valkey_client.ping()
```
