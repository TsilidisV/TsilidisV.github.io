---
date: 2026-01-12
categories:
  - Coding
  - Python
  - Docker
  - Data Science
  - Data Engineering
tags:
  - productivity
  - mkdocs
title: "Introduction to Docker"
---
# {{ title }}

This guide is a practical, Python-centric introduction to Docker that takes you from basic concepts like images and containers to building and optimizing efficient data pipelines.

<!-- more -->

## What's docker?
Docker is a virtualization tool which can automate the deployment of applications within lightweight containers, enabling them to run consistently across different computing environments, like a local machine or a web server.

## Preliminaries
Let's assume that we have a very basic project structure, with a single `python` file called `pipeline.py` located inside the `src/` folder, and a `requirements.txt` file in the root directory.
```bash
project/
├── src/
│   ├── pipeline.py
└── requirements.txt
```
`pipeline.py` is just a toy script that creates a `DataFrame` and prints it:
```python
import pandas as pd

df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

print(df)
```
`requirements.txt` contains only the dependence of our code to `pandas`:
```text
pandas==2.3.3
```

## Docker Concepts
### Image
A docker image is a read-only template. Just like a Python `class` or a blueprint for a building. They contain everything the application needs to run:
- The operating system (usually a slim version of Linux)
- The code (python scripts)
- The dependencies (pandas, NumPy, etc.)

Just like a Python `class`, it doesn't do anything on its own. It just sits there waiting to be instantiated.

### Container
A docker container is a running instance of an image. Just like a Python `object` or the building based on a blueprint. When you tell Docker to run an image it creates a container. You can have multiple containers running from the same docker image simultaneously. An important aspect of containers is that they are ephemeral, meaning that if a container is deleted, any files created inside of it are gone forever.

### Volumes
Due to the ephemerality of containers, we need a way to save our data so they persist when a container stops. Volumes allow us to map a folder on our actual computer (host) to a folder inside the container.

## Building a Blueprint: The Dockerfile
### FROM
A `dockerfile` is just a text file with instructions on how to build an image.
Let's place an empty `dockerfile` in the root of our directory:
```bash
project/
├── src/
│   ├── pipeline.py
│   requirements.txt
└── dockerfile
```

 One of the first commands you can see in a dockerfile is the `FROM` command. This tells Docker to inherit from a parent image. For example
```dockerfile
FROM python:3.14-slim
``` 
this command tells Docker to inherit from an already existing image called python:3.14-slim. This image contains python version 3.14 and contains a "slim" version of it rather than the full standard version. A standard Python image can be quite large (nearly 1GB), while a slim version strips out unnecessary tools, bringing it down to under 200MB. This makes your data pipelines start up much faster and saves money on storage.

### WORKDIR
`WORKDIR` command allows us to set up a workspace inside the image so we aren't putting files into the root system:
```dockerfile
WORKDIR /app
```
This creates a folder called `app` making it the default location for all the files that we are going to move in the image.

### COPY
`COPY` makes a copy of our files into `\app` folder in the image. Assuming that we have a `requirements.txt` and a `pipeline.py` file we can write: 
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
COPY src/pipeline.py ./src/
```

### RUN
We can use the `RUN` command to execute build commands, such as installing the requirements from the `requirements.txt`. We do this by including the command:
```dockerfile
RUN pip install -r requirements.txt
```
with the `-r` meaning that pip will read the list inside that file rather than searching online for a package named `requirements.txt`.

### CMD
So far the image has the OS, the code, and the libraries installed. But we haven't told the container what to actually do when it starts up. 

We want it to execute python pipeline.py. The Docker instruction for this is `CMD`. Unlike the other commands, `CMD` is often written as a list of strings (like `["executable", "file"]`).

Hence, assuming that we want to execute the `pipeline.py` file with `python`, we can write:
```dockerfile
CMD ["python", "src/pipeline.py"]
```

Hence our dockerfile is:
```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
COPY src/pipeline.py ./src
RUN pip install -r requirements.txt
CMD ["python", "src/pipeline.py"]
```

## Keeping it Clean: The .dockerignore file

Before we build our image, there is one small but important detail we should address: the **build context**.

When we run `docker build`, Docker doesn't just read the `dockerfile`. It first bundles up *everything* in our current directory and sends it to the Docker daemon. This bundle is called the "build context."

If we have a local virtual environment (like `venv/`), massive data files, or hidden git history folders (`.git`) in our project folder, Docker will try to copy all of them into the build context. This makes the build process slow and the resulting image unnecessarily large.

### How to use it

To prevent this, we use a `.dockerignore` file. It works exactly like a `.gitignore` file. We simply list the file patterns we want Docker to ignore.

Let's place a `.dockerignore` file in our root directory:

```bash
project/
├── src/
│   ├── pipeline.py
├── requirements.txt
├── dockerfile
└── .dockerignore

```

Inside `.dockerignore`, we can list the things we don't want to copy:

```text
# Ignore the version control folder
.git

# Ignore python cache files
__pycache__

# Ignore local virtual environments (if you have one)
venv/
env/

# Ignore local data files (if you don't want them baked into the image)
*.csv
*.parquet

```

By adding this file, we ensure that when we run the build command, Docker only "sees" the essential source code and requirements, keeping our image clean and our build time fast.

## Building the Image

To build the image from the `dockerfile`, we first need to open a terminal in the directory where the `dockerfile` is located. Then, all we have to do is run:

```bash
docker build -t my-data-pipeline .

```

Let's see what each of those flags does:

* `build`: The main command that builds the image.
* `-t <tag>`: Tags the image with a name, in our case `my-data-pipeline`. This makes it easier to reference later.
* `.`: This tells Docker to look for the `dockerfile` in the **current directory**. It also defines the build context. Because we added a `.dockerignore` file, only the necessary files are sent to the Docker daemon, making the start of the build process instant.

Aaand it's done. This is how you build an image. We should note that the command `python src/pipeline.py` is not executed yet; we have simply created the blueprint.

## Running the Container
All we have to do now is run
```bash
docker run my-data-pipeline
```
This tells Docker to find the image with the tag `my-data-pipeline` and create a container of this image and execute the command `python src/pipeline.py`. Naturally, we notice that the system prints the `DataFrame` we specified in `src/pipeline.py`.

Essentially, running  `docker run my-data-pipeline` is the same as running `python src/pipeline.py` but without having to manually install the specific python version and dependencies version.

## Layer Caching
Let's assume that we want to change something in our code. For example add a new feature or fix a bug. For instance, let's add another row to the dataframe we create in `pipeline.py`:
```python
import pandas as pd

df = pd.DataFrame({"A": [1, 2, 10], "B": [3, 4, 20]})

print(df)
```

Now, we need to rebuild our docker image. Hence we run:
```bash
docker build -t my-data-pipeline .
```

If we do that, we notice that docker redownloads `pandas`. That sucks, we just added a new row to the `DataFrame` and we have to wait for all of our dependencies to redownload? Thankfully, no!

When we build an image (`docker build`), Docker looks sequentially at the commands in our Dockerfile. For each command, it checks if it has an existing layer in its cache that matches that exact command and the files involved.
- Cache Hit: If nothing has changed, Docker reuses the existing layer instantly.
- Cache Miss: If something has changed, Docker rebuilds that layer and every layer after it.

The goal of writing a good Dockerfile is to maximize cache hits. We want the layers that change the least often to be at the top, and the layers that change the most often to be at the bottom.

The `dockerfile` we used earlier copies the source files before installing the dependencies. With our new knowledge about layer caching, we should first copy  `requirements.txt` and install the listed dependences, and then copy the source code, as it's more likely to change.

Hence, our `dockerfile` should be:
```dockerfile
FROM python:3.14-slim

WORKDIR /app

# 1. Install dependencies first (for caching)
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2. Copy the actual application code
COPY src/pipeline.py ./src/

# 3. specify the command to run on startup
CMD ["python", "src/pipeline.py"]
```

With this `dockerfile`, any time we change the source code, the dependencies won't be reinstalled. They will only be reinstalled if we change `requirements.txt`. Since source code changes frequently but dependencies do not, this structure ensures we rarely have to wait for pip install to run again.