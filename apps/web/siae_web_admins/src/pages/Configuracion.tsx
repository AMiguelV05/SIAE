// Preferencias generales del panel y reglas recomendadas para el asistente SIAE.
import { useState } from 'react'
import { Bell, BookOpenCheck, Settings, ShieldCheck, Sparkles } from 'lucide-react'
import type { AdminAutenticado } from '../api'
import { actualizarNombreAdministrador } from '../api'

type AjustesPanel = {
  systemName: string
  institution: string
  supportEmail: string
  period: string
  language: string
  timeZone: string
  notices: boolean
  urgentAlerts: boolean
  weeklySummary: boolean
  assistantCitations: boolean
  humanReview: boolean
}

function ajustesPredeterminados(): AjustesPanel {
  return {
    systemName: 'Sistema Integral de Asistencia Estudiantil',
    institution: 'CUCEI · Universidad de Guadalajara',
    supportEmail: 'soporte.siae@cucei.udg.mx',
    period: '2026-B',
    language: 'Español (México)',
    timeZone: 'Ciudad de México',
    notices: true,
    urgentAlerts: true,
    weeklySummary: false,
    assistantCitations: true,
    humanReview: true,
  }
}

function leerAjustes(key: string): AjustesPanel {
  try {
    const saved = localStorage.getItem(key)
    return saved ? { ...ajustesPredeterminados(), ...JSON.parse(saved) as Partial<AjustesPanel> } : ajustesPredeterminados()
  } catch {
    return ajustesPredeterminados()
  }
}

export function Configuracion({ onNotify, admin, onAdminUpdated }: { onNotify: (message: string) => void; admin: AdminAutenticado; onAdminUpdated: (admin: AdminAutenticado) => void }) {
  const [adminName, setAdminName] = useState(admin.name)
  const [savingName, setSavingName] = useState(false)
  const storageKey = `siae-configuracion-${admin.id}`
  const [settings, setSettings] = useState<AjustesPanel>(() => leerAjustes(storageKey))
  const changeSetting = <K extends keyof AjustesPanel>(key: K, value: AjustesPanel[K]) => setSettings(current => ({ ...current, [key]: value }))
  const saveSettings = () => {
    localStorage.setItem(storageKey, JSON.stringify(settings))
    onNotify('La configuración se guardó en este navegador.')
  }
  // Dibuja un interruptor controlado reutilizable para las preferencias booleanas.
  const toggle = (key: keyof AjustesPanel, title: string, description: string) => <label className="settings-toggle"><span><b>{title}</b><small>{description}</small></span><input type="checkbox" checked={Boolean(settings[key])} onChange={event => changeSetting(key, event.target.checked)}/><i/></label>

  async function guardarNombre(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSavingName(true)
    try {
      const adminActualizado = await actualizarNombreAdministrador(adminName.trim())
      onAdminUpdated(adminActualizado)
      setAdminName(adminActualizado.name)
      onNotify('El nombre del administrador se guardó en la base de datos.')
    } catch (error) {
      onNotify(error instanceof Error ? error.message : 'No se pudo guardar el nombre del administrador.')
    } finally {
      setSavingName(false)
    }
  }

  return <div className="settings-page">
    <div className="settings-heading"><div><span className="settings-eyebrow">PREFERENCIAS DEL ESPACIO DE TRABAJO</span><h1>Configuración</h1><p>Administra los datos institucionales y el comportamiento del panel SIAE.</p></div><button className="primary-button" onClick={saveSettings}>Guardar cambios</button></div>
    <div className="settings-layout">
      <div className="settings-sections">
        <section className="settings-card" id="cuenta"><div className="settings-card-heading"><span className="settings-icon settings-icon-green"><ShieldCheck size={17}/></span><div><h2>Cuenta del administrador</h2><p>Actualiza el nombre que se guarda en la base de datos y aparece en el panel.</p></div></div><form onSubmit={guardarNombre}><div className="settings-fields settings-fields-two"><label htmlFor="settings-admin-name">Nombre completo<input id="settings-admin-name" value={adminName} onChange={event => setAdminName(event.target.value)} required minLength={3} maxLength={101} autoComplete="name"/></label><label htmlFor="settings-admin-email">Correo institucional<input id="settings-admin-email" value={admin.email} readOnly/></label></div><p className="settings-hint">Escribe nombre y apellido. El correo y los permisos se mantienen sin cambios.</p><div className="settings-form-actions"><button className="primary-button" type="submit" disabled={savingName || adminName.trim() === admin.name}>{savingName ? 'Guardando…' : 'Guardar nombre'}</button></div></form></section>
        <section className="settings-card" id="institucion"><div className="settings-card-heading"><span className="settings-icon"><ShieldCheck size={17}/></span><div><h2>Datos institucionales</h2><p>Identidad que aparece en el panel y los reportes.</p></div></div><div className="settings-fields"><label>Nombre del sistema<input value={settings.systemName} onChange={event => changeSetting('systemName', event.target.value)}/></label><label>Institución<input value={settings.institution} onChange={event => changeSetting('institution', event.target.value)}/></label><label>Correo de soporte<input type="email" value={settings.supportEmail} onChange={event => changeSetting('supportEmail', event.target.value)}/></label><label>Periodo académico<select value={settings.period} onChange={event => changeSetting('period', event.target.value)}><option>2026-B</option><option>2027-A</option><option>2027-B</option></select></label></div></section>
        <section className="settings-card" id="preferencias"><div className="settings-card-heading"><span className="settings-icon settings-icon-green"><Settings size={17}/></span><div><h2>Preferencias regionales</h2><p>Formato usado para fechas y horarios del panel.</p></div></div><div className="settings-fields settings-fields-two"><label>Idioma<select value={settings.language} onChange={event => changeSetting('language', event.target.value)}><option>Español (México)</option><option>Español (España)</option></select></label><label>Zona horaria<select value={settings.timeZone} onChange={event => changeSetting('timeZone', event.target.value)}><option>Ciudad de México</option><option>Tijuana</option><option>Chihuahua</option><option>Cancún</option></select></label></div><p className="settings-hint">Los reportes y las fechas se mostrarán con el formato regional seleccionado.</p></section>
        <section className="settings-card" id="notificaciones"><div className="settings-card-heading"><span className="settings-icon settings-icon-blue"><Bell size={17}/></span><div><h2>Notificaciones</h2><p>Elige qué actividad administrativa quieres seguir.</p></div></div><div className="settings-toggles">{toggle('notices', 'Nuevos tickets', 'Avisar cuando llegue una solicitud estudiantil.')}{toggle('urgentAlerts', 'Tickets urgentes o escalados', 'Resaltar casos que requieren atención prioritaria.')}{toggle('weeklySummary', 'Resumen semanal', 'Recibir un resumen de actividad y tiempos de respuesta.')}</div></section>
        <section className="settings-card" id="asistente"><div className="settings-card-heading"><span className="settings-icon settings-icon-green"><Sparkles size={17}/></span><div><h2>Asistente SIAE y fuentes</h2><p>Criterios recomendados para las respuestas automatizadas.</p></div></div><div className="settings-toggles">{toggle('assistantCitations', 'Solicitar citas de documentos oficiales', 'Las respuestas deben señalar el documento que las respalda.')}{toggle('humanReview', 'Revisión humana para casos sensibles', 'Enviar casos ambiguos o de prioridad alta a coordinación.')}</div><div className="settings-source-reminder"><BookOpenCheck size={16}/><span>Administra reglamentos, calendarios y convocatorias desde <b>Documentos</b>. Mantén las fuentes vigentes para evitar respuestas desactualizadas.</span></div></section>
      </div>
    </div>
  </div>
}
