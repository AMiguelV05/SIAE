// Gestión de avisos oficiales, incluyendo su público, vigencia y estado editorial.
import React, { useEffect, useState } from 'react'
import { ChevronDown, ChevronLeft, ChevronRight, Eye, Pencil, Plus, Search, Trash2, X } from 'lucide-react'
import { PublicationStatus, Publication } from '../datosCompartidos'

function normalizarTexto(value: string) {
  return value.toLocaleLowerCase('es').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
}

function fechaActualLocal() {
  const hoy = new Date()
  hoy.setMinutes(hoy.getMinutes() - hoy.getTimezoneOffset())
  return hoy.toISOString().slice(0, 10)
}

export function GestionPublicaciones({ publications, setPublications, authorName, onNotify }: { publications: Publication[]; setPublications: React.Dispatch<React.SetStateAction<Publication[]>>; authorName: string; onNotify: (message: string) => void }) {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('Todas')
  const [audience, setAudience] = useState('Todos los públicos')
  const [status, setStatus] = useState('Todos')
  const [dateFilter, setDateFilter] = useState('Cualquier fecha')
  const [page, setPage] = useState(1)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<Publication | null>(null)
  const [viewing, setViewing] = useState<Publication | null>(null)
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const categories = ['Todas', 'Becas', 'Becas y movilidad', 'Control escolar', 'Servicio social', 'Titulación']
  // Combina los filtros de texto, categoría, carrera destinataria, estado y fecha.
  const filtered = publications.filter(item => {
    const matchesSearch = normalizarTexto(`${item.title} ${item.author} ${item.category} ${item.audience} ${item.content}`).includes(normalizarTexto(search.trim()))
    const matchesCategory = category === 'Todas' || item.category === category
    const matchesAudience = audience === 'Todos los públicos' || item.audience === audience
    const matchesStatus = status === 'Todos' || item.status === status
    const ageDays = (Date.now() - new Date(`${item.date}T12:00:00`).getTime()) / 86400000
    const matchesDate = dateFilter === 'Cualquier fecha' || (ageDays >= 0 && (dateFilter === 'Últimos 7 días' ? ageDays <= 7 : ageDays <= 30))
    return matchesSearch && matchesCategory && matchesAudience && matchesStatus && matchesDate
  })
  const totalPages = Math.max(1, Math.ceil(filtered.length / 5))
  const pageItems = filtered.slice((page - 1) * 5, page * 5)
  const visibleIds = pageItems.map(item => item.id)
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every(id => selectedIds.includes(id))
  useEffect(() => { if (page > totalPages) setPage(totalPages) }, [page, totalPages])
  const closeForm = () => { setShowModal(false); setEditing(null) }
  // Guarda una publicación nueva o reemplaza la que se está editando.
  const savePublication = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const title = form.get('title')!.toString().trim()
    const next: Publication = { id: editing?.id ?? Date.now(), title, author: editing?.author ?? authorName, category: form.get('category')!.toString(), audience: form.get('audience')!.toString(), status: form.get('status')!.toString() as PublicationStatus, date: form.get('date')!.toString(), content: form.get('content')!.toString().trim() }
    setPublications(current => editing ? current.map(item => item.id === editing.id ? next : item) : [next, ...current])
    setPage(1)
    closeForm()
    onNotify(editing ? 'La publicación se actualizó correctamente.' : 'La publicación se creó correctamente.')
  }
  const showEdit = (item: Publication) => { setEditing(item); setShowModal(true) }
  const toggleVisibleSelection = () => setSelectedIds(current => allVisibleSelected ? current.filter(id => !visibleIds.includes(id)) : Array.from(new Set([...current, ...visibleIds])))
  const toggleSelection = (id: number) => setSelectedIds(current => current.includes(id) ? current.filter(selectedId => selectedId !== id) : [...current, id])
  const deleteSelected = () => {
    if (!selectedIds.length) return
    setPublications(current => current.filter(item => !selectedIds.includes(item.id)))
    onNotify(`Se eliminaron ${selectedIds.length} publicaciones seleccionadas.`)
    setSelectedIds([])
  }
  const formattedDate = (date: string) => new Intl.DateTimeFormat('es-MX', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(`${date}T12:00:00`))
  const statusClass = (value: PublicationStatus) => value === 'Publicado' ? 'publicado' : value === 'Borrador' ? 'borrador' : 'revision'

  return <div className="publications-page">
    <div className="publications-heading"><div><h1>Gestión de publicaciones</h1><p>Administra los avisos oficiales que verá la comunidad estudiantil.</p></div><button className="publication-create" onClick={() => { setEditing(null); setShowModal(true) }}><Plus size={17}/> Crear nueva publicación</button></div>
    <section className="publications-panel"><div className="publications-toolbar"><div className="publication-search"><input aria-label="Buscar publicaciones" placeholder="Buscar publicaciones..." value={search} onChange={e => { setSearch(e.target.value); setPage(1) }}/><button type="button" aria-label="Buscar" onClick={() => setPage(1)}><Search size={17}/></button></div><label className="publication-filter"><span>Filtrar por categoría</span><select aria-label="Filtrar por categoría" value={category} onChange={e => { setCategory(e.target.value); setPage(1) }}>{categories.map(item => <option key={item}>{item}</option>)}</select><ChevronDown size={14}/></label><label className="publication-filter"><span>Público</span><select aria-label="Filtrar por público" value={audience} onChange={e => { setAudience(e.target.value); setPage(1) }}><option>Todos los públicos</option><option>Todas las carreras</option><option>ICOM</option><option>INNI</option><option>INRO</option><option>IBIM</option></select><ChevronDown size={14}/></label><label className="publication-filter"><span>Filtrar por estado</span><select aria-label="Filtrar por estado" value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}><option>Todos</option><option>Publicado</option><option>Borrador</option><option>En revisión</option></select><ChevronDown size={14}/></label><label className="publication-filter"><span>Filtrar por fecha</span><select aria-label="Filtrar por fecha" value={dateFilter} onChange={e => { setDateFilter(e.target.value); setPage(1) }}><option>Cualquier fecha</option><option>Últimos 7 días</option><option>Últimos 30 días</option></select><ChevronDown size={14}/></label></div>{selectedIds.length > 0 && <div className="publication-selection"><span>{selectedIds.length} seleccionada{selectedIds.length === 1 ? '' : 's'}</span><button type="button" onClick={deleteSelected}><Trash2 size={14}/> Eliminar seleccionadas</button></div>}
      <div className="publications-table-wrap"><table className="publications-table"><thead><tr><th className="publication-check"><input type="checkbox" aria-label="Seleccionar publicaciones de esta página" checked={allVisibleSelected} onChange={toggleVisibleSelection}/></th><th>Título de publicación</th><th>Autor</th><th>Categoría</th><th>Público</th><th>Estado</th><th>Fecha de publicación</th><th>Acciones</th></tr></thead><tbody>{pageItems.map((item, index) => <tr key={item.id} className={index % 2 === 0 ? 'publication-row-highlight' : ''}><td><input type="checkbox" aria-label={`Seleccionar ${item.title}`} checked={selectedIds.includes(item.id)} onChange={() => toggleSelection(item.id)}/></td><td className="publication-title-cell">{item.title}</td><td>{item.author}</td><td>{item.category}</td><td>{item.audience}</td><td><span className={`publication-state publication-state-${statusClass(item.status)}`}>{item.status}</span></td><td>{formattedDate(item.date)}</td><td><div className="publication-actions"><button aria-label={`Editar ${item.title}`} title="Editar publicación" onClick={() => showEdit(item)}><Pencil size={16}/></button><button aria-label={`Ver ${item.title}`} title="Ver publicación" onClick={() => setViewing(item)}><Eye size={17}/></button><button aria-label={`Eliminar ${item.title}`} title="Eliminar publicación" onClick={() => { setPublications(current => current.filter(post => post.id !== item.id)); setSelectedIds(current => current.filter(id => id !== item.id)); onNotify('La publicación se eliminó de la lista.') }}><Trash2 size={16}/></button></div></td></tr>)}</tbody></table>{pageItems.length === 0 && <div className="users-empty">No hay publicaciones para los filtros seleccionados.</div>}</div>
      <div className="publications-pagination"><span>Se muestran <b>{pageItems.length}</b> de <b>{filtered.length}</b> publicaciones</span><div><span>Página {page} de {totalPages}</span><button aria-label="Página anterior" disabled={page <= 1} onClick={() => setPage(value => value - 1)}><ChevronLeft size={15}/></button><button aria-label="Página siguiente" disabled={page >= totalPages} onClick={() => setPage(value => value + 1)}><ChevronRight size={15}/></button></div></div>
    </section>
    {showModal && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) closeForm() }}><form className="modal" onSubmit={savePublication}><div className="modal-header"><div><span className="modal-kicker">AVISOS OFICIALES</span><h2>{editing ? 'Editar publicación' : 'Crear publicación'}</h2><p>Comparte información clara y vigente con los estudiantes.</p></div><button type="button" className="icon-button" onClick={closeForm} aria-label="Cerrar"><X size={19}/></button></div><label htmlFor="publication-title">Título</label><input id="publication-title" name="title" required maxLength={120} placeholder="Escribe el título del aviso" defaultValue={editing?.title}/><label htmlFor="publication-category">Categoría</label><select id="publication-category" name="category" defaultValue={editing?.category ?? 'Control escolar'}>{categories.filter(item => item !== 'Todas').map(item => <option key={item}>{item}</option>)}</select><label htmlFor="publication-audience">Dirigida a</label><select id="publication-audience" name="audience" defaultValue={editing?.audience ?? 'Todas las carreras'}><option>Todas las carreras</option><option>ICOM</option><option>INNI</option><option>INRO</option><option>IBIM</option></select><label htmlFor="publication-content">Contenido</label><textarea id="publication-content" name="content" rows={4} required placeholder="Describe la información que necesitan conocer los estudiantes..." defaultValue={editing?.content}/><div className="publication-form-row"><div><label htmlFor="publication-date">Fecha de publicación</label><input id="publication-date" type="date" name="date" required defaultValue={editing?.date ?? fechaActualLocal()}/></div><div><label htmlFor="publication-status">Estado</label><select id="publication-status" name="status" defaultValue={editing?.status ?? 'Borrador'}><option>Borrador</option><option>En revisión</option><option>Publicado</option></select></div></div><div className="modal-actions"><button type="button" className="outline-button" onClick={closeForm}>Cancelar</button><button type="submit" className="primary-button">{editing ? 'Guardar cambios' : 'Guardar publicación'}</button></div></form></div>}
    {viewing && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setViewing(null) }}><section className="modal publication-preview"><div className="modal-header"><div><span className="modal-kicker">{viewing.category.toLocaleUpperCase('es')}</span><h2>{viewing.title}</h2><p>Publicado por {viewing.author} · {formattedDate(viewing.date)}</p></div><button className="icon-button" onClick={() => setViewing(null)} aria-label="Cerrar"><X size={19}/></button></div><span className={`publication-state publication-state-${statusClass(viewing.status)}`}>{viewing.status}</span><p>{viewing.content}</p><div className="modal-actions"><button className="outline-button" onClick={() => setViewing(null)}>Cerrar</button><button className="primary-button" onClick={() => { setViewing(null); showEdit(viewing) }}><Pencil size={15}/>Editar publicación</button></div></section></div>}
  </div>
}
