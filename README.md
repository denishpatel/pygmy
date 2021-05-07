# pygmy
Pygmy - Saving on Cloud bills by Scaling Down Postgres Replica DB Servers

---

### Environment setup
Install system dependencies : E.g for ubuntu
```shell
$ sudo apt install build-essential python3-dev libpq-dev python3-virtualenv
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

Run Migration
```shell
$ python manage.py migrate
```

Load instance types data
```shell
$ python manage.py refresh_all_db_instance_types
```

Populate settings data ( Run only one time at starting )
```shell
$ python manage.py populate_settings_data
```

Optional You can enter secrets using following command (COMMAND LINE)
```shell
$ python manage.py set_secrets
```

create user from command line
```shell
$ python manage.py createsuperuser
```

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

