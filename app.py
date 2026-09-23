import os
import sqlite3

from flask import Flask, g, jsonify, render_template, request


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.getenv(
            "DATABASE_PATH", os.path.join(app.instance_path, "todos.db")
        )
    )
    if test_config:
        app.config.update(test_config)

    database_path = os.path.abspath(app.config["DATABASE"])
    os.makedirs(os.path.dirname(database_path), exist_ok=True)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"], timeout=10)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS todo_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS todo_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (list_id) REFERENCES todo_lists (id) ON DELETE CASCADE
            );
            """
        )
        db.commit()

    def item_json(row):
        return {
            "id": row["id"],
            "list_id": row["list_id"],
            "name": row["name"],
            "completed": bool(row["completed"]),
            "created_at": row["created_at"],
        }

    def list_json(row, include_items=True):
        result = {
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
        }
        if include_items:
            items = get_db().execute(
                "SELECT * FROM todo_items WHERE list_id = ? ORDER BY id",
                (row["id"],),
            )
            result["items"] = [item_json(item) for item in items.fetchall()]
        return result

    def json_body():
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else None

    def valid_name(data):
        if data is None or not isinstance(data.get("name"), str):
            return None
        name = data["name"].strip()
        return name if 0 < len(name) <= 200 else None

    def find_list(list_id):
        return get_db().execute(
            "SELECT * FROM todo_lists WHERE id = ?", (list_id,)
        ).fetchone()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/lists")
    def get_lists():
        rows = get_db().execute("SELECT * FROM todo_lists ORDER BY id").fetchall()
        items = get_db().execute("SELECT * FROM todo_items ORDER BY id").fetchall()
        items_by_list = {row["id"]: [] for row in rows}
        for item in items:
            items_by_list[item["list_id"]].append(item_json(item))
        result = []
        for row in rows:
            todo_list = list_json(row, include_items=False)
            todo_list["items"] = items_by_list[row["id"]]
            result.append(todo_list)
        return jsonify(result)

    @app.post("/api/lists")
    def create_list():
        name = valid_name(json_body())
        if name is None:
            return jsonify({"error": "name must be between 1 and 200 characters"}), 400
        cursor = get_db().execute(
            "INSERT INTO todo_lists (name) VALUES (?)", (name,)
        )
        get_db().commit()
        return jsonify(list_json(find_list(cursor.lastrowid))), 201

    @app.get("/api/lists/<int:list_id>")
    def get_list(list_id):
        row = find_list(list_id)
        if row is None:
            return jsonify({"error": "list not found"}), 404
        return jsonify(list_json(row))

    @app.patch("/api/lists/<int:list_id>")
    def update_list(list_id):
        if find_list(list_id) is None:
            return jsonify({"error": "list not found"}), 404
        name = valid_name(json_body())
        if name is None:
            return jsonify({"error": "name must be between 1 and 200 characters"}), 400
        get_db().execute(
            "UPDATE todo_lists SET name = ? WHERE id = ?", (name, list_id)
        )
        get_db().commit()
        return jsonify(list_json(find_list(list_id)))

    @app.delete("/api/lists/<int:list_id>")
    def delete_list(list_id):
        if find_list(list_id) is None:
            return jsonify({"error": "list not found"}), 404
        get_db().execute("DELETE FROM todo_lists WHERE id = ?", (list_id,))
        get_db().commit()
        return "", 204

    @app.post("/api/lists/<int:list_id>/items")
    def create_item(list_id):
        if find_list(list_id) is None:
            return jsonify({"error": "list not found"}), 404
        name = valid_name(json_body())
        if name is None:
            return jsonify({"error": "name must be between 1 and 200 characters"}), 400
        cursor = get_db().execute(
            "INSERT INTO todo_items (list_id, name) VALUES (?, ?)", (list_id, name)
        )
        get_db().commit()
        row = get_db().execute(
            "SELECT * FROM todo_items WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify(item_json(row)), 201

    @app.patch("/api/lists/<int:list_id>/items/<int:item_id>")
    def update_item(list_id, item_id):
        row = get_db().execute(
            "SELECT * FROM todo_items WHERE id = ? AND list_id = ?",
            (item_id, list_id),
        ).fetchone()
        if row is None:
            return jsonify({"error": "item not found"}), 404

        data = json_body()
        if data is None or not ({"name", "completed"} & data.keys()):
            return jsonify({"error": "name or completed is required"}), 400

        name = row["name"]
        completed = row["completed"]
        if "name" in data:
            name = valid_name(data)
            if name is None:
                return (
                    jsonify({"error": "name must be between 1 and 200 characters"}),
                    400,
                )
        if "completed" in data:
            if not isinstance(data["completed"], bool):
                return jsonify({"error": "completed must be a boolean"}), 400
            completed = int(data["completed"])

        get_db().execute(
            "UPDATE todo_items SET name = ?, completed = ? WHERE id = ?",
            (name, completed, item_id),
        )
        get_db().commit()
        updated = get_db().execute(
            "SELECT * FROM todo_items WHERE id = ?", (item_id,)
        ).fetchone()
        return jsonify(item_json(updated))

    @app.delete("/api/lists/<int:list_id>/items/<int:item_id>")
    def delete_item(list_id, item_id):
        cursor = get_db().execute(
            "DELETE FROM todo_items WHERE id = ? AND list_id = ?",
            (item_id, list_id),
        )
        if cursor.rowcount == 0:
            get_db().rollback()
            return jsonify({"error": "item not found"}), 404
        get_db().commit()
        return "", 204

    with app.app_context():
        init_db()

    return app


app = create_app()
