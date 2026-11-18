// Bandeja del superadministrador para revisar solicitudes y otorgar permisos.
import { useMemo, useState } from 'react'
import { Building2, Check, Clock3, Mail, Phone, Search, UserRoundCheck, X } from 'lucide-react'
import type { AccessRequest } from '../datosCompartidos'

type RolAutorizable = 'Coordinador'

export function SolicitudesAcceso({ requests, onApprove, onReject }: {
  requests: AccessRequest[]
  onApprove: (request: AccessRequest, role: RolAutorizable) => void
  onReject: (request: AccessRequest) => void
}) {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('Todos')

  // La búsqueda recorre los datos de la solicitud; el filtro permite separar pendientes de revisadas.
  const visibleRequests = useMemo(() => requests.filter(request => {
    const matchesSearch = `${request.name} ${request.email} ${request.phone ?? ''} ${request.department} ${request.id}`.toLocaleLowerCase('es').includes(search.toLocaleLowerCase('es'))
    return matchesSearch && (status === 'Todos' || request.status === status)
  }), [requests, search, status])
  const pendingCount = requests.filter(request => request.status === 'Pendiente').length
  const approvedCount = requests.filter(request => request.status === 'Aprobada').length
  const deniedCount = requests.filter(request => request.status === 'Rechazada').length

  return <main className="access-page">
    <header className="access-heading">
      <div><span className="access-eyebrow">CONTROL DE PERMISOS</span><h1>Solicitudes de acceso</h1><p>Revisa la identidad y el motivo de cada solicitud antes de habilitar una cuenta administrativa.</p></div>
    </header>

    <section className="access-metrics" aria-label="Resumen de solicitudes">
      <article className="access-metric"><span className="access-metric-icon access-icon-pending"><Clock3 size={18}/></span><div><small>Pendientes de revisión</small><strong>{pendingCount}</strong></div></article>
      <article className="access-metric"><span className="access-metric-icon access-icon-approved"><UserRoundCheck size={18}/></span><div><small>Accesos aprobados</small><strong>{approvedCount}</strong></div></article>
      <article className="access-metric"><span className="access-metric-icon access-icon-denied"><X size={18}/></span><div><small>Accesos denegados</small><strong>{deniedCount}</strong></div></article>
    </section>

    <section className="access-panel">
      <div className="access-toolbar">
        <div><h2>Registro de solicitudes</h2><p>{requests.length} solicitudes recibidas</p></div>
        <label className="access-search"><Search size={17}/><input aria-label="Buscar solicitudes de acceso" placeholder="Buscar por nombre, correo o folio..." value={search} onChange={event => setSearch(event.target.value)}/></label>
        <label className="access-filter"><span>Estado</span><select aria-label="Filtrar por estado" value={status} onChange={event => setStatus(event.target.value)}><option>Todos</option><option>Pendiente</option><option>Aprobada</option><option>Rechazada</option></select></label>
      </div>

      <div className="access-list">
        {visibleRequests.map(request => {
          return <article className="access-request" key={request.id}>
            <div className="access-person"><span className="access-avatar">{request.name.split(' ').slice(0, 2).map(part => part[0]).join('')}</span><div><h3>{request.name}</h3><span className="access-request-id">{request.id}</span></div></div>
            <div className="access-detail"><span><Mail size={14}/>{request.email}</span>{request.phone && <span><Phone size={14}/>{request.phone}</span>}<span><Building2 size={14}/>{request.department}</span></div>
            <div className="access-reason"><small>Motivo de acceso</small><p>{request.reason}</p><time>Solicitada el {request.requestedAt}</time></div>
            <div className="access-review">
              {request.status === 'Pendiente' ? <>
                <label>Permiso a otorgar<span className="access-role-label">Administrador de área</span></label>
                <div className="access-actions"><button className="access-approve" onClick={() => onApprove(request, 'Coordinador')}><Check size={15}/> Aprobar acceso</button><button className="access-reject" aria-label={`Rechazar solicitud de ${request.name}`} title="Rechazar solicitud" onClick={() => onReject(request)}><X size={16}/></button></div>
              </> : <span className={`access-state access-state-${request.status.toLocaleLowerCase('es')}`}>{request.status === 'Aprobada' ? <Check size={14}/> : <X size={14}/>} {request.status}</span>}
            </div>
          </article>
        })}
        {visibleRequests.length === 0 && <div className="access-empty">No hay solicitudes que coincidan con los filtros.</div>}
      </div>
    </section>
  </main>
}
