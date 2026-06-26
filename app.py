import logging
import os
import secrets
from functools import wraps
from logging.handlers import SysLogHandler

from flask import Flask, Response, redirect, request, session, url_for

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # nosec B105 - senha padrão apenas para laboratório

tasks = []


def configure_logger():
    logger = logging.getLogger("task-manager")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(name)s: %(levelname)s %(message)s")

    try:
        if os.path.exists("/dev/log"):
            handler = SysLogHandler(address="/dev/log")
        else:
            handler = logging.StreamHandler()
    except Exception:
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = configure_logger()


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("authenticated"):
            logger.warning("SECURITY_EVENT unauthorized_access path=%s ip=%s", request.path, request.remote_addr)
            return redirect(url_for("login"))
        return function(*args, **kwargs)

    return wrapper


@app.route("/")
def index():
    if session.get("authenticated"):
        return redirect(url_for("task_list"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == ADMIN_USER and password == ADMIN_PASSWORD:
            session["authenticated"] = True
            session["username"] = username
            logger.info("AUTH_SUCCESS user=%s ip=%s", username, request.remote_addr)
            return redirect(url_for("task_list"))

        logger.warning("AUTH_FAILURE user=%s ip=%s", username, request.remote_addr)
        error = "Usuário ou senha inválidos."

    return f"""
    <h1>Sistema de Gestão de Tarefas</h1>
    <p style='color:red'>{error}</p>
    <form method="post">
        <label>Usuário:</label><br>
        <input name="username"><br><br>
        <label>Senha:</label><br>
        <input name="password" type="password"><br><br>
        <button type="submit">Entrar</button>
    </form>
    <p>Usuário de teste: admin / admin123</p>
    """


@app.route("/logout")
def logout():
    user = session.get("username", "unknown")
    session.clear()
    logger.info("LOGOUT user=%s ip=%s", user, request.remote_addr)
    return redirect(url_for("login"))


@app.route("/tasks")
@login_required
def task_list():
    items = "".join(
        f"<li>{task} <a href='/tasks/delete/{index}'>Excluir</a></li>"
        for index, task in enumerate(tasks)
    )

    return f"""
    <h1>Minhas Tarefas</h1>
    <form method="post" action="/tasks/add">
        <input name="task" placeholder="Nova tarefa">
        <button type="submit">Adicionar</button>
    </form>
    <ul>{items}</ul>
    <a href="/logout">Sair</a>
    """


@app.route("/tasks/add", methods=["POST"])
@login_required
def add_task():
    task = request.form.get("task", "").strip()

    if task:
        tasks.append(task)
        logger.info("TASK_CREATED user=%s task=%s ip=%s", session.get("username"), task, request.remote_addr)

    return redirect(url_for("task_list"))


@app.route("/tasks/delete/<int:index>")
@login_required
def delete_task(index):
    if 0 <= index < len(tasks):
        removed = tasks.pop(index)
        logger.info("TASK_DELETED user=%s task=%s ip=%s", session.get("username"), removed, request.remote_addr)

    return redirect(url_for("task_list"))


@app.route("/health")
def health():
    return {"status": "ok", "service": "task-manager-devsecops"}


@app.route("/metrics")
def metrics():
    content = [
        "# HELP task_manager_tasks_total Total de tarefas cadastradas",
        "# TYPE task_manager_tasks_total gauge",
        f"task_manager_tasks_total {len(tasks)}",
        "# HELP task_manager_app_info Informacoes da aplicacao",
        "# TYPE task_manager_app_info gauge",
        'task_manager_app_info{service="task-manager-devsecops"} 1',
    ]
    return Response("\n".join(content) + "\n", mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)  # nosec B104
