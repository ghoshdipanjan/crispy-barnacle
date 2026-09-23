# Shopping List

A small Flask website for creating shopping lists and checking off items while
you shop. The browser uses the JSON API for every list and item operation, and
SQLite keeps data between requests.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
flask --app app run --debug
```

Open <http://127.0.0.1:5000>. Run the tests with:

```bash
pytest
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET`, `POST` | `/api/lists` | List or create shopping lists |
| `GET`, `PATCH`, `DELETE` | `/api/lists/<id>` | Read, rename, or delete a list |
| `POST` | `/api/lists/<id>/items` | Add an item |
| `PATCH`, `DELETE` | `/api/lists/<id>/items/<item-id>` | Update or delete an item |
| `GET` | `/api/health` | Check application health |

Create and update requests accept JSON. A list or item name is provided as
`{"name": "Groceries"}`. An item is checked off with
`{"completed": true}`.

## Azure App Service

Create a Linux Python Web App, deploy this repository, and set its startup
command to:

```bash
gunicorn --bind=0.0.0.0:$PORT app:app
```

The default SQLite database is `instance/todos.db`. For a durable mounted
location in Azure, add an application setting such as
`DATABASE_PATH=/home/data/todos.db`.