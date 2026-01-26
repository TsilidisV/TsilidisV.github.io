---
date: 2026-01-14
categories:
  - Coding
  - Python
tags:
  - productivity
  - mkdocs
title: "Introduction to `uv`"
description: "Discover `uv`, a high-speed Python package manager, and see how to initialize projects, lock dependencies, and share reproducible environments instantly."
---

# {{ title }}
{{ description }}


<!-- more -->

## What's `uv`?
`uv` is a relatively new, extremely fast Python package and project manager written in Rust.

For data science, where installing heavy libraries like `PyTorch`, `TensorFlow`, or `Pandas` can be slow and dependency conflicts are common, `uv` aims to be a much faster and more reliable replacement for tools like `pip`, `pip-tools`, and even `poetry`.

Let's begin by installing `uv`. For Windows we open PowerShell and run:
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```
and for Linux/Mac we open bash and run
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Project Initialization: `uv init`
Start by making a new folder, called for example `uv_test` and open a terminal inside of that folder. Next, run
```bash
uv init . --python=3.13
```
In your folder, you'll see some new files:
```bash
uv_test/
├── .python-version
│   main.py
│   pyproject.toml
└── README.md
```
`main.py` is just a toy script containing:
```python
def main():
    print("Hello from uv-test!")

if __name__ == "__main__":
    main()
```
and `README.md` is just an empty Markdown file.
The important files are `.python-version` and `pyproject.toml`.

`.python-version` contains the Python version we specified while initializing the project, namely `3.13`.

The `pyproject.toml` file is the heart of our project. It’s a standardized configuration file used by almost all modern Python tools, but `uv` uses it to manage our dependencies with precision.

Right now, `pyproject.toml` will look something like this:
```toml
[project]
name = "uv-test"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.13"
dependencies = []
```

- `name`: The official name of our project.
- `version`: Our project's version number. We'd bump this from 0.1.0 to 0.1.1 when you make changes.
- `requires-python`: This is a guardrail. It tells `uv`: "Refuse to run this project if the user has an old Python version (like 3.8)."
- `dependencies`: The most crucial part. Here go the libraries our code needs in order to run. For example `pandas>=2.2.0`, which means give me `pandas` but it must be version 2.2.0 or newer. `uv` manages this list for us automatically when we run `uv add`.

## Adding Dependencies: `uv add`

Let's assume that our project requires `pandas`. If we were to use `pip`, we'd run `pip install pandas`, but that won't update our project automatically. With `uv`, we can do both automatically:
```bash
uv add pandas
```
What just happened? uv did three things in the blink of an eye:

- *Resolved*: It calculated which version of pandas works with your python version.
- *Installed*: It downloaded pandas and set up a virtual environment (check for a hidden folder called .venv).
- *Locked*: It created a new file called uv.lock.

Let's take a look at the pyproject.toml again:
```toml
[project]
name = "uv-test"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "pandas>=2.3.3",
]
```
We now see the dependencies containing `"pandas>=2.3.3"`.

## Running code: `uv run`
Let's change the toy script in `main.py` with something that requires `pandas`:
```python
import pandas as pd

# Create a simple dataset
data = {
    "Fruit": ["Apples", "Bananas", "Cherries"],
    "Amount": [10, 20, 15]
}

# Load it into a Pandas DataFrame
df = pd.DataFrame(data)

# Calculate a quick stat
total_fruit = df["Amount"].sum()

print("--- Data Science Test ---")
print(df)
print(f"\nTotal Fruit: {total_fruit}")
```

Had we not used `uv`, now we'd have to activate our virtual environment, and then run `python main.py`.

Thankfully, `uv` can manage virtual environments on its own due to the `.venv` folder. All we have to do is replace `python` in `python main.py` with `uv run`. Hence, we have:
```bash
uv run main.py
```
which shows the dataframe along with the total number of fruits in the terminal.

## File sharing: `uv sync`
Imagine we need to send this project to a colleague (or move it to a cloud server). We would never send the `.venv` folder. It is huge, contains thousands of files, and won't work on a different operating system.

Instead, we only send the recipe files (`pyproject.toml` and `uv.lock`) and the code (`main.py`). 

!!!note

    Always commit `uv.lock` and `pyproject.toml` to version control.

Let's pretend we just downloaded this project on a brand new computer. We will simulate this by deleting our environment.

Let's delete the `.venv` folder. We'd send the rest of our files to some colleague. Now, our colleague only has to run
```bash
uv sync
```


Perfect! No more "But, it works on my machine!".

## Summary
We have mastered the core cycle of using `uv` for data science projects:

- `uv init . --python=<version>` : Creates the project skeleton in the current folder for a specified Python version.
- `uv add <library>`: Installs a library and locks the version (updating both `pyproject.toml` and `uv.lock`).
- `uv run <script>`: Runs our code using the project's isolated environment without needing manual activation.
- `uv sync`: The "Restore" button. It makes sure our `.venv` perfectly matches our `uv.lock`.