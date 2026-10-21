from fastapi import FastAPI

app = FastAPI(
    title="API de Modelos - Sistema Modular UDG",
    version="1.0.0",
)

@app.get("/")
def root():
    return {"mensaje": "Servidor de modelos de base de datos activo"}
