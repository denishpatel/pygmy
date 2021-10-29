# pygmy
Pygmy - Saving on Cloud bills by Scaling Down Postgres Replica DB Servers

- Do you run PostgreSQL in AWS, either on EC2 or in RDS? 
- Do you have one or more streaming replicas? 
- Do you size your servers for peak load and wish they would cost less when the load is less?

Pygmy is the tool for you!

Pygmy is a tool which takes advantage of predictable load patterns, resizing your replica dbs to something more appropriate at defined times of the day. When combined with pgBouncer, it can make sure clients never know you're saving money. Before taking any action it will check current activity and replication status, and it will call a script before and after stopping instances to play nicely with your environment. It will also call a script at the appropriate place when downsizing or upsizing cluster replicas to make sure no clients are impacted. 

---

Pygmy runs on a central server, from which it manipulates the Postgres clusters it has been configured to know about. Setting up pygmy therefore involves both preparing your environment to be manipulated by pygmy, and setting up pygmy itself.

## Environment setup
### Make a db role 
Pygmy requires a superuser role to be created on every Postgres DB it will be controlling. The role will be used to do things like observe load, connection counts, and replication lag.

Create a superuser role and make sure it can log into the postgres db on your postgres clusters you'd like to manage.

### Install the EnterpriseDB system_stats extension
This extension gives a way to determine system load independent of EC2 or RDS.

Install this extension however you like on all members of your cluster. Make sure it is installed in the postgres db instead of your application's db, as that is what pygmy will be connecting to.
```sh
sudo apt-get -y install make gcc postgresql-server-dev-12 llvm clang

git clone https://github.com/EnterpriseDB/system_stats.git
cd system_stats/
PATH="/usr/lib/postgresql/13/bin:$PATH" make USE_PGXS=1
sudo PATH="/usr/lib/postgresql/13/bin:$PATH" make install USE_PGXS=1
psql -U postgres -d postgres
postgres=# CREATE EXTENSION system_stats;
CREATE EXTENSION
```


## Pygmy setup
Set up a machine for pygmy to run on, making sure it has a postgres db on it for pygmy to keep its state.

Install system dependencies : E.g for ubuntu
```sh
$ sudo apt install build-essential python3-dev libpq-dev python3-virtualenv libxml2-dev libxslt1-dev
```

Create virtualenv
```sh
$ virtualenv -p python3 venv
```

### Start Project
Activate virtualenv
```sh
$ source venv/bin/activate
```

Install all dependencies
```sh
$ pip install -r requirements.txt
```

Make Migrations
```sh
$ python manage.py makemigrations
```

Alter DB connection parameters.
- Modify `pygmy/settings.py` or,
- Set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and `DB_HOST` in an .env file as needed, in the same directory as manage.py.

Run Migration
```sh
$ python manage.py migrate
```

Populate settings data ( Run only one time at starting )
This will also enable 
```sh
$ python manage.py populate_settings_data
```

Optional You can enter secrets using following command (COMMAND LINE)
```sh
$ python manage.py set_secrets
```

Load instance types data
```sh
$ python manage.py refresh_all_db_instance_types
```

create user from command line
```sh
$ python manage.py createsuperuser
```

Pygmy will scan instances which have following Tag-Value set
```sh
"EC2_INSTANCE_POSTGRES_TAG_KEY_NAME": "Role"
"EC2_INSTANCE_POSTGRES_TAG_KEY_VALUE": "PostgreSQL"
"EC2_INSTANCE_PROJECT_TAG_KEY_NAME": "Project"
"EC2_INSTANCE_ENV_TAG_KEY_NAME": "Environment"
"EC2_INSTANCE_CLUSTER_TAG_KEY_NAME": "Cluster"
```

Load instance data
```sh
$ python manage.py get_all_db_data
```

Make DNS, pre-resize, and post-streaming scripts at `scripts/{dns-change,pre-resize,post-streaming}.sh`
- `dns-change.sh` will be used to modify DNS before and after resize.
- `pre-resize.sh` will be called before a replica is resized. You might use this to gag your monitoring or give your auto-failover logic a xanax.
- `post-streaming.sh` will be called after a replica has been resized *and* has resumed streaming replication. You might use this to undo the effects of `pre-resize.sh`.

For each of these scripts,
- Copy one of the existing example scripts in scripts
- Roll your own
- Remember to make them executable


Start local server ( Testing only )
```sh
$ python manage.py runserver
```

Modify `uwsgi.sgi` as needed.

Start uwsgi ( Production )
```sh
$  nohup uwsgi uwsgi.ini &
```

Restart uwsgi ( Production )
```sh
$  pkill -9 uwsgi
$  nohup uwsgi uwsgi.ini &
```
---
## API Cookbook
### Get a list of all clusters
```sh
curl -s  http://127.0.0.1:8000/v1/api/clusters | jq '.'
```
> [  {
    "id": 249,
    "name": "project-loadtest-1",
    "primaryNodeIp": "10.37.71.67",
    "type": "EC2"
   },
  {
    "id": 252,
    "name": "project-loadtest-jobs1",
    "primaryNodeIp": "10.37.90.106",
    "type": "EC2"
  }
]

### Manage cluster 249
In this case, project-loadtest-1
- `cluser_id` is the cluster
- `avg_load` is ???
```sh
curl -X POST http://127.0.0.1:8000/v1/api/cluster/management \
   -H "Content-Type: application/json" \
   -d '{"cluster_id": 249, "avg_load": 12}'
 ```
>{"id":1,"avg_load":"12","fallback_instances_scale_up":null,"fallback_instances_scale_down":null,"check_active_users":null,"cluster_id":249}

#### woops, add instance types
We can delete the old rule and make a new one
- `fallback_instances_scale_up` is an array of instances to try, in order, for scale_up rules when our chosen instance size isn't available
- `fallback_instances_scale_down` is an array of instances to try, in order, for scale_down rules when our chosen instance size isn't available
```sh
curl -X DELETE http://127.0.0.1:8000/v1/api/cluster/management/1
curl -X POST http://127.0.0.1:8000/v1/api/cluster/management \
   -H "Content-Type: application/json" \
   -d '{
          "cluster_id": 249, 
          "avg_load": 12, 
          "fallback_instances_scale_up": ["m5.24xlarge","m5.16xlarge"], 
          "fallback_instances_scale_down": ["m5.large","m5.xlarge"]
      }'
```
>{"id":2,"avg_load":"12","fallback_instances_scale_up":["m5.24xlarge","m5.16xlarge"],"fallback_instances_scale_down":["m5.large","m5.xlarge"],"check_active_users":null,"cluster_id":249}

#### Validate
```sh
curl -s  http://127.0.0.1:8000/v1/api/cluster/management | jq '.'
```
>[
  {
    "id": 2,
    "avg_load": "12",
    "fallback_instances_scale_up": [
      "m5.24xlarge",
      "m5.16xlarge"
    ],
    "fallback_instances_scale_down": [
      "m5.large",
      "m5.xlarge"
    ],
    "check_active_users": null,
    "cluster_id": 249
  }
]

#### woops, m5.xlarge isn't what we wanted, _and_ we forgot users
We can also use PUT to modify a rule in place
- `check_active_users` is an array of LIKE arguments to match against db role when looking to count relevant active transactions. In this rule, we will count transactions if their db role is like 'project%' or like 'bench-rw'
```sh
curl -X PUT http://127.0.0.1:8000/v1/api/cluster/management/2 \
   -H "Content-Type: application/json" \
   -d '{
          "cluster_id": 249, 
          "avg_load": 12, 
          "fallback_instances_scale_up": ["m5.24xlarge","m5.16xlarge"], 
          "fallback_instances_scale_down": ["m5.large","m5.2xlarge"],
          "check_active_users": ["project%","bench-rw"]
      }'
```

### Now manage cluster 252 (project-loadtest-jobs1)
```sh
curl -X POST http://127.0.0.1:8000/v1/api/cluster/management \
   -H "Content-Type: application/json" \
   -d '{
          "cluster_id": 252, 
          "avg_load": 2, 
          "fallback_instances_scale_up": ["m5.24xlarge","m5.16xlarge"], 
          "fallback_instances_scale_down": ["m5.large","m5.xlarge"],
          "check_active_users": ["project%","bench-rw"]
      }'
```
>{"id":5,"avg_load":"2","fallback_instances_scale_up":["m5.24xlarge","m5.16xlarge"],"fallback_instances_scale_down":["m5.large","m5.xlarge"],"check_active_users":["project%","bench-rw"],"cluster_id":252}

### Make a DNS entries
When Pygmy manipulates a db, it will also twiddle DNS to move load away from, or back to, that replica. We will need to record the CNAME that Pygmy will change, but _also_ record how Pygmy will find that CNAME when it is working on a specific db. Pygmy supports two ways of matching an actual instance it is working on to a DNS entry:
* MATCH_INSTANCE is used when there is a static, 1:1 relationship between a CNAME and an instance. This is simple and works well when your DB instances won't change: for example, i-123456 will always host cluster3-replica.example.com.
* MATCH_ROLE is used when you want any db node with a specific tag for a given cluster to use a CNAME. This works well when your DB nodes have some flux, or if multiple share the same CNAME. For example, if cluster3-replica.example.com is serviced by one or more DBs tagged as Secondary, and those DBs might be replaced over time, MATCH_ROLE will reliably change the DNS for them whenever Pygmy runs.

```sh
curl -X POST http://127.0.0.1:8000/v1/api/dns \
   -H "Content-Type: application/json" \
   -d '{
          "match_type": "MATCH_ROLE",
          "tag_role": "Slave",
          "cluster": 249,
          "instance_id": null,
          "dns_name": "cluster1-slave-rrdns.project-loadtest.insops.net", 
          "hosted_zone_name": "n/a"
      }'

# OR

for id in $(curl -s  http://127.0.0.1:8000/v1/api/instances | jq '.[] | select(.cluster == 252 and .isPrimary == 'false') | .id'); do
 curl -X POST http://127.0.0.1:8000/v1/api/dns \
   -H "Content-Type: application/json" \
   -d '{
          "match_type": "MATCH_INSTANCE",
          "instance_id": '$id', 
          "tag_role": null,
          "cluster": null,
          "dns_name": "clusterjobs1-secondary.project-loadtest.insops.net", 
          "hosted_zone_name": "n/a"
      }'; done
```

### Make a simple scaledown rule
This is a simple scale down rule with a scheduled reverse. It is likely a terrible idea, but shows how the various checks can be defined.
- Every 10 minutes, starting at the top of the hour, the cluster will scale down to an m5.2xlarge.
- The rule will only run if our replication lag is exactly equal to 12 seconds (unlikely)
- The rule will only run if we have more than 12 active connections, as defined by the owners above (unlikely what we want)
- The rule will only run if the combined average load of the nodes in the cluster is <32.
- If any of those 3 checks are false, the rule will retry 3 times, 15 minutes apart.
- The rule will also try to reverse itself every 10 minutes, starting 5 minutes after the top of the hour.
```sh
curl -X POST http://127.0.0.1:8000/v1/api/rules \
   -H "Content-Type: application/json" \
   -d '{ 
          "name": "Test rule", 
          "typeTime": "CRON", 
          "cronTime": "0,10,20,30,40,50 * * * *",

          "cluster_id": 249,
          "action": "SCALE_DOWN",
          "ec2_type": "m5.2xlarge",

          "enableReplicationLag": "on",
          "selectReplicationLagOp": "equal",
          "replicationLag": "12",

          "enableCheckConnection": "on",
          "selectCheckConnectionOp": "greater",
          "checkConnection": "12",

          "enableAverageLoad": "on",
          "selectAverageLoadOp": "less",
          "averageLoad": "32",

          "enableRetry": "on",
          "retryAfter": "15",
          "retryMax": "3",

          "enableReverse": "on",
          "reverse_action": "SCALE_UP",
          "reverseCronTime": "5,15,25,35,45,55 * * * *"
    }'
```

### Get rid of a rule
Notice that its reverse rule also goes away
```sh
curl -X DELETE http://127.0.0.1:8000/v1/api/rules/12
```

### Make a better rule
This is another simple example of a rule with a reverse, with more reasonable settings.
```sh
curl -X POST http://127.0.0.1:8000/v1/api/rules \
   -H "Content-Type: application/json" \
   -d '{ 
          "name": "Simple cluster1 control", 
          "typeTime": "CRON", 
          "cronTime": "0 * * * *",

          "cluster_id": 249,
          "action": "SCALE_DOWN",
          "ec2_type": "m5.2xlarge",

          "enableCheckConnection": "on",
          "selectCheckConnectionOp": "less",
          "checkConnection": "12",

          "enableReplicationLag": "on",
          "selectReplicationLagOp": "less",
          "replicationLag": "120",

          "enableAverageLoad": "on",
          "selectAverageLoadOp": "less",
          "averageLoad": "32",

          "enableRetry": "on",
          "retryAfter": "15",
          "retryMax": "3",

          "enableReverse": "on",
          "reverse_action": "SCALE_UP",
          "reverseCronTime": "30 * * * *"
    }'
```

### Make a realistic rule
#### First the scaledown
```sh
curl -X POST http://127.0.0.1:8000/v1/api/rules \
   -H "Content-Type: application/json" \
   -d '{ 
          "name": "jobs1 downsize", 
          "typeTime": "CRON", 
          "cronTime": "0 * * * *",

          "cluster_id": 252,
          "action": "SCALE_DOWN",
          "ec2_type": "c5.large",

          "enableCheckConnection": "on",
          "selectCheckConnectionOp": "less",
          "checkConnection": "2",

          "enableReplicationLag": "on",
          "selectReplicationLagOp": "less",
          "replicationLag": "60",

          "enableAverageLoad": "on",
          "selectAverageLoadOp": "less",
          "averageLoad": "2",

          "enableRetry": "on",
          "retryAfter": "5",
          "retryMax": "3"
    }'
```

#### Make a scheduled scaleup rule for jobs1
We don't care about checks here - when the time comes, make sure the cluster is embiggened.
```sh
curl -X POST http://127.0.0.1:8000/v1/api/rules \
   -H "Content-Type: application/json" \
   -d '{ 
          "name": "jobs1 deadline upsize", 
          "typeTime": "CRON", 
          "cronTime": "55 * * * *",

          "cluster_id": 252,
          "action": "SCALE_UP",
          "ec2_type": "c5.2xlarge",

          "enableRetry": "on",
          "retryAfter": "5",
          "retryMax": "3"
    }'
```

#### Make a pre-emptive scaleup rule for jobs1
This rule starts soon after the scaledown has completed, and repeatedly checks if the load has gotten too high or if replication has fallen behind. If so, then scale up before we normally would.
- `conditionLogic` set to ANY means that if any of the checks are true, the rule will run. The default is for ALL, meaning all checks must be true.
- `retryAfter` and `retryMax` are set to make sure the rule keeps trying until the manditory scaleup occurs.
```sh
curl -X POST http://127.0.0.1:8000/v1/api/rules \
   -H "Content-Type: application/json" \
   -d '{ 
          "name": "jobs1 early upsize", 
          "typeTime": "CRON", 
          "cronTime": "20 * * * *",

          "conditionLogic": "ANY",

          "cluster_id": 252,
          "action": "SCALE_UP",
          "ec2_type": "c5.2xlarge",

          "enableReplicationLag": "on",
          "selectReplicationLagOp": "greater",
          "replicationLag": "60",

          "enableAverageLoad": "on",
          "selectAverageLoadOp": "greater",
          "averageLoad": "2",

          "enableRetry": "on",
          "retryAfter": "5",
          "retryMax": "6"
    }'
```
