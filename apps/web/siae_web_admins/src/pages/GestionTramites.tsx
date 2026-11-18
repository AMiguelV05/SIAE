// Catálogo administrativo de trámites, con búsqueda, categorías y edición de registros.
import React, { useState } from 'react'
import { ArrowLeftRight, BookOpen, ChevronLeft, ChevronRight, Download, Eye, FileCheck2, Pencil, Plus, PlusCircle, Search, Trash2, X } from 'lucide-react'
import { Procedure } from '../datosCompartidos'

export function GestionTramites({ procedures, setProcedures, onNotify }: { procedures: Procedure[]; setProcedures: React.Dispatch<React.SetStateAction<Procedure[]>>; onNotify: (message: string) => void }) {
  const [category, setCategory] = useState('Todos')
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<Procedure | null>(null)
  const categories = ['Todos', 'Titulación', 'Agenda / Materias', 'Servicio / Prácticas', 'Justificantes', 'Becas', 'Otros']
  // Solo se muestran trámites que coinciden con la categoría y el texto de búsqueda.
  const visible = procedures.filter(item => (category === 'Todos' || item.category === category) && `${item.title} ${item.department}`.toLocaleLowerCase('es').includes(search.toLocaleLowerCase('es')))
  const iconFor = (icon: Procedure['icon']) => {
    if (icon === 'degree') return <FileCheck2 size={20}/>
    if (icon === 'medical') return <PlusCircle size={20}/>
    if (icon === 'language') return <BookOpen size={20}/>
    if (icon === 'transfer') return <ArrowLeftRight size={20}/>
    return <Plus size={20}/>
  }
  const closeForm = () => { setShowModal(false); setEditing(null) }
  // Conserva los cambios del trámite actual o agrega uno nuevo al catálogo.
  const saveProcedure = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const title = form.get('title')!.toString().trim()
    const department = form.get('department')!.toString().trim()
    const next: Procedure = { id: editing?.id ?? Date.now(), title, department, attention: form.get('attention')!.toString(), status: editing?.status ?? 'Pendiente', category: form.get('category')!.toString(), icon: editing?.icon ?? 'degree' }
    setProcedures(current => editing ? current.map(item => item.id === editing.id ? next : item) : [next, ...current])
    closeForm()
    onNotify(editing ? 'El trámite se actualizó correctamente.' : 'El trámite se agregó correctamente.')
  }
  const changeStatus = (id: number) => setProcedures(current => current.map(item => item.id === id ? { ...item, status: item.status === 'Pendiente' ? 'En proceso' : item.status === 'En proceso' ? 'Completado' : 'Pendiente' } : item))

  return <div className="procedures-page">
    <div className="procedures-heading"><div><span className="procedures-eyebrow">SISTEMA INTEGRAL DE ASISTENCIA ESTUDIANTIL</span><h1>Gestión de trámites</h1><p>Administra y consulta los trámites disponibles para la comunidad universitaria.</p></div><div className="procedures-heading-actions"><button onClick={() => onNotify('La exportación de trámites estará disponible al conectar los datos.')}><Download size={16}/> Exportar</button><button className="procedure-create" onClick={() => { setEditing(null); setShowModal(true) }}><Plus size={17}/> Crear trámite</button></div></div>
    <section className="procedures-panel"><div className="procedure-search-row"><div className="procedure-search"><Search size={18}/><input aria-label="Buscar trámites o documentos" placeholder="Buscar trámites o documentos..." value={search} onChange={e => setSearch(e.target.value)}/><button aria-label="Buscar" onClick={() => {}}><Search size={18}/></button></div></div><div className="procedure-categories">{categories.map((item, index) => <button key={item} className={`category-chip ${category === item ? 'category-selected' : ''} ${index === 0 || index === 3 ? 'category-green' : ''}`} onClick={() => setCategory(item)}><i/>{item}</button>)}</div>
      <div className="procedure-table-wrap"><table className="procedure-table"><thead><tr><th>Icono</th><th>Nombre del trámite</th><th>Departamento</th><th>Tiempo estimado / atención</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>{visible.map((item, index) => <tr key={item.id} className={index % 2 === 0 ? 'procedure-row-highlight' : ''}><td><span className="procedure-icon">{iconFor(item.icon)}</span></td><td className="procedure-title">{item.title}</td><td>{item.department}</td><td className="procedure-attention">Requisitos oficiales<br/><b>{item.attention}</b></td><td><button className={`procedure-state procedure-state-${item.status.toLocaleLowerCase('es').replace(' ', '-')}`} onClick={() => changeStatus(item.id)} title="Cambiar estado">{item.status}</button></td><td><div className="procedure-actions"><button aria-label={`Editar ${item.title}`} title="Editar" onClick={() => { setEditing(item); setShowModal(true) }}><Pencil size={16}/></button><button aria-label={`Ver ${item.title}`} title="Ver detalles" onClick={() => onNotify(`${item.title} · ${item.department} · ${item.attention}`)}><Eye size={17}/></button><button aria-label={`Eliminar ${item.title}`} title="Eliminar" onClick={() => { setProcedures(current => current.filter(procedure => procedure.id !== item.id)); onNotify('El trámite se eliminó de la lista.') }}><Trash2 size={16}/></button></div></td></tr>)}</tbody></table>{visible.length === 0 && <div className="users-empty">No hay trámites para esta búsqueda o categoría.</div>}</div>
      <div className="procedure-table-footer"><span>Se muestran <b>{visible.length}</b> de <b>{procedures.length}</b> trámites</span><div><button disabled aria-label="Página anterior"><ChevronLeft size={15}/></button><button className="procedure-page-current">1</button><button disabled aria-label="Página siguiente"><ChevronRight size={15}/></button></div></div>
    </section>
    {showModal && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) closeForm() }}><form className="modal" onSubmit={saveProcedure}><div className="modal-header"><div><span className="modal-kicker">CATÁLOGO INSTITUCIONAL</span><h2>{editing ? 'Editar trámite' : 'Crear trámite'}</h2><p>Agrega información clara y vigente del proceso.</p></div><button type="button" className="icon-button" onClick={closeForm} aria-label="Cerrar"><X size={19}/></button></div><label htmlFor="procedure-title">Nombre del trámite</label><input id="procedure-title" name="title" required placeholder="Ej. Solicitud de titulación" defaultValue={editing?.title}/><label htmlFor="procedure-department">Departamento o coordinación</label><input id="procedure-department" name="department" required placeholder="Ej. Coordinación de carrera" defaultValue={editing?.department}/><label htmlFor="procedure-category">Categoría</label><select id="procedure-category" name="category" defaultValue={editing?.category ?? 'Otros'}>{categories.filter(item => item !== 'Todos').map(item => <option key={item}>{item}</option>)}</select><label htmlFor="procedure-attention">Tiempo estimado de atención</label><input id="procedure-attention" name="attention" required placeholder="Ej. En línea · 24–48 h" defaultValue={editing?.attention}/><div className="modal-actions"><button type="button" className="outline-button" onClick={closeForm}>Cancelar</button><button type="submit" className="primary-button">{editing ? 'Guardar cambios' : 'Crear trámite'}</button></div></form></div>}
  </div>
}
