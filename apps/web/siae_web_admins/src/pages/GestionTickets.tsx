// Bandeja de atención: clasifica tickets, filtra la cola y permite registrar seguimiento.
import { useState } from 'react'
import { Activity, Bell, ChevronDown, CheckCircle2, CircleHelp, ClipboardList, Eye, Search, Sparkles, X } from 'lucide-react'
import { SupportCase } from '../datosCompartidos'

export function GestionTickets({ cases, setCases, onNotify }: { cases: SupportCase[]; setCases: React.Dispatch<React.SetStateAction<SupportCase[]>>; onNotify: (message: string) => void }) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('Todos')
  const [departmentFilter, setDepartmentFilter] = useState('Todos')
  const [priorityFilter, setPriorityFilter] = useState('Todas')
  const [activeCase, setActiveCase] = useState<SupportCase | null>(null)
  const [reply, setReply] = useState('')
  const departments = ['Todos', ...Array.from(new Set(cases.map(item => item.department)))]
  // Respeta todos los criterios para enfocar la atención en los casos pertinentes.
  const visibleCases = cases.filter(item => {
    const matchesSearch = `${item.id} ${item.student} ${item.code} ${item.subject}`.toLocaleLowerCase('es').includes(search.toLocaleLowerCase('es'))
    return matchesSearch && (statusFilter === 'Todos' || item.status === statusFilter) && (departmentFilter === 'Todos' || item.department === departmentFilter) && (priorityFilter === 'Todas' || item.priority === priorityFilter)
  })
  const setCaseStatus = (id: string, status: SupportCase['status']) => setCases(current => current.map(item => item.id === id ? { ...item, status } : item))
  // Actualiza el estado del ticket abierto y limpia la respuesta escrita en el formulario.
  const closeTicket = (status: 'En proceso' | 'Resuelto') => {
    if (!activeCase) return
    setCaseStatus(activeCase.id, status)
    setActiveCase(null)
    setReply('')
    onNotify(status === 'Resuelto' ? 'El ticket se marcó como resuelto.' : 'El ticket se asignó para seguimiento.')
  }
  const countStatus = (status: SupportCase['status']) => cases.filter(item => item.status === status).length
  const openCase = (item: SupportCase) => { setActiveCase(item); setReply('') }

  return <div className="tickets-page">
    <div className="ticket-page-heading"><div><span className="ticket-eyebrow">CUCEI · UNIVERSIDAD DE GUADALAJARA</span><h1>Atención y gestión de tickets</h1><p>Revisa las consultas, valida la clasificación y brinda seguimiento a cada estudiante.</p></div><div className="ticket-period"><Bell size={17}/><span>Periodo 2026-B</span></div></div>
    <div className="ticket-stats"><section className="ticket-stat"><div><span>Total recibidos</span><strong>{cases.length}</strong><small className="ticket-stat-green">↗ Actividad de atención</small></div><span className="ticket-stat-icon ticket-stat-blue"><InboxIcon/></span></section><section className="ticket-stat"><div><span>Pendientes</span><strong className="ticket-number-orange">{countStatus('Pendiente')}</strong><small>Requieren atención</small></div><span className="ticket-stat-icon ticket-stat-orange"><CircleHelp size={21}/></span></section><section className="ticket-stat"><div><span>En proceso</span><strong className="ticket-number-blue">{countStatus('En proceso')}</strong><small>En revisión activa</small></div><span className="ticket-stat-icon ticket-stat-blue"><Activity size={21}/></span></section><section className="ticket-stat"><div><span>Escalados / urgentes</span><strong className="ticket-number-red">{countStatus('Escalado')}</strong><small className="ticket-stat-red">Atención por jefatura</small></div><span className="ticket-stat-icon ticket-stat-red-bg"><CircleHelp size={21}/></span></section></div>
    <section className="ticket-filter-panel"><div className="ticket-search"><Search size={17}/><input aria-label="Buscar tickets" placeholder="Buscar por folio, alumno o trámite..." value={search} onChange={e => setSearch(e.target.value)}/></div><label className="ticket-select"><span>Estado: {statusFilter}</span><select aria-label="Filtrar tickets por estado" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}><option>Todos</option><option>Pendiente</option><option>En proceso</option><option>Escalado</option><option>Resuelto</option></select><ChevronDown size={15}/></label><label className="ticket-select"><span>Depto.: {departmentFilter === 'Todos' ? 'Todos' : departmentFilter}</span><select aria-label="Filtrar por departamento" value={departmentFilter} onChange={e => setDepartmentFilter(e.target.value)}>{departments.map(item => <option key={item}>{item}</option>)}</select><ChevronDown size={15}/></label><label className="ticket-select"><span>Prioridad: {priorityFilter}</span><select aria-label="Filtrar por prioridad" value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)}><option>Todas</option><option>Alta</option><option>Media</option><option>Baja</option></select><ChevronDown size={15}/></label></section>
    <section className="ticket-list-panel"><div className="ticket-list-wrap"><table className="ticket-list-table"><thead><tr><th>Estudiante</th><th>Trámite / asunto</th><th>Análisis RAG / clasificación</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>{visibleCases.map(item => <tr key={item.id}><td><b>{item.student}</b><small>Cód.: {item.code} · {item.program}</small></td><td><b>{item.subject}</b><small>{item.department}</small></td><td><span className={`ticket-analysis priority-${item.priority.toLocaleLowerCase('es')}`}><Sparkles size={12}/>{item.analysis}</span></td><td><span className={`ticket-status ticket-status-${item.status.toLocaleLowerCase('es').replace(' ', '-')}`}>{item.status}</span></td><td><button className="ticket-attend" onClick={() => openCase(item)}><Eye size={14}/> Atender</button></td></tr>)}</tbody></table>{visibleCases.length === 0 && <div className="users-empty">No hay tickets que coincidan con los filtros.</div>}</div><div className="ticket-list-footer">Se muestran <b>{visibleCases.length}</b> de <b>{cases.length}</b> tickets recibidos</div></section>
    {activeCase && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setActiveCase(null) }}><section className="modal ticket-detail"><div className="modal-header"><div><span className="modal-kicker">{activeCase.id} · {activeCase.status.toLocaleUpperCase('es')}</span><h2>{activeCase.subject}</h2><p>{activeCase.student} · {activeCase.code} · {activeCase.program}</p></div><button className="icon-button" onClick={() => setActiveCase(null)} aria-label="Cerrar"><X size={19}/></button></div><div className="ticket-detail-grid"><div><small>Departamento</small><b>{activeCase.department}</b></div><div><small>Prioridad</small><b>{activeCase.priority}</b></div></div><div className="ticket-rag-note"><Sparkles size={15}/><span><b>Análisis del asistente</b>{activeCase.analysis}</span></div><label htmlFor="ticket-reply">Respuesta o nota de seguimiento</label><textarea id="ticket-reply" rows={4} value={reply} onChange={e => setReply(e.target.value)} placeholder="Escribe una respuesta para el estudiante o una nota interna..."/><div className="modal-actions ticket-detail-actions"><button className="outline-button" onClick={() => closeTicket('En proceso')}>Dejar en proceso</button><button className="primary-button" onClick={() => closeTicket('Resuelto')}><CheckCircle2 size={15}/> Marcar resuelto</button></div></section></div>}
  </div>
}

function InboxIcon() { return <ClipboardList size={21}/> }
