from app import app, tasks


def test_health_endpoint():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_login_success_and_create_task():
    tasks.clear()
    client = app.test_client()

    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )

    assert login.status_code == 200
    assert "Minhas Tarefas" in login.get_data(as_text=True)

    create = client.post(
        "/tasks/add",
        data={"task": "Estudar DevSecOps"},
        follow_redirects=True,
    )

    assert create.status_code == 200
    assert "Estudar DevSecOps" in create.get_data(as_text=True)


def test_login_failure():
    client = app.test_client()

    response = client.post(
        "/login",
        data={"username": "admin", "password": "senhaerrada"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Usuário ou senha inválidos" in response.get_data(as_text=True)
