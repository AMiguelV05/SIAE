from app.core.database import Base, engine
from app.models.academic import *
from app.models.ai_rag import *
from app.models.chat import *
from app.models.user import *

print("Conectando a la base de datos y creando las 17 tablas...")
Base.metadata.create_all(bind=engine)
print("¡Las 17 tablas se han creado exitosamente!")
