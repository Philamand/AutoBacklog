# AutoBacklog
AutoBacklog is a backlogging app built with Django that automatically import your PSN library, distributed under the GNU Affero General Public License v3.0. It tags your game as unplayed, played, beaten or platinumed. It also tags your games as bought, monthly game (PS+) or game catalog (PS+).

This is a personal project that I decided to share to help others. My priority was not to write clean code but code that works and that is fast to write. A code cleanup will happen eventually.

## How to use ?
### In vscode
I use vscode with devcontainers to build this app. Here is how to set it up.

Create a file named `.devcontainer/devcontainer.json` and paste this:

```json
{
    "name": "AutoBacklog",
    "dockerComposeFile": "../docker-compose.dev.yml",
    "service": "autobacklog",
    "workspaceFolder": "/app",
    "customizations": {
        "vscode": {
            "extensions": [
                "ms-python.python",
                "charliermarsh.ruff"
            ]
        }
    },
    "postCreateCommand": "uv run manage.py makemigrations && uv run manage.py migrate"
}
```

Create a file named `.vscode/settings.json` and paste this:

```json
{
    "python.testing.unittestEnabled": true,
    "python.testing.pytestEnabled": false,
    "python.testing.unittestArgs": [
        "-p",
        "*test*.py"
    ]
}
```

Create a file named `.env` and copy/paste the content of .example.dev.env. Make sure to add your own reddit client ID and secret if you have one.

Open the command palette with `ctrl + shift + p` and select `Dev Containers: Rebuild Container`. Run `uv run manage.py collectstatic`, then acces [localhost:8000](localhost:8000)

### In production
Create the following files:

- .env
- .db.env
- .umami.env
- .umami_db.env

and copy/paste the corresponding .example.x.env file's content. Make sure to replace the values with your own. ***Do not reuse the dev fernet key***. To generate one, use:

```python
from cryptography.fernet import Fernet

key = Fernet.generate_key()
print(key)
```

If you use Umami, do not forget to add the script tag in the base.html.

Then run `docker compose up` and `docker compose run autobacklog uv run manage.py rundramatiq`. After the first run, be sure to run `docker compose run autobacklog uv run manage.py makemigrations`, `docker compose run autobacklog uv run manage.py migrate` and `docker compose run autobacklog uv run manage.py collectstatic`

### Admin Setup

In the admin, head to Psn accounts and add a PSN account with it's NPSSO to be able to access tha PlayStation API.

Then, downlad the `json/All_Titles.json` file from this repository: https://github.com/andshrew/PlayStation-Titles/tree/main/Json and import it in the Play station titles section of the admin.