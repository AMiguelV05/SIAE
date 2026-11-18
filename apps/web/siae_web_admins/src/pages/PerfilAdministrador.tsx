// Perfil de la cuenta administrativa y formularios de actualización de datos y contraseña.
import React, { useState } from 'react'
import { Building2, CalendarDays, Check, Eye, EyeOff, KeyRound, LockKeyhole, LogOut, Mail, MapPin, Phone, Save, ShieldCheck, UserRound } from 'lucide-react'
import type { AdminAutenticado } from '../api'
import { actualizarContrasenaAdministrador, actualizarNombreAdministrador } from '../api'

export function PerfilAdministrador({ onNotify, admin, onAdminUpdated, onLogout }: { onNotify: (message: string) => void; admin: AdminAutenticado; onAdminUpdated: (admin: AdminAutenticado) => void; onLogout: () => void | Promise<void> }) {
  const [mostrarContrasena, setMostrarContrasena] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [guardandoContrasena, setGuardandoContrasena] = useState(false)

  // Guarda el nombre en la API y sincroniza la sesión visible con la respuesta del servidor.
  const guardarPerfil = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setGuardando(true)
    const formulario = new FormData(event.currentTarget)
    const nombre = formulario.get('nombre')?.toString().trim() ?? ''
    const telefono = formulario.get('telefono')?.toString().trim() ?? ''
    try {
      const adminActualizado = await actualizarNombreAdministrador(nombre, telefono || null)
      onAdminUpdated(adminActualizado)
      setGuardando(false)
      onNotify('Los datos del perfil se actualizaron en la base de datos.')
    } catch (error) {
      setGuardando(false)
      onNotify(error instanceof Error ? error.message : 'No se pudo guardar el nombre del perfil.')
    }
  }

  // Comprueba longitud y coincidencia antes de enviar la solicitud de cambio.
  const cambiarContrasena = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const formulario = event.currentTarget
    const datos = new FormData(formulario)
    const actual = datos.get('actual')?.toString() ?? ''
    const nueva = datos.get('nueva')?.toString() ?? ''
    const confirmacion = datos.get('confirmacion')?.toString() ?? ''
    if (nueva.length < 12) {
      onNotify('La nueva contraseña debe tener al menos 12 caracteres.')
      return
    }
    if (nueva !== confirmacion) {
      onNotify('La confirmación no coincide con la nueva contraseña.')
      return
    }
    setGuardandoContrasena(true)
    try {
      await actualizarContrasenaAdministrador(actual, nueva)
      formulario.reset()
      setMostrarContrasena(false)
      onNotify('La contraseña se actualizó correctamente.')
    } catch (error) {
      onNotify(error instanceof Error ? error.message : 'No se pudo actualizar la contraseña.')
    } finally {
      setGuardandoContrasena(false)
    }
  }

  return <div className="admin-profile-page">
    <div className="admin-profile-heading"><div><span className="admin-profile-eyebrow">CUENTA Y ACCESO</span><h1>Perfil del administrador</h1><p>Consulta y actualiza la información de tu cuenta institucional.</p></div><button type="button" className="outline-button profile-signout" onClick={onLogout}><LogOut size={14}/> Cerrar sesión</button></div>
    <div className="admin-profile-grid">
      <div className="admin-profile-main">
        <section className="admin-profile-card profile-identity">
          <div className="profile-avatar-large">{admin.name.split(' ').slice(0, 2).map(part => part[0]).join('').toLocaleUpperCase('es')}<span className="profile-online-dot"/></div>
          <div className="profile-identity-copy"><span className="profile-role-badge"><ShieldCheck size={13}/> {admin.role}</span><h2>{admin.name}</h2><p>{admin.department} · CUCEI</p><span className="profile-email"><Mail size={14}/> {admin.email}</span></div>
          <div className="profile-member"><small>Miembro desde</small><b><CalendarDays size={14}/> Agosto de 2025</b></div>
        </section>

        <section className="admin-profile-card">
          <div className="profile-card-heading"><span className="profile-card-icon"><UserRound size={17}/></span><div><h2>Información personal</h2><p>Estos datos identifican tu cuenta dentro del panel.</p></div></div>
          <form className="profile-form" onSubmit={guardarPerfil}>
            <label>Nombre<input name="nombre" defaultValue={admin.name} required/></label>
            <label>Correo institucional<input name="correo" type="email" value={admin.email} readOnly/></label>
            <label>Teléfono de contacto<span className="profile-input-icon"><Phone size={15}/><input name="telefono" type="tel" inputMode="numeric" maxLength={10} pattern="[0-9]{10}" title="Escribe exactamente 10 dígitos, sin espacios ni letras." autoComplete="tel-national" defaultValue={(admin.phone ?? '').replace(/\D/g, '').slice(0, 10)} onChange={event => { event.currentTarget.value = event.currentTarget.value.replace(/\D/g, '').slice(0, 10) }} placeholder="10 dígitos"/></span></label>
            <label>Área de adscripción<span className="profile-input-icon"><Building2 size={15}/><input name="area" defaultValue="Administración CUCEI"/></span></label>
            <label className="profile-field-wide">Ubicación<span className="profile-input-icon"><MapPin size={15}/><input name="ubicacion" defaultValue="Guadalajara, Jalisco, México"/></span></label>
            <div className="profile-form-actions"><span>Última actualización: 24 de octubre de 2026</span><button className="primary-button" type="submit" disabled={guardando}>{guardando ? <Check size={15}/> : <Save size={15}/>} {guardando ? 'Guardando...' : 'Guardar cambios'}</button></div>
          </form>
        </section>

        <section className="admin-profile-card">
          <div className="profile-card-heading"><span className="profile-card-icon profile-card-icon-green"><KeyRound size={17}/></span><div><h2>Seguridad de la cuenta</h2><p>Actualiza tu contraseña para proteger el acceso administrativo.</p></div></div>
          <form className="profile-form profile-password-form" onSubmit={cambiarContrasena}>
            <label>Contraseña actual<input type="password" name="actual" autoComplete="current-password" required maxLength={128} placeholder="Ingresa tu contraseña actual"/></label>
            <label>Nueva contraseña<span className="profile-password-field"><input type={mostrarContrasena ? 'text' : 'password'} name="nueva" autoComplete="new-password" required minLength={12} maxLength={128} placeholder="Mínimo 12 caracteres"/><button type="button" onClick={() => setMostrarContrasena(value => !value)} aria-label={mostrarContrasena ? 'Ocultar contraseña' : 'Mostrar contraseña'}>{mostrarContrasena ? <EyeOff size={16}/> : <Eye size={16}/>}</button></span></label>
            <label className="profile-field-wide">Confirmar nueva contraseña<input type="password" name="confirmacion" autoComplete="new-password" required minLength={12} maxLength={128} placeholder="Repite la nueva contraseña"/></label>
            <div className="profile-password-hint"><LockKeyhole size={14}/> Usa al menos 12 caracteres. Se verificará tu contraseña actual antes de guardar.</div>
            <div className="profile-form-actions"><span></span><button className="outline-button" type="submit" disabled={guardandoContrasena}>{guardandoContrasena ? 'Actualizando…' : 'Actualizar contraseña'}</button></div>
          </form>
        </section>
      </div>

    </div>
  </div>
}
