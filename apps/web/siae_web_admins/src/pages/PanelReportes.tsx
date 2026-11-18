// Indicadores, tendencias y rendimiento por coordinación con datos demostrativos.
import { useState } from 'react'
import { ChevronDown, Download, Filter } from 'lucide-react'

export function PanelReportes() {
  const [period, setPeriod] = useState('Últimos 30 días (Mes actual)')
  const [department, setDepartment] = useState('Todos los departamentos')
  // Valores de muestra para comparar solicitudes observadas con la proyección del asistente.
  const weeks = [
    { day: 'Lun', real: 44, forecast: 38 }, { day: 'Mar', real: 64, forecast: 59 },
    { day: 'Mié', real: 70, forecast: 66 }, { day: 'Jue', real: 67, forecast: 68 },
    { day: 'Vie', real: 48, forecast: 54 }, { day: 'Sáb', real: 24, forecast: 20 },
  ]
  const common = [
    { name: 'Titulación por Promedio', count: 340, color: 'blue' },
    { name: 'Emisión de Justificante Médico', count: 280, color: 'green' },
    { name: 'Liberación de Servicio Social / Inglés', count: 190, color: 'orange' },
    { name: 'Altas y Bajas de Materias', count: 140, color: 'purple' },
    { name: 'Revalidación / Acreditación Externa', count: 90, color: 'gray' },
  ]
  // Métricas ilustrativas por coordinación; sustituir por datos del servicio al integrarlo.
  const coordinations = [
    { name: 'Mtro. Roberto Flores', area: 'ICOM', assigned: 142, resolved: 138, time: '1.2 h', efficiency: 97 },
    { name: 'Dra. Elena Vázquez', area: 'Control Escolar', assigned: 210, resolved: 195, time: '2.1 h', efficiency: 92 },
    { name: 'Ing. Laura Méndez', area: 'INNI', assigned: 126, resolved: 113, time: '2.7 h', efficiency: 90 },
  ]
  return <div className="reports-page">
    <div className="reports-heading"><div><h1>Centro de reportes y estadísticas SIAE</h1><p>Indicadores para comprender la atención y anticipar la demanda.</p></div><div className="reports-period"><span>CUCEI · UdeG</span><i/><small>Periodo 2026-B</small></div></div>
    <section className="reports-filters"><div className="report-filter-title"><Filter size={15}/><b>Filtros de reporte:</b></div><label className="report-select"><span>{period}</span><select aria-label="Filtrar por periodo" value={period} onChange={e => setPeriod(e.target.value)}><option>Últimos 7 días</option><option>Últimos 30 días (Mes actual)</option><option>Últimos 90 días</option></select><ChevronDown size={15}/></label><label className="report-select"><span>{department}</span><select aria-label="Filtrar por departamento" value={department} onChange={e => setDepartment(e.target.value)}><option>Todos los departamentos</option><option>ICOM</option><option>Control Escolar</option><option>INNI</option><option>IBIM</option></select><ChevronDown size={15}/></label><button className="report-export" onClick={() => window.print()}><Download size={16}/> Exportar reporte PDF</button></section>
    <div className="report-metrics"><article className="report-metric"><span>Tiempo promedio de respuesta</span><strong className="metric-blue">1.8 <small>Horas</small></strong><p className="metric-positive">↓ 45% de reducción<br/>vs. filas físicas</p></article><article className="report-metric"><span>Índice de desahogo digital</span><strong className="metric-green">84.2%</strong><p>Trámites resueltos<br/>en línea sin cita</p></article><article className="report-metric"><span>Precisión de clasificación RAG</span><strong>96.5%</strong><p className="metric-positive">Asignación correcta<br/>automática</p></article><article className="report-metric"><span>Satisfacción estudiantil</span><strong className="metric-orange">4.8 / 5.0</strong><p>Basado en 1,240<br/>encuestas</p></article></div>
    <section className="report-card report-trend"><div className="report-card-heading"><div><h2>Tendencia de solicitudes (semanales)</h2><p>Proyección RAG comparada con las solicitudes reales · {period}</p></div><span className="forecast-badge"><i/> Predicción activa</span></div><div className="trend-chart"><div className="trend-y-axis"><span>80</span><span>60</span><span>40</span><span>20</span><span>0</span></div><div className="trend-plot"><div className="trend-gridlines"><i/><i/><i/><i/><i/></div><div className="trend-bars">{weeks.map(week => <div className="trend-group" key={week.day}><div className="trend-bar-pair"><span className="trend-bar trend-real" style={{height:`${week.real}%`}}/><span className="trend-bar trend-forecast" style={{height:`${week.forecast}%`}}/></div><small>{week.day}</small></div>)}</div></div></div><div className="trend-legend"><span><i className="legend-real"/> Solicitudes reales</span><span><i className="legend-forecast"/> Predicción IA RAG</span></div></section>
    <section className="report-card frequent-report"><div className="report-card-heading"><div><h2>Los 5 trámites más frecuentes</h2><p>Distribución del volumen de atención · {department}</p></div></div><div className="frequent-list">{common.map(item => <div className="frequent-item" key={item.name}><div><b>{item.name}</b><span>{item.count} solicitudes</span></div><div className="frequent-track"><i className={`frequent-fill fill-${item.color}`} style={{width:`${item.count / 3.4}%`}}/></div></div>)}</div></section>
    <section className="report-card coordination-report"><div className="report-card-heading"><div><h2>Rendimiento por coordinación</h2><p>Métricas operativas del personal administrativo · {department}</p></div></div><div className="coordination-table-wrap"><table className="coordination-table"><thead><tr><th>Coordinador / área</th><th>Tickets asignados</th><th>Resueltos</th><th>Tiempo promedio</th><th>Eficiencia</th></tr></thead><tbody>{coordinations.filter(item => department === 'Todos los departamentos' || item.area === department).map(item => <tr key={item.name}><td><b>{item.name}</b><small>{item.area}</small></td><td>{item.assigned}</td><td className="resolved-count">{item.resolved}</td><td>{item.time}</td><td><span className={`efficiency efficiency-${item.efficiency > 94 ? 'high' : 'medium'}`}>{item.efficiency}%</span></td></tr>)}</tbody></table>{coordinations.filter(item => department === 'Todos los departamentos' || item.area === department).length === 0 && <div className="users-empty">No hay métricas de muestra para este departamento.</div>}</div></section>
  </div>
}
