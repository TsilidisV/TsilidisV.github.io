---
date: 2026-01-17
categories:
  - Coding
  - Python
  - Docker
  - Data Science
  - Data Engineering
  - SQL
tags:
  - productivity
  - mkdocs
title: "Introduction to Docker - Part 4: Connecting Python to a Dockerized PostgreSQL"
description: "Bridge the gap between your local Python environment and a Dockerized database using SQLAlchemy, while securing your credentials with environment variables."
---

# {{ title }}
{{ description }}

<!-- more -->

In [Introduction to Docker - Part 3: Compose](./compose.md) we saw how to run PostgreSQL and pgAdmin with Docker. In this article we will connect to PostgreSQL with a local version of Python.

## Preliminaries
Let's create a folder, open it up in a terminal and run `uv init . --python=3.14`. Next, place the `docker-compose.yml` created in [Introduction to Docker - Part 3: Compose](./compose.md) inside the folder and run `docker compose up -d`.

## SQLAlchemy
SQLAlchemy is an open-source Python library that provides an SQL toolkit and an object–relational mapper for database interactions. 

In order to connect to some database through SQLAlchemy, we need to first construct the SQLAlchemy’s database URL, which looks like this:
```bash
dialect+driver://username:password@host:port/database
```

- `dialect`: The database type (e.g., `postgresql`, `mysql`, `sqlite`).
- `driver`: The Python database API implementation (e.g., `psycopg2` for `postgresql`, `pymysql` for `mysql`). If we omit the driver, SQLAlchemy will pick a default if available. 
- `username` and `password`: The account credentials used to authenticate to the database server.
- `host`: The server address. 
- `port`: The TCP (Transmission Control Protocol) port the database listens on. 
- `database`: The name of the database.

In our case, we will use `postgresql` as the `dialect` and `psycopg2` as the driver. Psycopg2 is a PostgreSQL database adapter for Python. It allows us to interact with PostgreSQL using our Python scripts.

Let's add SQLAlchemy and `psycopg2` to our project with `uv add sqlalchemy psycopg2-binary`.

For the rest of the fields we need to take a look at `docker-compose.yml` and specifically at the `db` section:
```yaml
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: "user"
      POSTGRES_PASSWORD: "password"
      POSTGRES_DB: "mydatabase"
    volumes:
      - "pgdata:/var/lib/postgresql/data"
    ports:
      - "5433:5432" 
```

In order to connect to this database, we have to set:

- `username` to the `POSTGRES_USER` field, that is, `user`
- `password` to the `POSTGRES_PASSWORD` field, that is, `password`
- `database` to the `POSTGRES_DB` field, that is, `mydatabase`.

All that's left is to set the `host` and `port`. Since we will run our script using a **local** Python environment which will run on our machine with `uv`, we access the container from the *outside*.

Because we're sitting outside of the container we'll set the `host` to be `localhost`. If we were running the script inside of the container, we'd use the service name of the database, that is `db`.

Regarding the port, all we have to remember is that
```yaml
ports:
    - "5433:5432" 
```
maps the port `5433` of our machine to the container port `5432`. Again, since we run python on our local environment, we set the port to be `5433`. If we were running the script inside of the container, we'd use the container port of the database, that is `5432`.

Hence, our full Connection URL string looks like:
```bash
postgresql+psycopg2://user:password@localhost:5433/mydatabase 
```



## Connection to the Database
In SQLAlchemy, everything starts with the Engine. Think of the Engine as the home base for our database. It manages the pool of connections so we don't have to open and close them manually every single time. To get started, we will need to import `create_engine` from the library. To initialize the engine, we write `create_engine(OUR_DB_URL_STRING)`. Hence, we update `main.py` to be:

 ```python
import os
from sqlalchemy import create_engine, text

def main():
    db_url = 'postgresql+psycopg2://user:password@localhost:5433/mydatabase'
 
    engine = create_engine(db_url)

if __name__ == "__main__":
    main()
``` 

Since `create_engine` is lazy, it hasn't really tried to talk the database yet. It only connects when we specifically ask it to do some work. To test if our bridge really works, we need to ask for a connection. To do that we call `engine.connect()`.

To keep things clean and ensure the connection closes automatically (even if errors happen), it's best practice to use it inside a context manager (a `with` statement). 

Additionally, SQLAlchemy requires us to wrap raw SQL strings in a function called `text()` which we have to import from `sqlalchemy`.

Finally, to execute some SQL command we have to call the `execute` method on the connection we have made.

Let's update `main.py` to reflect all that:

 ```python
import os
from sqlalchemy import create_engine, text

def main():
    db_url = 'postgresql+psycopg2://user:password@localhost:5433/mydatabase'
 
    engine = create_engine(db_url)

    with engine.connect() as connection:
        # Send the query!
        result = connection.execute(text("SELECT version()"))
        print(result.all())

if __name__ == "__main__":
    main()
``` 

If we now run `uv run main.py` we'll see the terminal printing the version of the PostgresSQL that runs on the container.

### Best Practices
Having things like the database username and password written in plain sight in our `docker-compose.yml` `and main.py` is a security risk. To keep our credentials safe, we'll store them in a file named `.env`.

Let's create a new file named `.env `in our project folder. Inside, we need to define some variables that hold our secrets (usernames and passwords) and connection settings (`HOST` and `PORT`):
```env
DB_USER=user
DB_PASSWORD=password
DB_NAME=mydatabase
HOST=localhost
PORT=5433
PGADMIN_EMAIL=admin@admin.com
PGADMIN_PASSWORD=root
```

Now that our secrets are safely tucked away in `.env`, let's modify the Python script to use them. First of all we have to learn how to load the variables we hid in `.env`. For that we will use the `dotenv` package. Let's add it to our environment with `uv add python-dotenv`. Then, let's update `main.py`:
```python
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def main():
    load_dotenv()  # This loads the .env file
    
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    host = os.getenv("HOST")
    port = os.getenv("PORT")

     # We get the variable here
    db_url =  f"postgresql+psycopg2://{db_user}:{db_password}@{host}:{port}/{db_name}"

    engine = create_engine(db_url)

    with engine.connect() as connection:
        # Send the query!
        result = connection.execute(text("SELECT version()"))
        print(result.all())

if __name__ == "__main__":
    main()
```

The variable `db_url` now holds the string `'postgresql+psycopg2://user:password@localhost:5433/mydatabase'`, but without being hardcoded in the script.

Additionally, we should modify our `docker-compose.yml` since there are secrets hardcoded in there as well:
```yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - "pgdata:/var/lib/postgresql/data"
    ports:
      - "${PORT}:5432"

  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: ${PGADMIN_EMAIL}
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD}
    volumes:
      - "pgadmin-data:/var/lib/pgadmin"
    ports:
      - "8085:80"

volumes:
  pgdata:
  pgadmin-data:
```

Docker looks for the variables encoded with `${}` inside the `.env` located in the same directory as `docker-compose.yml`.

Most importantly, if we plan to upload our code in GitHub, we should add `.env` to our `.gitignore` file so these secrets are never pushed to our repository.