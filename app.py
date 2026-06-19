import socket
import subprocess
import time


def esperar_puerto(host, port, timeout=60):
    limite = time.time() + timeout
    while time.time() < limite:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(1)
    return False


def ejecutar_en_paralelo():
    print("Iniciando multiples servicios en paralelo...")
    procesos = []

    try:
        p3 = subprocess.Popen("docker-compose up --build", shell=True)
        procesos.append(p3)

        # Lanzar proceso 2 (Backend de ejemplo en la raiz u otra carpeta)
        p2 = subprocess.Popen(
            "python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000",
            shell=True,
        )
        procesos.append(p2)

        if not esperar_puerto("127.0.0.1", 8000):
            raise RuntimeError("El backend no respondio en el puerto 8000.")

        p1 = subprocess.Popen("npm run dev", cwd="web", shell=True)
        procesos.append(p1)

        print("\nServicios corriendo en paralelo. Presiona Ctrl+C para apagar ambos.\n")

        # Mantiene el script vivo mientras los procesos sigan corriendo
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nApagando todos los servicios...")
        # Recorremos la lista para cerrar de forma limpia cada proceso abierto
        for p in procesos:
            p.terminate()

        subprocess.run("docker-compose down", shell=True)
        print("Todos los servicios se han cerrado correctamente.")


if __name__ == "__main__":
    ejecutar_en_paralelo()
