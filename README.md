# AutoBacklog
AutoBacklog is a backlogging app built with Django that automatically import your PSN library. It tags your game as unplayed, played, beaten or platinumed. It also tags your games as bought, monthly game (PS+) or game catalog (PS+).

This is a personal project that I decided to share to help others. This is not clean code, this is code I wrote fast and that work. I plan to clean up the codebase.

***Important:*** This app use the NPSSO to retrieve the user's library. The NPSSO is currently stored on the database. It's "hidden" from the admin, but someone with full access to the server can get and decrypt all the NPSSOs with a few line of code. The NPSSO is required to get the user's unplayed games. I'm working on a solution to get the user's library without his NPSSO, with a client side tool to retrieve the unplayed games. The user will have to provide his NPSSO every time he wants to get his unplayed games, but it will be way more secure, as the NPSSO will only be used client-side.

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