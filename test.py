import os
import earthaccess
from dotenv import load_dotenv

load_dotenv()

usuario = os.getenv("EARTHDATA_USERNAME")
contraseña = os.getenv("EARTHDATA_PASSWORD")

if not usuario or not contraseña:
    raise ValueError(
        "Faltan EARTHDATA_USERNAME o EARTHDATA_PASSWORD en el archivo .env"
    )

# strategy="environment" lee EARTHDATA_USERNAME / EARTHDATA_PASSWORD del entorno
auth = earthaccess.login(strategy="environment")

print("Autenticación con Earthdata completada.")
print(f"Autenticado: {auth.authenticated}")
