---
date: 2026-02-05
categories:
  - Data Orchestration
  - Infrastructure as Code (IaC)
  - Data Engineering
tags:  

 - Kestra 
 - Docker 
 - Makefile 
 - DRY 
 - Automation

title: "Building a Clean Data Loading Stack: Kestra, Terraform, and the Art of Not Repeating Yourself"
description: "Integrate a data loading pipeline with Terraform and Kestra through Docker and a Makefile. It solves the common problem of manual configuration by using Terraform outputs to dynamically generate environment variables, ensuring a 'Single Source of Truth' for infrastructure and orchestration."
---

# {{ title }}
{{ description }}

<!-- more -->

Start a data project today, and you’ll likely face the "Configuration Spaghetti" problem. You have a bucket name in Terraform, a Service Account key in a JSON file, and an orchestration tool that needs both.

Usually, people copy-paste these values into five different places. But, personally, I love the **DRY (Don't Repeat Yourself)** principle.

In this post, I’ll walk you through how we built a clean, automated Data Engineering stack using **Kestra**, **Terraform**, and **Docker**, tied together with a robust **Makefile**.

The full code for this article can be found [here](https://github.com/TsilidisV/dezoomcamp2026_homework/tree/main/03-data-warehouse).

## 1. The Blueprint (Structure)

First, let's look at the home we built. We wanted a structure where infrastructure code lives separately from orchestration logic, but they talk to each other seamlessly.

```text
my-data-project/
├── .env                     # The secret sauce (Auto-generated, GitIgnored!)
├── docker-compose.yml       # Kestra & Postgres services
├── Makefile                 # The command center
├── infrastructure/          # Terraform (The Source of Truth)
│   ├── main.tf              # Bucket & IAM definitions
│   ├── outputs.tf           # 📢 The Bridge to Kestra
│   └── keys/                # Service Account JSON (kept safe/ignored)
└── orchestration/           # Kestra Flows
    └── _flows/              # Mounted directly to Kestra for hot-reloading
        ├── batch_runner.yml
        └── data_ingest.yml

```

**Why this rocks:**

* **Separation of Concerns:** Terraform handles the resources. Kestra handles the orchestration.
* **Security:** Our keys stay in `infrastructure/keys/` and are never committed to Git (thanks to `.gitignore`).

## 2. Terraform: The Loudspeaker

The magic starts with Terraform. We didn't just create a bucket; we made sure Terraform *announced* what it created.

In `infrastructure/outputs.tf`, we explicitly exposed the values Kestra needs:

```hcl
output "bucket_name" {
  value       = google_storage_bucket.local_variable_name_for_bucket.name
  description = "The generated name of the GCS bucket"
}
```

This is crucial. By outputting the value, we allow other tools (like our Makefile) to read it programmatically via `terraform output -raw bucket_name`. No more logging into the GCP console to copy the id of our bucket.

---

## 3. The "Glue": A Makefile with Superpowers

Here is where the real engineering happened. We needed a way to get that Terraform output and our Service Account JSON key into Kestra without hardcoding them.

Enter the **Makefile**. Specifically, our `generate-env` target:

```makefile
generate-env:
	@echo "🔗 Generating .env file for Kestra..."
    # 1. Ask Terraform for the bucket name
    @echo "ENV_GCS_BUCKET=$$(terraform -chdir=$(TF_DIR) output -raw bucket_name)" > .env
    
    # 2. Read the Key -> Remove Newlines -> Base64 Encode -> Save
    @echo "SECRET_GCP_CREDS=$$(cat infrastructure/keys/service-account.json | tr -d '\n' | base64 -w 0)" >> .env

```

First of all, we pass the bucket name to the `.env` file by the name `ENV_GCS_BUCKET`. This will allow us to reference inside our Kestra flow by writing {% raw %}`"{{ env.gcs_bucket }}"`{% endraw %}.

Additionally, we encode the JSON key into Base64. Why? Because passing raw JSON (with all its quotes and curly braces) inside environment variables is a nightmare that breaks things. Base64 turns it into a safe, unbreakable string.


## 4. Kestra & Docker: The "Hot Reload" Setup

We run Kestra using Docker Compose, but we tuned it for a developer-friendly experience.

### Reading the Secrets

We simply point Docker to the `.env` file our Makefile generated.

```yaml
services:
  kestra:
    env_file:
      - .env  # Loads ENV_GCS_BUCKET and SECRET_GCP_CREDS

```

### Hot Reloading Flows

Instead of using the UI to upload flows every time we change a line of code, we mounted our local folder directly into the container:

```yaml
    volumes:
      - ./orchestration/_flows:/docker_folder
    environment:
      KESTRA_CONFIGURATION: |
        micronaut:
          io:
            watch:
              paths:
                - /docker_folder  # Kestra watches this folder for changes!

```

Now, when we save a YAML file in VS Code, Kestra updates instantly. 


## 5. The Flows: Parent & Child

We structured our pipeline into two parts to keep things modular.

### The Child: `data-ingest`

This flow does the heavy lifting. It accepts `taxi`, `year`, and `month` as inputs.
Crucially, it decodes our secret credential on the fly:

```yaml
pluginDefaults:
  - type: io.kestra.plugin.gcp
    values:
      # The Decode Step: Turning our Base64 env var back into JSON
      serviceAccount: {% raw %} "{{ secret('GCP_CREDS') }}" {% endraw %}
      bucket: {% raw %} "{{ envs.gcs_bucket }}" {% endraw %}

```

### The Parent: `batch-runner`

This flow is the manager. It uses the `ForEach` task to iterate over a list of months and trigger the child flow for each one.

```yaml
tasks:
  - id: run_for_each_month
    type: io.kestra.plugin.core.flow.ForEach
    values: ["01", "02", "03"]
    tasks:
      - id: call_ingest
        type: io.kestra.plugin.core.flow.Subflow
        flowId: data-ingest
        inputs:
          month: {% raw %} "{{ taskrun.value }}" {% endraw %}

```

## 6. The Grand Finale: `make demo`

Finally, we wanted a single command to prove everything works. But we faced a classic race condition: Docker says "I'm up!" seconds before the Java application (Kestra) is actually ready to receive traffic.

If we tried to `curl` the API immediately, it failed.

We solved this with a robust **Wait Loop** in our Makefile:

```makefile
wait-for-kestra:
    @echo "⏳ Waiting for Kestra..."
    # Poll the Health endpoint on port 8081 until we get a 200 OK
	@bash -c 'until curl -u "admin@kestra.io:Admin1234" --output /dev/null \
		--silent --head --fail http://localhost:8081/health; do \
		printf "."; \
		sleep 5; \
	done'

```

Now, we just type:

```bash
make demo
```

And the system:

1. Builds the Infrastructure (Terraform).
2. Generates the Config (Makefile).
3. Starts the Containers (Docker).
4. **Waits patiently** for health checks.
5. Triggers the flow automatically.

Now the files we want will patiently wait for us inside our GCP bucket!

## Closing Thoughts

This stack is more than just "getting it to run." It’s about building a workflow that respects your time. No manual copying of keys, no UI dragging-and-dropping, and no wondering "which bucket was that again?"
