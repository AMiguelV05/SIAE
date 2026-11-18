// Inicio de sesión y solicitud de cuenta conectados con la API del panel.
import React, { useState } from 'react'
import { ArrowRight, Eye, EyeOff, GraduationCap, KeyRound, LockKeyhole, UserRound, X } from 'lucide-react'
import type { AccessRequest } from '../datosCompartidos'
import { iniciarSesion } from '../api'
import type { AdminAutenticado } from '../api'

type DatosSolicitud = Omit<AccessRequest, 'id' | 'requestedAt' | 'status' | 'phone'> & { phone: string; password: string }

export function InicioSesion({ onLogin, onRequestAccess }: { onLogin: (user: AdminAutenticado) => void; onRequestAccess: (data: DatosSolicitud) => Promise<unknown> }) {
  const [remember, setRemember] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [showAccessForm, setShowAccessForm] = useState(false)
  const [accessError, setAccessError] = useState('')
  const [sendingRequest, setSendingRequest] = useState(false)
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const user = form.get('user')?.toString().trim().toLocaleLowerCase('es')
    const password = form.get('password')?.toString()
    if (!user || !password) { setError('Escribe tu correo institucional y contraseña para continuar.'); return }
    setError('')
    try {
      const authenticatedUser = await iniciarSesion(user, password)
      if (remember) localStorage.setItem('siae-admin-user', user)
      else localStorage.removeItem('siae-admin-user')
      onLogin(authenticatedUser)
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : 'No se pudo iniciar sesión.')
    }
  }
  return <main className="login-page login-page-solo">
    <div className="login-layout login-layout-solo">
      
      <section className="login-side"><form className="login-card" onSubmit={submit}>
        <div className="login-card-brand"><div className="card-logo"><GraduationCap size={23} strokeWidth={2.2}/></div><span><b>SIAE</b><small>Sistema Integral de<br/>Asistencia Estudiantil</small></span></div>
        <div className="login-heading"><div className="login-kicker">PORTAL ADMINISTRATIVO</div><h2>Bienvenido de nuevo</h2><p>Ingresa con tu cuenta institucional para continuar.</p></div>
        <label htmlFor="login-user">Correo institucional</label><div className="login-input-wrap"><UserRound size={17}/><input id="login-user" name="user" type="email" autoComplete="username" placeholder="nombre@cucei.udg.mx" required defaultValue={localStorage.getItem('siae-admin-user') ?? ''} onChange={() => setError('')}/></div>
        <div className="password-label-row"><label htmlFor="login-password">Contraseña</label><button type="button" onClick={() => setNotice('Solicita el restablecimiento de acceso con el administrador principal de tu división.')}>¿La olvidaste?</button></div><div className="login-input-wrap"><KeyRound size={17}/><input id="login-password" name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="Ingresa tu contraseña" required onChange={() => setError('')}/><button className="password-toggle" type="button" aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'} onClick={() => setShowPassword(value => !value)}>{showPassword ? <EyeOff size={16}/> : <Eye size={16}/>}</button></div>
        <label className="remember-option"><input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)}/><span className="custom-check"/><span>Recordar mi usuario</span></label>
        {error && <div className="login-error" role="alert">{error}</div>}{notice && <div className="login-notice" role="status">{notice}</div>}
        <button className="login-submit" type="submit">Iniciar sesión <ArrowRight size={17}/></button>
        <div className="login-security"><LockKeyhole size={13}/><span>Acceso exclusivo para personal autorizado</span></div>
        <div className="login-divider"><span/></div><p className="login-help">¿Necesitas una cuenta?</p><button type="button" className="login-access-request" onClick={() => { setNotice(''); setAccessError(''); setShowAccessForm(true) }}>Solicitar acceso administrativo</button>
      </form><footer className="login-copyright">© 2026 SIAE · CUCEI <span>•</span> Universidad de Guadalajara</footer>
      {showAccessForm && <div className="modal-backdrop login-access-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) setShowAccessForm(false) }}><form className="modal login-access-modal" onSubmit={async event => {
        event.preventDefault()
        const form = new FormData(event.currentTarget)
        const password = form.get('password')!.toString()
        const confirmation = form.get('confirmation')!.toString()
        if (password !== confirmation) { setAccessError('Las contraseñas no coinciden.'); return }
        setSendingRequest(true)
        try {
          await onRequestAccess({ name: form.get('name')!.toString().trim(), email: form.get('email')!.toString().trim(), phone: form.get('phone')!.toString().trim(), department: form.get('department')!.toString().trim(), reason: form.get('reason')!.toString().trim(), password })
          setShowAccessForm(false)
          setNotice('Tu solicitud quedó registrada para revisión del superadministrador.')
        } catch (requestError) {
          setAccessError(requestError instanceof Error ? requestError.message : 'No se pudo enviar la solicitud.')
        } finally {
          setSendingRequest(false)
        }
      }}><div className="modal-header"><div><span className="modal-kicker">SOLICITUD DE CUENTA</span><h2>Solicitar acceso</h2><p>El superadministrador revisará tus datos y definirá tus permisos.</p></div><button type="button" className="icon-button" onClick={() => setShowAccessForm(false)} aria-label="Cerrar"><X size={17}/></button></div><label htmlFor="access-name">Nombre completo</label><input id="access-name" name="name" required maxLength={100} placeholder="Nombre y apellidos"/><label htmlFor="access-email">Correo institucional</label><input id="access-email" name="email" type="email" required maxLength={120} placeholder="nombre@cucei.udg.mx"/><label htmlFor="access-phone">Teléfono de contacto</label><input id="access-phone" name="phone" type="tel" inputMode="numeric" autoComplete="tel-national" required minLength={10} maxLength={10} pattern="[0-9]{10}" title="Escribe exactamente 10 dígitos, sin espacios ni letras." onChange={event => { event.currentTarget.value = event.currentTarget.value.replace(/\D/g, '').slice(0, 10) }} placeholder="10 dígitos"/><label htmlFor="access-department">Departamento o coordinación</label><input id="access-department" name="department" required maxLength={100} placeholder="Ej. Coordinación ICOM"/><label htmlFor="access-reason">¿Para qué necesitas el acceso?</label><textarea id="access-reason" name="reason" rows={3} required minLength={10} maxLength={400} placeholder="Describe brevemente las tareas que realizarás..."/><label htmlFor="access-password">Crea tu contraseña (mínimo 12 caracteres)</label><input id="access-password" name="password" type="password" autoComplete="new-password" required minLength={12} maxLength={128} placeholder="Contraseña segura"/><label htmlFor="access-confirmation">Confirma tu contraseña</label><input id="access-confirmation" name="confirmation" type="password" autoComplete="new-password" required minLength={12} maxLength={128} placeholder="Repite la contraseña"/>{accessError && <div className="login-error" role="alert">{accessError}</div>}<div className="modal-actions"><button type="button" className="outline-button" disabled={sendingRequest} onClick={() => setShowAccessForm(false)}>Cancelar</button><button type="submit" className="primary-button" disabled={sendingRequest}>{sendingRequest ? 'Enviando…' : <>Enviar solicitud <ArrowRight size={15}/></>}</button></div></form></div>}
      </section>
    </div>
    <span className="login-version">SIAE · PANEL ADMINISTRATIVO</span>
  </main>
}

