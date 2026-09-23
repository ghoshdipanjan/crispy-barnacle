import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": tmp_path / "test.db"})
    return app.test_client()


def test_list_and_item_lifecycle(client):
    response = client.post("/api/lists", json={"name": " Groceries "})
    assert response.status_code == 201
    todo_list = response.get_json()
    assert todo_list["name"] == "Groceries"
    assert todo_list["items"] == []

    response = client.post(
        f"/api/lists/{todo_list['id']}/items", json={"name": "Milk"}
    )
    assert response.status_code == 201
    item = response.get_json()
    assert item["completed"] is False

    response = client.patch(
        f"/api/lists/{todo_list['id']}/items/{item['id']}",
        json={"completed": True},
    )
    assert response.get_json()["completed"] is True

    stored = client.get(f"/api/lists/{todo_list['id']}").get_json()
    assert stored["items"][0]["name"] == "Milk"
    assert stored["items"][0]["completed"] is True

    assert (
        client.delete(
            f"/api/lists/{todo_list['id']}/items/{item['id']}"
        ).status_code
        == 204
    )
    assert client.delete(f"/api/lists/{todo_list['id']}").status_code == 204
    assert client.get("/api/lists").get_json() == []


def test_validation_and_missing_resources(client):
    assert client.post("/api/lists", json={"name": "  "}).status_code == 400
    assert client.post("/api/lists", data="not json").status_code == 400
    assert client.get("/api/lists/999").status_code == 404
    assert (
        client.post("/api/lists/999/items", json={"name": "Milk"}).status_code
        == 404
    )

    todo_list = client.post("/api/lists", json={"name": "Shop"}).get_json()
    item = client.post(
        f"/api/lists/{todo_list['id']}/items", json={"name": "Bread"}
    ).get_json()
    assert (
        client.patch(
            f"/api/lists/{todo_list['id']}/items/{item['id']}",
            json={"completed": "yes"},
        ).status_code
        == 400
    )


def test_home_and_health(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"My Lists" in response.data
    assert client.get("/api/health").get_json() == {"status": "ok"}
