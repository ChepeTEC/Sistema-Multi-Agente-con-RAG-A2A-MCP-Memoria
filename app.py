import subprocess
import time

def ejecutar_en_paralelo():
    print("Iniciando múltiples servicios en paralelo...")
    procesos = []

    try:
        
        p1 = subprocess.Popen(["npm", "run", "dev"], cwd="web", shell=True)
        procesos.append(p1)
        
        # Lanzar proceso 2 (Backend de ejemplo en la raíz u otra carpeta)
        p2 = subprocess.Popen(["python", "-m", "uvicorn", "src.api.server:app", "--host", "127.0.0.1", "--port", "8000"], shell=True)
        procesos.append(p2)
        
        p3 = subprocess.Popen(["docker-compose", "up", "--build"], shell=True)
        procesos.append(p3)

        print("\nServicios corriendo en paralelo. Presiona Ctrl+C para apagar ambos.\n")
        
        # Mantiene el script vivo mientras los procesos sigan corriendo
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nApagando todos los servicios...")
        # Recorremos la lista para cerrar de forma limpia cada proceso abierto
        for p in procesos:
            p.terminate() 
            
        subprocess.run(["docker-compose", "down"], shell=True)
        print("Todos los servicios se han cerrado correctamente.")

if __name__ == "__main__":
    ejecutar_en_paralelo()
