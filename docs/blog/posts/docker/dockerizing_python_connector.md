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
title: "Introduction to Docker - Part 5: Dockerizing a Python Script"
---
# {{ title }}

This article breaks down the containerization setup for a Python application which connects to a PostgreSQL database, specifically focusing on the build process (`Dockerfile`) and the application service configuration (`docker-compose.yml`).

<!-- more -->

## Preliminaries
Here's our project structure:
```
project/
├─ .dockerignore
├─ .env
├─ docker-compose.yml
├─ Dockerfile
├─ main.py
```
With `.dockerignore`:
```.dockerignore
.env
.git
__pycache__
venv/
```

`.env:`
```
DB_USER=user
DB_PASSWORD=password
DB_NAME=mydatabase
HOST=localhost
PORT=5433
PGADMIN_EMAIL=admin@admin.com
PGADMIN_PASSWORD=root
```

`docker-compose.yml`:
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

  app:
    build: .
    environment:
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      DB_NAME: ${DB_NAME}
      HOST: db
      PORT: 5432

volumes:
  pgdata:
  pgadmin-data:
```

```Dockerfile
FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml .python-version uv.lock . 
RUN uv sync --locked

COPY . .

CMD ["uv", "run", "main.py"]
```

and `main.py`:
```python
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def main():
    load_dotenv()  # This loads the .env file
    
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    host = os.getenv('HOST')
    port = os.getenv('PORT')

     # We get the variable here
    db_url =  f"postgresql+psycopg2://{db_user}:{db_password}@{host}:{port}/{db_name}"
    
    print(db_url)

    engine = create_engine(db_url)

    with engine.connect() as connection:
        # Send the query!
        result = connection.execute(text("SELECT version()"))
        print(result.all())

if __name__ == "__main__":
    main()
```


Let's initialize the project by typing `uv init . --python=3.14` in the terminal and then running `uv add python-dotenv sqlalchemy psycopg2-binary`. We are now ready to start the docker container by running 
```bash
docker compose up --build
```
The `--build` flag forces compose to run the image build step for any service that has a build section in `docker-compose.yml` before creating or starting containers. Without it, Compose will use existing images (local or pulled) and skip rebuilding, which can leave containers running older code or layers.

If things went well, we'll see 
```bash
 [('PostgreSQL 16.11 (Debian 16.11-1.pgdg13+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit',)]
```
somewhere in the terminal.

## 1. The Dockerfile
Let's get started with the `dockerfile`. This file uses a multi-stage build process optimized for modern Python tooling using `uv`:

### Step-by-Step Breakdown

1. **`FROM python:3.14-slim`**
* **Base Image:** Uses a lightweight ("slim") version of Python 3.14 to keep the final image size small while ensuring the correct Python runtime is available.


2. **`COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/`**
* **Tooling:** Instead of installing `uv` via pip, we copy the pre-compiled binary directly from the official `uv` Docker image.
* **Why?** `uv` is a high-performance Python package manager that replaces pip/poetry. Copying the binary is faster and cleaner than installing it.


3. **`WORKDIR /app`**
* Sets the working directory inside the container to `/app`. All subsequent commands run here.


4. **`COPY pyproject.toml .python-version uv.lock .`**
* **Caching Strategy:** We copy *only* the dependency definition files first.
* **Benefit:** Docker caches layers. If you change your code (`main.py`) but not your dependencies, Docker will skip the installation step (next) and reuse the cache, making builds significantly faster.


5. **`RUN uv sync --locked`**
* **Installation:** Installs the dependencies defined in `uv.lock`.
* **`--locked`:** Ensures strict reproducibility by refusing to update versions that differ from the lockfile.


6. **`COPY . .`**
* Copies the remaining source code (like `main.py`) into the container.


7. **`CMD ["uv", "run", "main.py"]`**
* **Startup:** Defines the command that runs when the container starts. `uv run` ensures the script runs within the virtual environment context created during the sync step.



---

## 2. The `app` Service (docker-compose.yml)
Here's our `docker-compose.yml` file:
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

  app:
    build: .
    environment:
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      DB_NAME: ${DB_NAME}
      HOST: db
      PORT: 5432

volumes:
  pgdata:
  pgadmin-data:
```

We've already covered how the `db` and `pgadmin` services work, so let's focus on the `app` service. The `app` service is the name we give to the service that configures how the Python container runs and interacts with the database. Essentially is where our python code lives:

```yaml
  app:
    build: .
    environment:
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      DB_NAME: ${DB_NAME}
      HOST: db      # <--- Hardcoded Override
      PORT: 5432    # <--- Hardcoded Override

```

### 1. Line-by-Line Breakdown

#### `build: .`

* **What it does:** Tells Docker to build a new image from scratch using the `Dockerfile` found in the **current directory** (`.`).
* **Context:** It sends all files in the current folder (main.py, pyproject.toml, etc.) to the Docker engine as the "build context" so they can be copied into the image.

#### `environment:`

* **What it does:** Defines the variables that will be available inside the Linux container when it starts. These are what `os.getenv()` in your Python script will read.
* **Dynamic Values (`${...}`):**
* `DB_USER: ${DB_USER}` tells Docker Compose: *"Look at the `.env` file on the host machine, grab the value for `DB_USER`, and pass it into the container."*


* **Static Values (Hardcoded):**
* `HOST: db` tells Docker Compose: *"Ignore the `.env` file. Force the variable `HOST` to be the string 'db' inside this container."*



---

### 2. Why do we override HOST and PORT?

This is the most critical concept in Docker networking. You have two different "worlds" trying to access the same database.

#### The "Local" World (Your Computer)

When you run scripts manually on your computer, you are outside the Docker network.

* **Host:** `localhost` (Your computer).
* **Port:** `5433` (The port exposed in `ports:` section of the `db` service).
* **Reason:** You cannot access the container's private IP directly, so you go through the "door" opened on port 5433.

#### The "Docker" World (Inside the Container)

When the `app` container runs, it is **inside** the Docker network, sitting right next to the `db` container.

* **Host:** `db` (The service name).
* **Port:** `5432` (The standard internal Postgres port).
* **Reason:**
1. **DNS:** Docker has an internal DNS server. It resolves the service name `db` to the internal IP address of the database container. `localhost` inside the app container would refer to the *app itself*, not the database.
2. **Direct Access:** Containers communicate directly on internal ports. The database is listening on 5432 internally. It does not know (or care) that your computer mapped it to 5433 externally.



**Summary Table:**

| Where code is running | Variable `HOST` | Variable `PORT` | Why? |
| --- | --- | --- | --- |
| **Local** (Testing) | `localhost` | `5433` | Needs external access via mapped port. |
| **Docker** (`app`) | `db` | `5432` | Uses internal Docker DNS and standard ports. |

---

### 3. The Order of Environment Variable Interaction

It can be confusing to track where a variable comes from. Here is the specific order of operations (Precedence) for how `main.py` gets its values when running via `docker-compose up`.

**Step 1: The `.env` File (Substitution)**

* Before doing anything, Docker Compose looks for a `.env` file in the folder.
* It reads `DB_USER=user`, `HOST=localhost`, etc.
* It temporarily stores these values.

**Step 2: The `docker-compose.yml` (Configuration)**

* Compose reads the YAML file.
* **Interpolation:** When it sees `${DB_USER}`, it replaces it with `user` (from Step 1).
* **Overriding:** When it reads the `HOST: db` line in the YAML, **it stops looking at the `.env` file for this variable.** The YAML configuration explicitly hardcodes this value to `db`. The `HOST=localhost` in your `.env` file is completely ignored for this specific container.

**Step 3: Container Runtime (Injection)**

* Docker starts the `app` container.
* It injects the final list of variables into the container's Linux environment:
* `DB_USER` = "user"
* `HOST` = "db" (The YAML override won)
* `PORT` = "5432" (The YAML override won)



**Step 4: Python Script (`main.py`)**

* The script runs `os.getenv('HOST')`.
* It sees "db".
* It successfully connects to the database.

#### Visual Hierarchy

1. **Highest Priority:** Variables defined explicitly in `docker-compose.yml` (e.g., `HOST: db`).
2. **Medium Priority:** Variables in `.env` (used only to fill `${}` placeholders).
3. **Lowest Priority:** Variables defined in the `Dockerfile` using `ENV` (these are overwritten by Compose).


