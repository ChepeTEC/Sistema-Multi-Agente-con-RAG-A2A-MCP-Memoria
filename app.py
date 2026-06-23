import os
import signal
import socket
import subprocess
import time
from pathlib import Path


BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = 5173
ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"
SHUTDOWN_REQUESTED = False


def is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def wait_for_port(host: str, port: int, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_open(host, port):
            return True
        time.sleep(1)
    return False


def npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def ensure_docker_services() -> None:
    subprocess.run(["docker", "compose", "up", "-d", "--build"], check=True)


def start_backend():
    if is_port_open(BACKEND_HOST, BACKEND_PORT):
        print(f"Backend ya responde en http://{BACKEND_HOST}:{BACKEND_PORT}")
        return None

    env = os.environ.copy()
    command = [
        "python",
        "-m",
        "uvicorn",
        "src.api.server:app",
        "--host",
        BACKEND_HOST,
        "--port",
        str(BACKEND_PORT),
    ]
    process = subprocess.Popen(command, cwd=ROOT_DIR, env=env)

    if not wait_for_port(BACKEND_HOST, BACKEND_PORT):
        terminate_process_tree(process)
        raise RuntimeError(f"El backend no respondio en el puerto {BACKEND_PORT}.")

    return process


def start_frontend():
    if is_port_open(FRONTEND_HOST, FRONTEND_PORT):
        print(f"Frontend ya responde en http://{FRONTEND_HOST}:{FRONTEND_PORT}")
        return None

    env = os.environ.copy()
    env["VITE_API_BACKEND_URL"] = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
    command = [
        npm_command(),
        "run",
        "dev",
        "--",
        "--host",
        FRONTEND_HOST,
        "--port",
        str(FRONTEND_PORT),
        "--strictPort",
    ]
    process = subprocess.Popen(command, cwd=WEB_DIR, env=env)

    if not wait_for_port(FRONTEND_HOST, FRONTEND_PORT):
        terminate_process_tree(process)
        raise RuntimeError(f"El frontend no respondio en el puerto {FRONTEND_PORT}.")

    return process


def terminate_process_tree(process) -> None:
    if process is None:
        return

    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"])
    else:
        process.terminate()


def stop_processes(processes) -> None:
    for process in processes:
        if process is None or process.poll() is not None:
            continue

        terminate_process_tree(process)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def request_shutdown(signum, frame) -> None:
    del signum, frame
    global SHUTDOWN_REQUESTED
    SHUTDOWN_REQUESTED = True


def install_signal_handlers() -> None:
    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)


def ejecutar_en_paralelo():
    print("Iniciando servicios del sistema multi-agente...")
    install_signal_handlers()
    processes = []

    try:
        ensure_docker_services()
        processes.append(start_backend())
        processes.append(start_frontend())

        print("\nServicios corriendo. Presiona Ctrl+C para apagar.\n")
        while not SHUTDOWN_REQUESTED:
            time.sleep(1)

    finally:
        print("\nApagando servicios...")
        stop_processes(processes)
        subprocess.run(["docker", "compose", "down"], check=False)
        print("Servicios cerrados correctamente.")


if __name__ == "__main__":
    ejecutar_en_paralelo()

