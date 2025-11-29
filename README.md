# Database Project with Django MongoDB, PostgreSQL using Docker



### Start docker containers:
```docker-compose up --build```

### Update database schema:
1. Apply changes to src/core/models.py
2. Run the following commands:

- ``` docker exec django_app python manage.py makemigrations```
- ```docker exec django_app python manage.py migrate```

### Import MongoDB data
1. CSV files should be placed in the `src/datasets` folder.
2. Run the following command:
```docker exec -ti django_app python manage.py import_mongo_data```

### Open SQL command line:
```docker exec -ti postgres_db psql -U dev_user -d dev_db```

### Open Django Python shell:
```docker exec -ti django_app python manage.py shell```

### Open MongoDB shell:
```docker exec -it mongo_db mongosh -u dev_user -p test --authenticationDatabase admin```

### Other commands: 
Create a Django superuser:
``` docker exec -ti django_app python manage.py createsuperuser```

Run Django tests:
``` docker exec -ti django_app python manage.py test```

Run Django Admin Commands:
``` docker exec -ti django_app python manage.py <file name in src/core/management/commands>```

### Testing URLS:
http://localhost:8000/api/products/search/?q=jean

### PostgreSQL Cheat Sheet:
https://gist.github.com/Kartones/dd3ff5ec5ea238d4c546

### Django MongoDB Mapper Documentation:
https://www.djongomapper.com/docs/get-started


