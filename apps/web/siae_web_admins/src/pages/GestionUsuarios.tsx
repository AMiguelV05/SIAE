// Administración de cuentas, roles y estados del personal y estudiantes.
import React, { useState } from 'react'
import { ChevronDown, ChevronsLeft, ChevronsRight, ChevronLeft, ChevronRight, Download, Filter, MoreHorizontal, Pencil, Search, Trash2, UserPlus, X } from 'lucide-react'
import { ManagedUser } from '../datosCompartidos'

export function GestionUsuarios({ users, setUsers, loading, onNotify, showNewUser, setShowNewUser }: { users: ManagedUser[]; setUsers: React.Dispatch<React.SetStateAction<ManagedUser[]>>; loading: boolean; onNotify: (message: string) => void; showNewUser: boolean; setShowNewUser: (show: boolean) => void }) {
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('Todos')
  const [statusFilter, setStatusFilter] = useState('Todos')
  const [editing, setEditing] = useState<ManagedUser | null>(null)
  // Aplica en conjunto la búsqueda y los filtros de rol y estado.
  const visibleUsers = users.filter(user => {
    const matchesSearch = `${user.name} ${user.email}`.toLocaleLowerCase('es').includes(search.toLocaleLowerCase('es'))
    return matchesSearch && (roleFilter === 'Todos' || user.role === roleFilter) && (statusFilter === 'Todos' || user.status === statusFilter)
  })
  // Descarga las cuentas visibles en formato CSV para abrirlas en una hoja de cálculo.
  const exportUsers = () => {
    const csv = ['Nombre,Correo,Rol,Estado,Último acceso', ...visibleUsers.map(user => [user.name, user.email, user.role, user.status, user.lastLogin].map(value => `"${value.replace(/"/g, '""')}"`).join(','))].join('\n')
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob(['\ufeff', csv], { type: 'text/csv;charset=utf-8' }))
    link.download = 'usuarios-siae.csv'
    link.click()
    URL.revokeObjectURL(link.href)
  }
  const closeModal = () => { setShowNewUser(false); setEditing(null) }
  // Crea o actualiza una cuenta; las cuentas nuevas quedan pendientes de activación.
  const saveUser = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const name = form.get('name')!.toString().trim()
    const email = form.get('email')!.toString().trim()
    const role = form.get('role')!.toString() as ManagedUser['role']
    const user: ManagedUser = { name, email, role, status: editing?.status ?? 'Pendiente', lastLogin: editing?.lastLogin ?? 'Sin iniciar sesión', avatar: name.split(/\s+/).map(part => part[0]).join('').slice(0, 2).toLocaleUpperCase('es') }
    if (editing) setUsers(current => current.map(item => item.email === editing.email ? user : item))
    else setUsers(current => [user, ...current])
    closeModal()
    onNotify(editing ? 'Los datos de la cuenta se actualizaron.' : 'La cuenta se creó y quedó pendiente de activación.')
  }
  return <div className="users-page">
    <div className="users-heading"><div><span className="users-eyebrow">SISTEMA INTEGRAL DE ASISTENCIA ESTUDIANTIL</span><h1>Gestión de usuarios</h1><p>Administra las cuentas y los permisos del personal de SIAE.</p></div><div className="users-heading-actions"><button className="users-create" onClick={() => { setEditing(null); setShowNewUser(true) }}><UserPlus size={16}/> Crear usuario</button><button className="users-export" onClick={exportUsers}><Download size={16}/> Exportar</button></div></div>
    <section className="users-table-card"><div className="users-toolbar"><div className="users-search"><Search size={17}/><input aria-label="Buscar usuarios" placeholder="Buscar usuarios..." value={search} onChange={e => setSearch(e.target.value)}/><button aria-label="Filtrar usuarios"><Filter size={16}/></button></div><label className="users-filter"><span>Filtrar por rol</span><select aria-label="Filtrar por rol" value={roleFilter} onChange={e => setRoleFilter(e.target.value)}><option>Todos</option><option>Superadministrador</option><option>Coordinador</option><option>Usuario</option></select><ChevronDown size={14}/></label><label className="users-filter"><span>Filtrar por estado</span><select aria-label="Filtrar por estado" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}><option>Todos</option><option>Activo</option><option>Inactivo</option><option>Pendiente</option></select><ChevronDown size={14}/></label></div>
      <div className="users-table-wrap"><table className="users-table"><thead><tr><th className="check-column"><input type="checkbox" aria-label="Seleccionar todos los usuarios"/></th><th>Avatar</th><th>Nombre</th><th>Correo</th><th>Rol</th><th>Estado</th><th>Último acceso</th><th>Acciones</th></tr></thead><tbody>{loading ? <tr><td colSpan={8} className="users-loading-cell">Cargando cuentas desde la base de datos…</td></tr> : visibleUsers.map((user, index) => <tr key={user.email} className={index % 2 ? 'user-row-shaded' : ''}><td><input type="checkbox" aria-label={`Seleccionar a ${user.name}`}/></td><td><div className={`user-avatar user-avatar-${index % 4}`}>{user.avatar}</div></td><td className="user-name">{user.name}</td><td className="user-email">{user.email}</td><td><span className={`user-role user-role-${user.role.toLocaleLowerCase('es')}`}>{user.role}</span></td><td><span className={`user-state user-state-${user.status.toLocaleLowerCase('es')}`}>{user.status}</span></td><td className="user-last-login">{user.lastLogin}</td><td><div className="user-actions"><button aria-label={`Editar a ${user.name}`} title="Editar usuario" onClick={() => { setEditing(user); setShowNewUser(true) }}><Pencil size={15}/></button><button aria-label={`Eliminar a ${user.name}`} title="Eliminar usuario" onClick={() => { setUsers(current => current.filter(item => item.email !== user.email)); onNotify('La cuenta se eliminó de la lista.') }}><Trash2 size={15}/></button><button aria-label={`Más acciones para ${user.name}`} title="Más acciones" onClick={() => onNotify(`Cuenta de ${user.name}: ${user.status.toLocaleLowerCase('es')}.`)}><MoreHorizontal size={17}/></button></div></td></tr>)}</tbody></table>{!loading && visibleUsers.length === 0 && <div className="users-empty">No hay usuarios registrados que coincidan con la búsqueda y los filtros.</div>}</div>
      <div className="users-pagination"><span>{loading ? 'Consultando cuentas…' : <>Se muestran <b>{visibleUsers.length}</b> de <b>{users.length}</b> usuarios</>}</span><div><button aria-label="Primera página" disabled><ChevronsLeft size={15}/></button><button aria-label="Página anterior" disabled><ChevronLeft size={15}/></button><button className="users-page-current">1</button><button aria-label="Página siguiente" disabled><ChevronRight size={15}/></button><button aria-label="Última página" disabled><ChevronsRight size={15}/></button></div></div>
    </section>
    {showNewUser && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) closeModal() }}><form className="modal" onSubmit={saveUser}><div className="modal-header"><div><span className="modal-kicker">CUENTAS Y PERMISOS</span><h2>{editing ? 'Editar usuario' : 'Crear usuario'}</h2><p>Captura los datos de la cuenta institucional.</p></div><button type="button" className="icon-button" onClick={closeModal} aria-label="Cerrar"><X size={19}/></button></div><label htmlFor="user-name">Nombre completo</label><input id="user-name" name="name" placeholder="Nombre y apellidos" required defaultValue={editing?.name}/><label htmlFor="user-email">Correo institucional</label><input id="user-email" name="email" type="email" placeholder="nombre@cucei.udg.mx" required defaultValue={editing?.email}/><label htmlFor="user-role">Rol</label><select id="user-role" name="role" defaultValue={editing?.role ?? 'Usuario'}><option>Usuario</option><option>Coordinador</option><option>Superadministrador</option></select><p className="users-permission-note">Las cuentas nuevas quedan pendientes. Según el proyecto, solo el superadministrador debe autorizar y asignar cuentas de coordinación.</p><div className="modal-actions"><button type="button" className="outline-button" onClick={closeModal}>Cancelar</button><button className="primary-button" type="submit">{editing ? 'Guardar cambios' : 'Crear cuenta'}</button></div></form></div>}
  </div>
}
