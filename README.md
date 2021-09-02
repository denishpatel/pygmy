# pygmy
Pygmy - Saving on Cloud bills by Scaling Down Postgres Replica DB Servers

---

### Environment setup
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
- Set DB_NAME, DB_USER, DB_PASSWORD, and DB_HOST as needed.

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

