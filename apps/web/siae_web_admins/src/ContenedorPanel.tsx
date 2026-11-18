import { useEffect, useState } from 'react'
import { Bell, BookOpenCheck, ChartNoAxesColumn, ChevronDown, ClipboardList, FileText, GraduationCap, Home, Menu, MessageCircle, MoreHorizontal, Settings, ShieldCheck, Users, X, type LucideIcon } from 'lucide-react'
import { initialCases, initialProcedures, initialPublications, initialSources, initialTickets, type AccessRequest, type ManagedUser, type Publication, type Section } from './datosCompartidos'
import { cerrarSesion, obtenerSesion, obtenerSolicitudesAcceso, obtenerUsuarios, revisarSolicitudAcceso, solicitarAcceso, type AdminAutenticado } from './api'
import { InicioSesion } from './pages/InicioSesion'
import { PanelPrincipal } from './pages/PanelPrincipal'
import { BibliotecaDocumentos } from './pages/BibliotecaDocumentos'
import { GestionTramites } from './pages/GestionTramites'
import { GestionPublicaciones } from './pages/GestionPublicaciones'
import { PanelReportes } from './pages/PanelReportes'
import { Configuracion } from './pages/Configuracion'
import { GestionTickets } from './pages/GestionTickets'
import { GestionUsuarios } from './pages/GestionUsuarios'
import { PerfilAdministrador } from './pages/PerfilAdministrador'
import { SolicitudesAcceso } from './pages/SolicitudesAcceso'

// Opciones del menú principal: se enlaza con una pantalla independiente.
const navItems: { label: Section; title: string; icon: LucideIcon }[] = [
  { label: 'Resumen', title: 'Panel principal', icon: Home },
  { label: 'Usuarios', title: 'Usuarios', icon: Users },
  { label: 'Trámites', title: 'Trámites', icon: ClipboardList },
  { label: 'Tickets', title: 'Tickets', icon: MessageCircle },
  { label: 'Publicaciones', title: 'Publicaciones', icon: FileText },
  { label: 'Documentos', title: 'Documentos', icon: BookOpenCheck },
  { label: 'Reportes', title: 'Reportes', icon: ChartNoAxesColumn },
]

// Convierte el nombre interno de la sección en el texto que aparece en la ruta superior.
function nombreSeccion(section: Section) {
  return section === 'Resumen' ? 'Panel principal' : section
}

// Lee las preferencias guardadas para decidir qué tickets aparecen en la campana.
function preferenciaActiva(adminId: string | undefined, key: 'notices' | 'urgentAlerts') {
  if (!adminId) return true
  try {
    const settings = JSON.parse(localStorage.getItem(`siae-configuracion-${adminId}`) ?? '{}') as Partial<Record<'notices' | 'urgentAlerts', boolean>>
    return settings[key] !== false
  } catch {
    return true
  }
}

// Recupera las publicaciones guardadas localmente y conserva los ejemplos si aún no hay datos guardados.
function leerPublicacionesGuardadas(): Publication[] {
  try {
    const saved = localStorage.getItem('siae-publicaciones')
    if (!saved) return initialPublications
    const parsed: unknown = JSON.parse(saved)
    return Array.isArray(parsed) ? parsed as Publication[] : initialPublications
  } catch {
    return initialPublications
  }
}

// Limita la navegación visible según el rol que confirmó el servidor.
function seccionesPermitidas(role: ManagedUser['role'] | undefined): Section[] {
  if (role === 'Superadministrador') return ['Resumen', 'Solicitudes de acceso', 'Usuarios', 'Trámites', 'Tickets', 'Publicaciones', 'Documentos', 'Reportes', 'Configuración', 'Perfil']
  if (role === 'Coordinador') return ['Resumen', 'Trámites', 'Tickets', 'Publicaciones', 'Documentos', 'Perfil']
  return ['Resumen', 'Perfil']
}

// Contenedor general: administra acceso, navegación, datos compartidos y avisos emergentes.
function App() {
  const [authenticated, setAuthenticated] = useState(false)
  const [authChecking, setAuthChecking] = useState(true)
  const [authUser, setAuthUser] = useState<AdminAutenticado | null>(null)
  const [section, setSection] = useState<Section>('Resumen')
  const [tickets] = useState(initialTickets)
  const [supportCases, setSupportCases] = useState(initialCases)
  const [procedures, setProcedures] = useState(initialProcedures)
  const [publications, setPublications] = useState<Publication[]>(leerPublicacionesGuardadas)
  const [documents, setDocuments] = useState(initialSources)
  const [globalSearch, setGlobalSearch] = useState('')
  const [mobileNav, setMobileNav] = useState(false)
  const [toast, setToast] = useState('')
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [readNotificationIds, setReadNotificationIds] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem('siae-notificaciones-leidas') ?? '[]') as string[] }
    catch { return [] }
  })
  const [users, setUsers] = useState<ManagedUser[]>([])
  const [usersLoading, setUsersLoading] = useState(true)
  const [accessRequests, setAccessRequests] = useState<AccessRequest[]>([])
  const [showNewUser, setShowNewUser] = useState(false)
  // Las vistas hijas usan esta función para mostrar confirmaciones consistentes.
  const notify = (message: string) => {
    setToast(message)
    window.setTimeout(() => setToast(''), 2600)
  }
  useEffect(() => {
    let vigente = true
    obtenerSesion().then(user => {
      if (vigente) { setAuthUser(user); setAuthenticated(Boolean(user)) }
    }).catch(() => {
      if (vigente) setAuthUser(null)
    }).finally(() => {
      if (vigente) setAuthChecking(false)
    })
    return () => { vigente = false }
  }, [])
  useEffect(() => {
    localStorage.setItem('siae-publicaciones', JSON.stringify(publications))
  }, [publications])
  useEffect(() => {
    if (authUser?.role !== 'Superadministrador') return
    let vigente = true
    let primeraCarga = true
    const cargarSolicitudes = () => {
      obtenerSolicitudesAcceso()
        .then(requests => { if (vigente) setAccessRequests(requests) })
        .catch(error => { if (vigente && primeraCarga) notify(error instanceof Error ? error.message : 'No se pudieron cargar las solicitudes.') })
        .finally(() => { primeraCarga = false })
    }
    cargarSolicitudes()
    setUsersLoading(true)
    obtenerUsuarios()
      .then(loadedUsers => { if (vigente) setUsers(loadedUsers) })
      .catch(error => { if (vigente) notify(error instanceof Error ? error.message : 'No se pudieron cargar las cuentas.') })
      .finally(() => { if (vigente) setUsersLoading(false) })
    const actualizacion = window.setInterval(cargarSolicitudes, 30000)
    return () => { vigente = false; window.clearInterval(actualizacion) }
  }, [authUser?.id, authUser?.role])
  // La API verifica el rol antes de conceder permisos y registrar la cuenta.
  const approveAccess = async (request: AccessRequest, role: 'Coordinador') => {
    try {
      const result = await revisarSolicitudAcceso(request.id, 'approve', role)
      setAccessRequests(current => current.map(item => item.id === request.id ? result.request : item))
      if (result.user) setUsers(current => [...current, { name: result.user!.name, email: result.user!.email, role: result.user!.role, status: 'Activo', lastLogin: 'Sin iniciar sesión', avatar: result.user!.name.split(' ').slice(0, 2).map(part => part[0]).join('').toLocaleUpperCase('es') }])
      notify(`Acceso aprobado para ${request.name} como administrador de área.`)
    } catch (error) {
      notify(error instanceof Error ? error.message : 'No se pudo aprobar la solicitud.')
    }
  }
  const rejectAccess = async (request: AccessRequest) => {
    try {
      const result = await revisarSolicitudAcceso(request.id, 'reject')
      setAccessRequests(current => current.map(item => item.id === request.id ? result.request : item))
      notify(`La solicitud de ${request.name} fue rechazada.`)
    } catch (error) {
      notify(error instanceof Error ? error.message : 'No se pudo rechazar la solicitud.')
    }
  }
  const logout = async () => {
    try { await cerrarSesion() }
    catch (error) { notify(error instanceof Error ? error.message : 'No se pudo cerrar la sesión en el servidor.'); return }
    setAuthUser(null)
    setAuthenticated(false)
    setSection('Resumen')
  }

  if (authChecking) return <main className="auth-loading" role="status">Comprobando la sesión segura…</main>
  if (!authenticated) return <InicioSesion onLogin={user => { setAuthUser(user); setAuthenticated(true) }} onRequestAccess={solicitarAcceso} />

  const canReviewAccess = authUser?.role === 'Superadministrador'
  const pendingAccessCount = accessRequests.filter(request => request.status === 'Pendiente').length
  const notifications = [
    ...accessRequests.filter(request => request.status === 'Pendiente').map(request => ({
      id: `acceso-${request.id}`,
      section: 'Solicitudes de acceso' as Section,
      title: 'Solicitud de acceso pendiente',
      detail: `${request.name} · ${request.department}`,
      date: request.requestedAt,
    })),
    ...supportCases.filter(item => (item.status === 'Pendiente' && preferenciaActiva(authUser?.id, 'notices')) || (item.status === 'Escalado' && preferenciaActiva(authUser?.id, 'urgentAlerts'))).map(item => ({
      id: `ticket-${item.id}-${item.status}`,
      section: 'Tickets' as Section,
      title: item.status === 'Escalado' ? 'Ticket escalado requiere atención' : 'Ticket pendiente de atención',
      detail: `${item.student} · ${item.subject}`,
      date: item.id,
    })),
  ]
  const unreadNotifications = notifications.filter(item => !readNotificationIds.includes(item.id))
  const marcarNotificacionLeida = (id: string) => setReadNotificationIds(current => {
    if (current.includes(id)) return current
    const updated = [...current, id]
    localStorage.setItem('siae-notificaciones-leidas', JSON.stringify(updated))
    return updated
  })
  const marcarTodasLeidas = () => setReadNotificationIds(current => {
    const updated = Array.from(new Set([...current, ...notifications.map(item => item.id)]))
    localStorage.setItem('siae-notificaciones-leidas', JSON.stringify(updated))
    return updated
  })
  const allowedSections = seccionesPermitidas(authUser?.role)
  const visibleNavItems = navItems.filter(item => allowedSections.includes(item.label))

  // Selecciona el componente que corresponde a la pestaña activa.
  const page = section === 'Resumen'
    ? <PanelPrincipal tickets={tickets} supportCases={supportCases} procedures={procedures} publications={publications} documents={documents} users={users} accessRequests={accessRequests} search={globalSearch} onSearchChange={setGlobalSearch} onTicket={() => setSection('Tickets')} onSection={setSection} onNotify={notify} />
    : section === 'Solicitudes de acceso'
      ? canReviewAccess ? <SolicitudesAcceso requests={accessRequests} onApprove={approveAccess} onReject={rejectAccess} /> : <PanelPrincipal tickets={tickets} supportCases={supportCases} procedures={procedures} publications={publications} documents={documents} users={users} accessRequests={accessRequests} search={globalSearch} onSearchChange={setGlobalSearch} onTicket={() => setSection('Tickets')} onSection={setSection} onNotify={notify} />
    : section === 'Usuarios'
      ? <GestionUsuarios users={users} setUsers={setUsers} loading={usersLoading} onNotify={notify} showNewUser={showNewUser} setShowNewUser={setShowNewUser} />
      : section === 'Trámites'
        ? <GestionTramites procedures={procedures} setProcedures={setProcedures} onNotify={notify} />
        : section === 'Tickets'
          ? <GestionTickets cases={supportCases} setCases={setSupportCases} onNotify={notify} />
          : section === 'Publicaciones'
            ? <GestionPublicaciones publications={publications} setPublications={setPublications} authorName={authUser?.name ?? 'Administración SIAE'} onNotify={notify} />
            : section === 'Documentos'
              ? <BibliotecaDocumentos sources={documents} setSources={setDocuments} onNotify={notify} />
              : section === 'Reportes'
                ? <PanelReportes />
                : section === 'Configuración'
                   ? <Configuracion onNotify={notify} admin={authUser!} onAdminUpdated={setAuthUser} />
                : <PerfilAdministrador onNotify={notify} admin={authUser!} onAdminUpdated={setAuthUser} onLogout={logout} />

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><GraduationCap size={23} strokeWidth={2.2}/></div><div><strong>SIAE</strong><small>CUCEI · Administración</small></div><button className="icon-button close-nav" onClick={() => setMobileNav(false)} aria-label="Cerrar menú"><X size={18} /></button></div>
      {canReviewAccess && <><div className="workspace-label">ESPACIO DE TRABAJO</div><button type="button" className={`workspace-switch ${section === 'Solicitudes de acceso' ? 'workspace-switch-active' : ''}`} aria-label={`Abrir solicitudes de acceso de Administración. ${pendingAccessCount} pendientes.`} title="Revisar solicitudes y permisos" onClick={() => { setSection('Solicitudes de acceso'); setMobileNav(false) }}><span className="workspace-icon"><ShieldCheck size={16} /></span><span><b>Administración</b><small>Solicitudes y permisos</small></span>{pendingAccessCount > 0 && <span className="workspace-count" aria-label={`${pendingAccessCount} solicitudes pendientes`}>{pendingAccessCount > 99 ? '99+' : pendingAccessCount}</span>}<ChevronDown size={15} /></button></>}
      <div className="nav-caption">MENÚ PRINCIPAL</div>
      <nav className="nav-list">{visibleNavItems.map(({ label, title, icon: Icon }) => <button key={label} className={`nav-item ${section === label ? 'active' : ''}`} onClick={() => { setSection(label); setMobileNav(false) }}><Icon size={18} /><span>{title}</span>{label === 'Tickets' && <span className="nav-count">8</span>}</button>)}</nav>
      <div className="nav-caption tools-caption">HERRAMIENTAS</div>
      <nav className="nav-list"><button className="nav-item" onClick={() => notify('El asistente SIAE estará disponible al conectar el servicio.')}><GraduationCap size={18} /><span>SIAE</span></button>{allowedSections.includes('Configuración') && <button className={`nav-item ${section === 'Configuración' ? 'active' : ''}`} onClick={() => { setSection('Configuración'); setMobileNav(false) }}><Settings size={18} /><span>Configuración</span></button>}</nav>
      <div className="sidebar-bottom"><button className={`profile ${section === 'Perfil' ? 'profile-active' : ''}`} onClick={() => { setSection('Perfil'); setMobileNav(false) }}><div className="avatar avatar-admin">{authUser?.name.split(' ').slice(0, 2).map(part => part[0]).join('').toLocaleUpperCase('es')}</div><span><b>{authUser?.name}</b><small>{authUser?.role}</small></span><MoreHorizontal size={18} /></button></div>
    </aside>
    {mobileNav && <button className="nav-scrim" aria-label="Cerrar navegación" onClick={() => setMobileNav(false)} />}
    <main className="main-area">
      <header className="topbar"><button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Abrir menú"><Menu size={20} /></button><div className="breadcrumbs"><span>Administración</span><span className="crumb-slash">/</span><b>{nombreSeccion(section)}</b></div><div className="top-actions">{section !== 'Resumen' && <div className="search-box"><input aria-label="Buscar en todo el panel" placeholder="Buscar en todo el panel..." value={globalSearch} onChange={event => setGlobalSearch(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && globalSearch.trim()) setSection('Resumen') }} /></div>}<div className="notification-wrapper"><button type="button" className="icon-button notification-button" aria-label={`Notificaciones. ${unreadNotifications.length} sin leer`} aria-expanded={notificationsOpen} onClick={() => setNotificationsOpen(open => !open)}><Bell size={18} />{unreadNotifications.length > 0 && <span className="notification-count">{unreadNotifications.length > 99 ? '99+' : unreadNotifications.length}</span>}</button>{notificationsOpen && <section className="notifications-panel" aria-label="Notificaciones"><header className="notifications-heading"><div><b>Notificaciones</b><small>{unreadNotifications.length ? `${unreadNotifications.length} sin leer` : 'Todo está al día'}</small></div><button type="button" onClick={marcarTodasLeidas} disabled={!unreadNotifications.length}>Marcar todas como leídas</button></header>{notifications.length ? <div className="notifications-list">{notifications.map(item => <button type="button" key={item.id} className={`notification-item ${readNotificationIds.includes(item.id) ? 'notification-read' : ''}`} onClick={() => { marcarNotificacionLeida(item.id); setNotificationsOpen(false); setSection(item.section) }}><span className="notification-item-dot"/><span className="notification-item-copy"><b>{item.title}</b><small>{item.detail}</small><small className="notification-item-date">{item.date}</small></span></button>)}</div> : <p className="notifications-empty">No hay notificaciones pendientes.</p>}</section>}</div><div className="top-divider" /><button type="button" className="top-user" aria-label="Abrir perfil de administradora" title="Ver perfil de administradora" aria-current={section === 'Perfil' ? 'page' : undefined} onClick={() => { setSection('Perfil'); setMobileNav(false) }}><div className="avatar avatar-admin">{authUser?.name.split(' ').slice(0, 2).map(part => part[0]).join('').toLocaleUpperCase('es')}</div><div><b>{authUser?.name}</b><small>{authUser?.role}</small></div><ChevronDown size={15} /></button></div></header>
      {page}
    </main>
    {toast && <div className="toast"><span className="toast-check">✓</span>{toast}</div>}
  </div>
}

export default App
