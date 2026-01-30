---
date: 2026-01-20
categories:
  - Orchestration
  - Data Engineering
tags:
  - Kestra
  - mkdocs
title: "Running Python in Kestra"
description: "Lets explore three strategies for running Python in Kestra (runtime installation, custom Docker images, and custom Worker images) which help us balance speed, isolation, and maintenance."
---

# {{ title }}
{{ description }}

<!-- more -->

In Kestra, Python is typically executed using the `io.kestra.plugin.scripts.python.Script` task. By default, Kestra spins up a Docker container (e.g., `python:3.11-slim`) for every task, runs our code, and then destroys the container. This ensures isolation and reproducibility.

Additionally, Kestra injects a small Python library (`kestra`) into the container automatically, allowing our script to talk back to the orchestration engine (sending outputs, metrics, etc.).

## Hello World
Let's start with a quick example:
```yaml
id: python_hello_world
namespace: company.team

tasks:
  - id: my_python_task
    type: io.kestra.plugin.scripts.python.Script
    containerImage: python:3.11-slim 
    script: |
      import sys
      print(f"Hello from Python {sys.version}")
```

We created a new flow with the `id` `python_hello_world` and with the `namespace` `company.team`.

Then, we defined a task called `my_python_task` with type `io.kestra.plugin.scripts.python.Script`. Let's see some key properties of this task:

- `script`: It allows us to execute Python script. It works as if we were writing code in our favorite IDE (not so conveniently, but more to that later). 
- `containerImage`: The specific Python docker container. We can use any of the [official Python Docker images](https://hub.docker.com/_/python/), or even define a custom made Python image.

## Managing Dependencies
How can we import Python packages in our code? There three main ways to go about it.

### `beforeCommands`
We can use the `beforeCommands` property to install packages before our script runs. For example:

```yaml
tasks:
  - id: my_python_task
    type: io.kestra.plugin.scripts.python.Script
    containerImage: python:3.11-slim
    beforeCommands:
      - pip install pandas
    script: |
      import pandas as pd
      df = pd.DataFrame({'Name': ['Tom', 'Nick'], 'Age': [20, 21]})
      print(df)
```

Running the code like this, will result in a reinstaltion of our packages every time we execute the flow, which naturally causes the execution time to be high.

### Pre-build Python image
Alternatively, we could provide Kestra with a Python image which already has our required packages.

We can do that by allowing Kestra to take a look at the images residing in our local computer. To do that, and assuming we run Kestra through some `docker-compose.yml`, we need to add the following to the aforementioned file:
```yaml
services:
  kestra:
    image: kestra/kestra:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /tmp/kestra-wd:/tmp/kestra-wd
```
This maps the Docker socket from our host (PC) to the Kestra container, allowing Kestra to see what our PC sees.

Then, all we have to do is make a `dockerfile` like this:
```dockerfile
FROM python:3.12-slim
RUN pip install --no-cache-dir pandas
```
and build it by `docker build python-with-pandas:latest .`

Then our task will look like this:
```yaml
tasks:
  - id: analyze_data
    type: io.kestra.plugin.scripts.python.Script
    taskRunner:
      type: io.kestra.plugin.scripts.runner.docker.Docker
      image: python-with-pandas:latest
      pullPolicy: IF_NOT_PRESENT
    script: |
      import pandas as pd
      df = pd.DataFrame({'Name': ['Tom', 'Nick'], 'Age': [20, 21]})
      print(df)
```

We used the docker image named `python-with-pandas:latest` we just built. Additionally, the `pullPolicy` property is set to `IF_NOT_PRESENT` which makes Kestra search for the image locally, and if it doesn't find it, then tries to download the specified image.

### Kestra Image with Required Dependences
Finally, we could build Kestra with the required dependencies already installed. To do that, we first create a `dockerfile`:
```dockerfile
# Start with the official Kestra image
FROM kestra/kestra:v1.2

# Switch to root to install system dependencies
USER root

# Install Python3, Pip, and Pandas
RUN apt-get update -y && \
    apt-get install -y python3 python3-pip && \
    pip3 install --no-cache-dir pandas
```

and then run Kestra trough the following `docker-compose.yml`:
```yaml
volumes:
  kestra_postgres_data:
    driver: local
  kestra_data:
    driver: local

services:
  kestra_postgres:
    image: postgres:18
    volumes:
      - kestra_postgres_data:/var/lib/postgresql
    environment:
      POSTGRES_DB: kestra
      POSTGRES_USER: kestra
      POSTGRES_PASSWORD: k3str4
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -d $${POSTGRES_DB} -U $${POSTGRES_USER}"]
      interval: 30s
      timeout: 10s
      retries: 10

  kestra:
    build: 
      context: .
    user: "root"
    command: server standalone
    volumes:
      - kestra_data:/app/storage
      # Maps the Docker socket from our host (PC) to the Kestra container, allowing Kestra to see the containers in our PC.
      - /var/run/docker.sock:/var/run/docker.sock
      - /tmp/kestra-wd:/tmp/kestra-wd
    environment:
      KESTRA_CONFIGURATION: |
        datasources:
          postgres:
            url: jdbc:postgresql://kestra_postgres:5432/kestra
            driverClassName: org.postgresql.Driver
            username: kestra
            password: k3str4
        kestra:
          server:
            basicAuth:
              username: "admin@kestra.io" # it must be a valid email address
              password: Admin1234
          repository:
            type: postgres
          storage:
            type: local
            local:
              basePath: "/app/storage"
          queue:
            type: postgres
          tasks:
            tmpDir:
              path: /tmp/kestra-wd/tmp
          url: http://localhost:8080/
    ports:
      - "8080:8080"
      - "8081:8081"
    depends_on:
      kestra_postgres:
        condition: service_started
```

The postgres database exists so that Kestra remembers our Flow definitions. Without it, every time we restarted the container we'd have to rewrite our flows.

Then our task will look like this:
```yaml
tasks:
  - id: analyze_data
    type: io.kestra.plugin.scripts.python.Script
    taskRunner:
      type: io.kestra.plugin.core.runner.Process # Runs on the server/worker directly
    script: |
      import pandas as pd
      df = pd.DataFrame({'Name': ['Tom', 'Nick'], 'Age': [20, 21]})
      print(df)
```

Notice how the `taskRunner` is no longer of type `Docker` but is of type `Process` since we need Python to run on Kestra as a local procedure.


Comparatively, the Process Runner approach is faster since there's no container start up time. On the other hand, the Docker Runner approach is easier to maintain since we just need to update the task image if for example we need to update the python packages.
