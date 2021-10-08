# pygmy
Pygmy - Saving on Cloud bills by Scaling Down Postgres Replica DB Servers

---

Pygmy runs on a central server, from which it manipulates various Postgres clusters. Setting up pygmy therefore involves both preparing your environment to be maniuplated by pygmy, and setting up pygmy itself.

## Environment setup
### Make a db role 
Pygmy requires a superuser role to be created on every Postgres DB it will be controlling. The role will be used to do things like observe load, connection counts, and replication lag.

Create a superuser role and make sure it can log into the postgres db on your postgres clusters you'd like to manage.

### Install the EnterpriseDB system_stats extension
This extension gives a way to determine system load independent of EC2 or RDS.

Install this extension however you like on all members of your cluster. Make sure it is installed in the postgres db instead of your application's db, as that is what pygmy will be connecting to.
```
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
```shell
$ sudo apt install build-essential python3-dev libpq-dev python3-virtualenv libxml2-dev libxslt1-dev
```

Create virtualenv
```shell
$ virtualenv -p python3 venv
```

### Start Project
Activate virtualenv
```shell
$ source venv/bin/activate
```

Install all dependencies
```shell
$ pip install -r requirements.txt
```

Make Migrations
```shell
$ python manage.py makemigrations
```

Alter DB connection parameters.
- Modify `pygmy/settings.py` or,
- Set DB_NAME, DB_USER, DB_PASSWORD, and DB_HOST in an .env file as needed, in the same directory as manage.py.

Run Migration
```shell
$ python manage.py migrate
```

Populate settings data ( Run only one time at starting )
This will also enable 
```shell
$ python manage.py populate_settings_data
```

Optional You can enter secrets using following command (COMMAND LINE)
```shell
$ python manage.py set_secrets
```

Load instance types data
```shell
$ python manage.py refresh_all_db_instance_types
```

create user from command line
```shell
$ python manage.py createsuperuser
```

Pygmy will scan instances which have following Tag-Value set
"EC2_INSTANCE_POSTGRES_TAG_KEY_NAME": "Role"
"EC2_INSTANCE_POSTGRES_TAG_KEY_VALUE": "PostgreSQL"
"EC2_INSTANCE_PROJECT_TAG_KEY_NAME": "Project"
"EC2_INSTANCE_ENV_TAG_KEY_NAME": "Environment"
"EC2_INSTANCE_CLUSTER_TAG_KEY_NAME": "Cluster"

Load instance data
```shell
$ python manage.py get_all_db_data
```

Make a DNS script at scripts/dns-change.sh
- Copy one of the existing scripts in scripts
- Roll your own

Start local server ( Testing only )
```shell
$ python manage.py runserver
```

Start uwsgi ( Production )
```shell
$  nohup uwsgi proj.ini &
```

Restart uwsgi ( Production )
```shell
$  pkill -9 uwsgi
$  nohup uwsgi proj.ini &
```
