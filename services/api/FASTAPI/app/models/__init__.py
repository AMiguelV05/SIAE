# app/models/__init__.py
from app.core.database import Base

# 1. Módulo de Usuarios y Administración
from app.models.user import Users, Admins, Admin_Logs

# 2. Módulo de Chat y Soporte
from app.models.chat import Conversations, Messages, Message_Sources, Feedback, Tickets

# 3. Módulo Académico y Estructura (ajustado a los nombres reales en singular)
from app.models.academic import Section, Subsection, Posts

# 4. Módulo de Inteligencia Artificial y RAG
from app.models.ai_rag import ML_Models, Academic_Periods, Topics, Demand_Forecasts, Docs, Document_Chunks