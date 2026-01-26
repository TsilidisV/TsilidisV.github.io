---
date: 2026-01-19
categories:
  - Orchestration
  - Data Engineering
tags:
  - Kestra
  - mkdocs
title: "Introduction to Kestra"
description: "This guide introduces Kestra, a declarative orchestration platform, explaining how to define Flows using YAML, manage tasks like logging and downloading, and automate execution with Triggers and Cron."
---

# {{ title }}
{{ description }}

<!-- more -->

## What's Kestra?
Kestra is an open-source **orchestration** platform. Just like in a philharmonic orchestra there are multiple musicians performing different musical instruments and a conductor directs the whole performance, in data processes there can be multiple tools (Python, SQL, etc.) performing different jobs (downloading data, storing data, etc.) and an **orchestration** platform (Kestra) directing the whole process.

Kestra allows us to build, schedule, run, and monitor complex workflows, which Kestra calls *Flows*. The defining feature of Kestra is that it is declarative. Instead of writing complex Python or Java code to manage the state of a job (like you might in older tools), you define what you want to happen using YAML.

## Flows
In Kestra, everything is defined in YAML. Here is a standard "Hello World" flow:
```yaml
id: hello-world
namespace: com.example.learning

tasks:
  - id: say-hello
    type: io.kestra.plugin.core.log.Log
    message: Hello, Kestra!
```

There are three mandatory properties at the root level here:

1. `id`: The unique name of our flow.
1. `namespace`: They are used to group flows and provide structure. We can think of this like a folder path to keep our flows organized (e.g., company.team.project)
1. `tasks`: A list of steps meant to be executed sequentially.

We cannot change a flow's `id` or `namespace` after creation. We must create a new flow with the desired namespace and delete the old one.

The `tasks` block defines three additional properties:

1. `id`: The unique name we give to this specific step in our flow.
1. `type`: This tells Kestra which tool (or plugin) to use. The value `io.kestra.plugin.core.log.Log` is the full name of the tool which performs logging actions like saying "Hello, Kestra!" or giving important information.
1. `message`: This is a property specific to the `Log` tool. Because we selected the `Log` tool, Kestra expects us to provide a `message` to print. Had we chosen a different tool, we'd use properties relevant to that tool.

If we want to write multi-line code, for example for printing a multi-line log message, we can use the pipe character (`|`) immediately after the `script:` property. For example:
```yaml
tasks:
  - id: say-hello-multiline
    type: io.kestra.plugin.core.log.Log
    message: | 
      Hello, Kestra!
      Hello, but from a second line!
```

### Types of `tasks`
We've already seen the `Log` type of task used for logging. Let's see some more.

#### `io.kestra.plugin.core.debug.Return`  
`Return` is designed to process data and expose it as a structured output of the task. While the `Log` task just writes text to the console (which is hard for computers to read later), the `Return` task packages data so other tasks or flows can easily pick it up and use it.

Here's the basic syntax:
```yaml
- id: output_data
  type: io.kestra.plugin.core.debug.Return
  format: This is my first time using Return
```

The `format` property contains a string.

After execution, this task generates a standard output variable that we can reference later using `outputs.<return_id_name>.value`:

```yaml
id: first_retrun
namespace: company.team

tasks:
  - id: return_test
    type: io.kestra.plugin.core.debug.Return
    format: first

  - id: hello
    type: io.kestra.plugin.core.log.Log
    message: |
     It's my {% raw %} {{ outputs.return_test.value }} {% endraw %} using Return
```

### `io.kestra.plugin.core.http.Download`
`Download` is an important task used to fetch a file from a URL and store it in Kestra's internal storage. 

For example, we can download a dataset from Kestra's github repository like this:
```yaml
id: download_dataset
type: io.kestra.plugin.core.http.Download
uri: "https://raw.githubusercontent.com/kestra-io/datasets/main/csv/orders.csv"
```

This task produces a single, critical output, the `uri`. The file is not saved to the local file system of the worker, but rather in Kestra's internal storage. The file in our example will be located at `outputs.download_dataset.uri`, which we could pass to another Kestra task by writing `{% raw %} {{ outputs.download_dataset.uri }} {% endraw %}`.

### `io.kestra.plugin.scripts.shell.Commands`
`Commands` is one of the most versatile tasks in Kestra. It allows us to execute a list of Shell commands (Bash, sh, etc.) sequentially.

We can think of it as a "Universal Adapter". If there isn't a specific Kestra plugin for a tool we need (like there is for Python as we will see next), but that tool has a Command Line Interface (CLI) (like `git`, `aws`, `terraform`, or `curl`) we can use this task to run it. It's also very useful for moving, renaming, zipping, or transforming files between other tasks.

let's see some of its key properties:

- `commands`. It's a **required** field and accepts a list of shell commands to execute one by one.
- `taskRunner`: Defines where to run the commands, for example inside a Docker container.
- `outputFiles`: Exports created files by our commands so that we can use them by other tasks.

Let's take a look at this flow:

```yaml
id: guide_to_commands
namespace: company.team

tasks:
  - id: generate_data
    type: io.kestra.plugin.scripts.shell.Commands
    taskRunner:
      type: io.kestra.plugin.scripts.runner.docker.Docker
      image: ubuntu:latest
    commands:
      - echo "id,name" > output.csv
      - echo "1,John" >> output.csv
      - echo "2,Jane" >> output.csv
    outputFiles:
      - output.csv  # This tells Kestra to save this file to internal storage
```

Let's begin with the `outputFiles` property which makes the `output.csv` file accessible for other tasks. It can be accessed by writting `{% raw %} {{ outputs.generate_data.outputFiles['output.csv'] }} {% endraw %}`


#### `taskRunner`
Let's take a detour and take a look at the `taskRunner` property. `taskRunner` is a configuration setting that defines where and how our commands will be executed. 

Instead of just running everything on the Kestra server, `taskRunner` allows us to dispatch that work to a Docker container, a Kubernetes pod, or a remote cloud instance. Let's see some of the `taskRunner` types:

- Local (`io.kestra.plugin.core.runner.Process`): Runs directly on the Kestra Worker as a local process.
- Docker (`io.kestra.plugin.scripts.runner.docker.Docker`): Runs the script inside a Docker container.
- Cloud (`io.kestra.plugin.gcp.cli.GCloudCLI`, `io.kestra.plugin.aws.cli.AwsCLI`, etc.): Runs the script on cloud platforms like Google Cloud, AWS, etc.

The Docker type has the interesting property called `image` which can configure the image for the task. 

Earlier we used:
```yaml
taskRunner:
  type: io.kestra.plugin.scripts.runner.docker.Docker
  image: ubuntu:latest
```

This means that in our case we use the Docker image for the latest ubuntu version.


### Running Python.

Let's look at another example and try to run Python:
```yaml
id: python_in_shell
type: io.kestra.plugin.scripts.shell.Commands
taskRunner:
  type: io.kestra.plugin.scripts.runner.docker.Docker
  image: python:3.9-slim
commands:
  - pip install requests
  - python -c "import requests; print('Requests library installed and verified!')"
```

This time, we change our docker image from `ubuntu:latest` to `python:3.9-slim` allowing us to use `pip` and `Python`.

However, there's an even better way to run Python in Kestra, with the use of `io.kestra.plugin.scripts.python.Script`. For more, check out this article _____________________________________________________

### Inputs
We usually want flows to react to data like a filename, a date, or a user's name. To do this we use inputs. Inputs are defined at the top level of our flow (alongside `id` and `tasks`).

Each input needs:

- `id`: The name of the variable
- `type`: The data type. For example, for text we use `STRING` and for integers we use `INT`

Now that we know how to define some inputs, we need to actually use them in our flow. Kestra uses a templating syntax (similar to Jinja or Liquid) to inject values. To access an input, you use double curly braces like this: `{% raw %} {{ inputs.your_input_id }} {% endraw %}`.

Hence, this is an example flow:

```yaml
id: guide_to_inputs
namespace: company.team

inputs: 
  - id: user_name 
    type: STRING
  - id: age
    type: INT

tasks:
  - id: hello
    type: io.kestra.plugin.core.log.Log
    message: Hello, I'm {% raw %} {{ inputs.user_name }} {% endraw %} and I'm  {% raw %} {{ inputs.age }} {% endraw %} years old
```

### Trigger
With our current knowledge, we still have to manually click the execute button to run a flow. The real power of orchestration comes from Triggers, that is, telling Kestra to run the flow automatically based on an event or a schedule.

`triggers` is a list that sits at the top level, just like `inputs` and `tasks`. The most common trigger is the Schedule. It's of type `io.kestra.plugin.core.trigger.Schedule` and has the important property `cron` which defines the trigger interval. Let's give an example:

```yaml
id: my_first_trigger
namespace: company.team

triggers:
  - id: hourly_running
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "@hourly"

tasks:
  - id: hello
    type: io.kestra.plugin.core.log.Log
    message: Hello, Kestra!
```

This Flow will run every hour because we used the shorthand string `@hourly`

!!! note

    The quotation marks around @hourly are important. In YAML, certain characters are "reserved" because they have special meanings to the parser. The `@` symbol is one of these. It's reserved for future language features. If we write `cron: @hourly` without quotes, the YAML parser tries to interpret the @ as a special command rather than just the text "`@hourly`", and it throws an error. By adding quotes (`"@hourly"`), we're telling the parser: "Treat everything inside here as a simple string of text. Do not try to interpret the symbols."

Here are the most common "shortcuts" supported by Kestra (and many other tools for that matter):

| Expression | Meaning |
| --- | --- |
| `"@hourly"` | Run once an hour at the beginning of the hour (e.g., 1:00, 2:00). |
| `"@daily"` | Run once a day at midnight (00:00). |
| `"@weekly"` | Run once a week at midnight on Sunday. |
| `"@monthly"` | Run once a month at midnight on the first day of the month. |

#### The Standard Syntax (The 5 Stars)

While shortcuts are handy, real power comes from understanding the standard cron syntax. It consists of 5 fields separated by spaces:

```minute hour day_of_month month day_of_week```

For example, `"0 12 * * *"` means "At minute 0, of hour 12 (noon), every day, every month, every day of the week.". `"30 9 * * 1"` means "30th minute, 9th hour, any day of the month, any month, Monday."

Let's see some more examples so we can understand the syntax a bit better:

| Expression            | Meaning                                            |
| -----------------     | -------------------------------------------------- |
| `"0 12 * * *"`        | Every day at 12:00                                 |
| `"30 9 * * 1"`        | Every Monday at 9:30                               |
| `"12 16 * 2 7"`       | Every Sunday of February at 16:12                  |
| `"0 0 3 2 *"`         | Every February 3rd at 00:00                        |
| `"0 9 * * 1-5"`       | Monday through Friday at 09:00                     |
| `"0 0 * * 1,3,5"`     | Monday, Wednesday, and Friday at 00:00             |
| `"15 14 1 * *"`       | Every 1st of every month at 14:15                  |
| `"*/15 * * * *"`      | Runs every 15 minutes                              |
| `"0 */2 * * *  "`     | Every 2 hours at minute 0                          |
| `"0 0 1 */3 *"`       | Every 3 months on the 1st day at midnight          |
| `"23 0-20/2 * * *"`   | At minute 23 past every 2nd hour from 0 through 20 |

There is a handy site called [crontab.guru](https://crontab.guru/) that we can use to double-check our expressions. It translates the code into plain English.

## Summary
Let's create a final Flow which will tie together everything we learned:

```yaml
id: monthly_report_demo
namespace: company.analytics
description: "Generates a report and notifies the team."

# 1. INPUTS: Dynamic data passed at runtime
inputs:
  - id: user_name
    type: STRING
    defaults: "Red Team"

# 2. TASKS: The actual steps to execute
tasks:
  # Step 1: Log a message using the input
  - id: log_start
    type: io.kestra.plugin.core.log.Log
    message: "Starting report generation for {% raw %} {{ inputs.user_name }} {% endraw %}"

  # Step 2: Simulate fetching data (returns a value)
  - id: fetch_data
    type: io.kestra.plugin.core.debug.Return
    format: "Report Date: {% raw %} {{ now() }} {% endraw %}"

  # Step 3: Run a script (Python example)
  - id: process_data
    type: io.kestra.plugin.scripts.python.Script
    script: |
      print("  {% raw %}  {{ outputs.fetch_data.value }}  {% endraw %}  \n Let's begin the report by ...")

# 3. TRIGGERS: How the flow starts automatically
triggers:
  - id: monthly_schedule
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "0 9 1 * *" # Runs at 9:00 AM on the 1st of every month
```

This Kestra flow runs at 9:00 AM on the 1st of every month, logs a message using the given input, simulates the fetching of data by returning a value and executes toy Python script that print the aforementioned value.

A new detail added is the use of `defaults` property in `inputs`. Without it, the Flow would fail because it's dependent on a user input which wouldn't be given every minute that the Flow would get triggered. Hence, if we provide the name "Blue Team" when we first execute the Flow, it would run for Blue Team, and in all subsequent runs it would run for Red Team.


