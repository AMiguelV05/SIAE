// Biblioteca de fuentes que respaldan al asistente; el procesamiento actual es una simulación.
import React, { useState } from 'react'
import { BookOpenCheck, ChevronDown, CheckCircle2, FileText, RefreshCw, Search, UploadCloud, X } from 'lucide-react'
import { KnowledgeSource } from '../datosCompartidos'

export function BibliotecaDocumentos({ sources, setSources, onNotify }: { sources: KnowledgeSource[]; setSources: React.Dispatch<React.SetStateAction<KnowledgeSource[]>>; onNotify: (message: string) => void }) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('Todos')
  const ready = sources.filter(source => source.status === 'Indexado').length
  const pending = sources.filter(source => source.status === 'Pendiente' || source.status === 'Error').length
  const filtered = sources.filter(source => `${source.fileName} ${source.scope}`.toLocaleLowerCase('es').includes(search.toLocaleLowerCase('es')) && (statusFilter === 'Todos' || source.status === statusFilter))
  // Agrega los archivos seleccionados a la lista local sin extraer su contenido todavía.
  const addFiles = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.currentTarget.files ?? [])
    if (!files.length) return
    const created = files.map((file, index): KnowledgeSource => ({ id: Date.now() + index, fileName: file.name, type: file.name.split('.').pop()?.toUpperCase() ?? 'ARCHIVO', scope: 'Todas las carreras', updated: new Date().toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' }), status: 'Pendiente', chunks: 0 }))
    setSources(current => [...created, ...current])
    event.currentTarget.value = ''
    onNotify(`${created.length} archivo${created.length === 1 ? '' : 's'} agregado${created.length === 1 ? '' : 's'} a la lista.`)
  }
  // Simula la indexación; la extracción y vectorización reales deben hacerse en backend.
  const processSource = (id: number) => {
    setSources(current => current.map(source => source.id === id ? { ...source, status: 'Procesando' } : source))
    window.setTimeout(() => setSources(current => current.map(source => source.id === id ? { ...source, status: 'Indexado', chunks: Math.max(8, Math.floor(source.fileName.length * 1.7)), updated: new Date().toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' }) } : source)), 1300)
  }
  const statusClass = (status: KnowledgeSource['status']) => `source-status-${status.toLocaleLowerCase('es')}`
  return <div className="sources-page">
    <div className="sources-heading"><div><span className="sources-eyebrow">BASE DE CONOCIMIENTO · ASISTENTE RAG</span><h1>Documentos oficiales</h1><p>Administra las fuentes que respaldan las respuestas del asistente SIAE.</p></div><label className="source-upload"><UploadCloud size={17}/> Agregar documentos<input type="file" accept=".pdf,.doc,.docx,.txt" multiple onChange={addFiles}/></label></div>
    <div className="source-metrics"><article><span className="source-metric-icon"><BookOpenCheck size={18}/></span><div><small>Fuentes registradas</small><b>{sources.length}</b></div></article><article><span className="source-metric-icon source-green"><CheckCircle2 size={18}/></span><div><small>Indexadas para consulta</small><b>{ready}</b></div></article><article><span className="source-metric-icon source-orange"><RefreshCw size={18}/></span><div><small>Pendientes de procesar</small><b>{pending}</b></div></article><article><span className="source-metric-icon source-teal"><FileText size={18}/></span><div><small>Fragmentos consultables</small><b>{sources.reduce((sum, source) => sum + source.chunks, 0)}</b></div></article></div>
    <section className="sources-panel"><div className="sources-panel-heading"><div><h2>Biblioteca de fuentes</h2><p>Los documentos indexados se utilizan para generar respuestas con citas verificables.</p></div></div><div className="sources-toolbar"><label className="sources-search"><Search size={16}/><input aria-label="Buscar documentos" placeholder="Buscar por nombre o carrera..." value={search} onChange={e => setSearch(e.target.value)}/></label><label className="source-filter"><span>Estado</span><select aria-label="Filtrar documentos por estado" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}><option>Todos</option><option>Indexado</option><option>Pendiente</option><option>Procesando</option><option>Error</option></select><ChevronDown size={14}/></label></div><div className="source-list-wrap"><table className="source-table"><thead><tr><th>Documento</th><th>Alcance</th><th>Última actualización</th><th>Fragmentos</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>{filtered.map(source => <tr key={source.id}><td><div className="source-file"><span><FileText size={17}/></span><div><b>{source.fileName}</b><small>{source.type} · Fuente institucional</small></div></div></td><td>{source.scope}</td><td>{source.updated}</td><td>{source.chunks > 0 ? source.chunks : '—'}</td><td><span className={`source-status ${statusClass(source.status)}`}><i/>{source.status}</span></td><td><div className="source-actions">{source.status !== 'Procesando' && <button title={source.status === 'Indexado' ? 'Volver a procesar' : 'Procesar documento'} onClick={() => processSource(source.id)}><RefreshCw size={15}/>{source.status === 'Indexado' ? 'Actualizar' : 'Procesar'}</button>}<button className="source-delete" title="Quitar documento" aria-label={`Quitar ${source.fileName}`} onClick={() => { setSources(current => current.filter(item => item.id !== source.id)); onNotify('El documento se quitó de la biblioteca.') }}><X size={16}/></button></div></td></tr>)}</tbody></table>{filtered.length === 0 && <div className="users-empty">No hay documentos que coincidan con la búsqueda y los filtros.</div>}</div></section>
    {/* La interfaz acepta archivos, pero la lectura de PDF y la indexación aún no están conectadas. */}
  </div>
}
