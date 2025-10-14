# Database Project with Django MongoDB, PostgreSQL using Docker



### Start docker containers:
```docker-compose up --build```

### Update database schema:
1. Apply changes to src/core/models.py
2. Run the following commands:
``` docker exec django_app python manage.py makemigrations```
```docker exec django_app python manage.py migrate```

### Open SQL command line:
```docker exec -ti postgres_db psql -U dev_user -d dev_db```

### Open Django Python shell:
```docker exec -ti django_app python manage.py shell```

### PostgreSQL Cheat Sheet:
https://gist.github.com/Kartones/dd3ff5ec5ea238d4c546