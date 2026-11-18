// Tipos comunes para que las pantallas compartan una estructura de datos coherente.
export type Section = 'Resumen' | 'Solicitudes de acceso' | 'Trámites' | 'Tickets' | 'Publicaciones' | 'Documentos' | 'Reportes' | 'Usuarios' | 'Configuración' | 'Perfil'
export type Ticket = { id: string; subject: string; student: string; program: string; date: string; status: 'Pendiente' | 'En proceso' | 'Resuelto'; initials: string; color: string }
export type ManagedUser = { name: string; email: string; role: 'Superadministrador' | 'Coordinador' | 'Usuario'; status: 'Activo' | 'Inactivo' | 'Pendiente'; lastLogin: string; avatar: string }
export type AccessRequest = { id: string; name: string; email: string; phone?: string | null; department: string; requestedAt: string; reason: string; status: 'Pendiente' | 'Aprobada' | 'Rechazada' }
export type ProcedureStatus = 'Pendiente' | 'En proceso' | 'Completado'
export type Procedure = { id: number; title: string; department: string; attention: string; status: ProcedureStatus; category: string; icon: 'degree' | 'medical' | 'language' | 'transfer' | 'schedule' }
export type PublicationStatus = 'Publicado' | 'Borrador' | 'En revisión'
export type Publication = { id: number; title: string; author: string; category: string; audience: string; status: PublicationStatus; date: string; content: string }
export type SupportCase = { id: string; student: string; code: string; program: string; subject: string; department: string; analysis: string; priority: 'Alta' | 'Media' | 'Baja'; status: 'Pendiente' | 'En proceso' | 'Escalado' | 'Resuelto' }
export type KnowledgeSource = { id: number; fileName: string; type: string; scope: string; updated: string; status: 'Indexado' | 'Pendiente' | 'Procesando' | 'Error'; chunks: number }
export const initialProcedures: Procedure[] = [
  { id: 1, title: 'Titulación por promedio', department: 'ICOM', attention: 'En línea · 24–48 h', status: 'Pendiente', category: 'Titulación', icon: 'degree' },
  { id: 2, title: 'Emisión de justificante médico', department: 'Coordinación', attention: 'En línea · 24–48 h', status: 'Pendiente', category: 'Justificantes', icon: 'medical' },
  { id: 3, title: 'Liberación de inglés', department: 'Coordinación', attention: 'En línea · 24–48 h', status: 'En proceso', category: 'Otros', icon: 'language' },
  { id: 4, title: 'Revalidación de materias', department: 'Coordinación', attention: 'En línea · 24–48 h', status: 'En proceso', category: 'Agenda / Materias', icon: 'transfer' },
  { id: 5, title: 'Altas y bajas de materias', department: 'ICOM', attention: 'En línea · 24–48 h', status: 'Completado', category: 'Agenda / Materias', icon: 'schedule' },
  { id: 6, title: 'Solicitud de beca institucional', department: 'Becas y movilidad', attention: 'En línea · 3–5 días hábiles', status: 'Pendiente', category: 'Becas', icon: 'degree' },
]
// Datos de ejemplo usados mientras el panel no está conectado al servicio backend.
export const initialTickets: Ticket[] = [
  { id: 'SIAE-0248', subject: 'Requisitos para iniciar titulación', student: 'Andrea López', program: 'Ingeniería en Computación', date: 'Hoy, 10:42', status: 'Pendiente', initials: 'AL', color: 'peach' },
  { id: 'SIAE-0247', subject: 'Ajuste de agenda de materias', student: 'Diego Ramírez', program: 'Ingeniería Informática', date: 'Hoy, 09:18', status: 'En proceso', initials: 'DR', color: 'blue' },
  { id: 'SIAE-0246', subject: 'Convocatoria de movilidad', student: 'Sofía Torres', program: 'Ingeniería en Robótica', date: 'Ayer, 16:35', status: 'Pendiente', initials: 'ST', color: 'lilac' },
  { id: 'SIAE-0245', subject: 'Entrega de justificante médico', student: 'Luis Mendoza', program: 'Ingeniería en Computación', date: 'Ayer, 14:07', status: 'Resuelto', initials: 'LM', color: 'mint' },
]
export const initialUsers: ManagedUser[] = [
  { name: 'Karen Hernández', email: 'karen.hernandez@cucei.udg.mx', role: 'Superadministrador', status: 'Activo', lastLogin: '23/10/2026, 9:13 a. m.', avatar: 'KH' },
  { name: 'María Sánchez', email: 'maria.sanchez@cucei.udg.mx', role: 'Coordinador', status: 'Inactivo', lastLogin: '22/10/2026, 1:23 p. m.', avatar: 'MS' },
  { name: 'Martín Juárez', email: 'martin.juarez@cucei.udg.mx', role: 'Usuario', status: 'Activo', lastLogin: '22/10/2026, 7:25 p. m.', avatar: 'MJ' },
  { name: 'Mariela Minolo', email: 'mariela.minolo@cucei.udg.mx', role: 'Coordinador', status: 'Activo', lastLogin: '21/10/2026, 1:22 p. m.', avatar: 'MM' },
  { name: 'Briana Páez', email: 'briana.paez@cucei.udg.mx', role: 'Coordinador', status: 'Pendiente', lastLogin: '20/10/2026, 7:00 a. m.', avatar: 'BP' },
  { name: 'Matías Barrios', email: 'matias.barrios@cucei.udg.mx', role: 'Usuario', status: 'Pendiente', lastLogin: '19/10/2026, 5:33 p. m.', avatar: 'MB' },
  { name: 'Alan Burka', email: 'alan.burka@cucei.udg.mx', role: 'Usuario', status: 'Activo', lastLogin: '18/10/2026, 7:20 p. m.', avatar: 'AB' },
]
export const initialPublications: Publication[] = [
  { id: 1, title: 'Nuevos formatos para reportes del servicio social', author: 'Karen Hernández', category: 'Servicio social', audience: 'Todas las carreras', status: 'Publicado', date: '2026-10-23', content: 'Ya están disponibles los formatos actualizados para la entrega de reportes de servicio social. Consulta los requisitos con tu coordinación.' },
  { id: 2, title: 'Convocatoria para becas CUCEI', author: 'María Sánchez', category: 'Becas', audience: 'Todas las carreras', status: 'Borrador', date: '2026-10-20', content: 'Consulta fechas, requisitos y documentos para participar en la convocatoria vigente de becas.' },
  { id: 3, title: 'Requisitos para iniciar el trámite de titulación', author: 'Karen Hernández', category: 'Titulación', audience: 'ICOM', status: 'En revisión', date: '2026-10-18', content: 'Revisa las modalidades y los documentos requeridos antes de iniciar tu proceso de titulación.' },
  { id: 4, title: 'Periodo de altas y bajas de materias', author: 'Martín Juárez', category: 'Control escolar', audience: 'Todas las carreras', status: 'Publicado', date: '2026-10-15', content: 'El periodo para realizar ajustes de materias se encuentra disponible de acuerdo con el calendario escolar.' },
  { id: 5, title: 'Fechas importantes para movilidad', author: 'María Sánchez', category: 'Becas y movilidad', audience: 'INRO', status: 'Publicado', date: '2026-10-12', content: 'Estas son las fechas de registro, entrega de documentos y publicación de resultados para movilidad.' },
  { id: 6, title: 'Guía para solicitar justificantes médicos', author: 'Karen Hernández', category: 'Control escolar', audience: 'Todas las carreras', status: 'Borrador', date: '2026-10-09', content: 'Pasos para entregar la documentación y solicitar el seguimiento de un justificante médico.' },
]
export const initialCases: SupportCase[] = [
  { id: 'SIAE-0248', student: 'Sofía Ramírez Gómez', code: '218739421', program: 'Ing. en Computación (ICOM)', subject: 'Titulación por promedio', department: 'Coordinación ICOM', analysis: 'Prioridad alta · RAG validado', priority: 'Alta', status: 'Pendiente' },
  { id: 'SIAE-0247', student: 'Carlos Eduardo Mendoza', code: '219304812', program: 'Ing. Informática (INNI)', subject: 'Emisión de justificante médico', department: 'Control Escolar', analysis: 'Requiere validación humana', priority: 'Media', status: 'En proceso' },
  { id: 'SIAE-0246', student: 'Mariana Torres Silva', code: '217482019', program: 'Ing. Biomédica (IBIM)', subject: 'Revalidación de materias', department: 'Coordinación IBIM', analysis: 'Materia externa detectada', priority: 'Alta', status: 'Escalado' },
  { id: 'SIAE-0245', student: 'Diego Ramírez Soto', code: '220481022', program: 'Ing. Informática (INNI)', subject: 'Ajuste de agenda de materias', department: 'Control Escolar', analysis: 'RAG validado · Respuesta sugerida', priority: 'Baja', status: 'Pendiente' },
  { id: 'SIAE-0244', student: 'Andrea López Cruz', code: '219330741', program: 'Ing. en Computación (ICOM)', subject: 'Convocatoria para beca', department: 'Becas y movilidad', analysis: 'Información vigente verificada', priority: 'Media', status: 'Resuelto' },
]
export const initialSources: KnowledgeSource[] = [
  { id: 1, fileName: 'Reglamento General de Titulación.pdf', type: 'PDF', scope: 'Todas las carreras', updated: '22 oct 2026', status: 'Indexado', chunks: 48 },
  { id: 2, fileName: 'Calendario escolar 2026-B.pdf', type: 'PDF', scope: 'Todas las carreras', updated: '20 oct 2026', status: 'Indexado', chunks: 16 },
  { id: 3, fileName: 'Guía de servicio social.docx', type: 'DOCX', scope: 'ICOM · INNI', updated: '18 oct 2026', status: 'Indexado', chunks: 23 },
  { id: 4, fileName: 'Convocatoria de movilidad.pdf', type: 'PDF', scope: 'Todas las carreras', updated: 'Pendiente', status: 'Pendiente', chunks: 0 },
]
