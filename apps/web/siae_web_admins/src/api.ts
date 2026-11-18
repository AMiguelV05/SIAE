import type { AccessRequest, ManagedUser } from './datosCompartidos'

export type AdminAutenticado = {
  id: string
  name: string
  email: string
  phone?: string | null
  department: string
  role: ManagedUser['role']
}

type RespuestaError = { error?: string; detail?: string | { msg?: string }[] }

async function solicitud<T>(url: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    const headers = new Headers(init.headers)
    if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
    response = await fetch(url, {
      ...init,
      credentials: 'same-origin',
      headers,
    })
  } catch {
    throw new Error('No se pudo conectar con el servidor. Comprueba que el backend esté iniciado.')
  }
  const result = await response.json().catch(() => ({})) as RespuestaError & T
  if (!response.ok) {
    const detail = Array.isArray(result.detail) ? result.detail.map(item => item.msg).filter(Boolean).join(' ') : result.detail
    const message = response.status >= 500 ? 'El servidor no está disponible. Comprueba que el backend esté iniciado.' : result.error || detail || 'No se pudo completar la solicitud.'
    throw new Error(message)
  }
  return result
}

export async function obtenerSesion(): Promise<AdminAutenticado | null> {
  const response = await solicitud<{ user: AdminAutenticado | null }>('/api/auth/session')
  return response.user
}

export async function iniciarSesion(email: string, password: string): Promise<AdminAutenticado> {
  const response = await solicitud<{ user: AdminAutenticado }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
  return response.user
}

export async function cerrarSesion(): Promise<void> {
  await solicitud<{ ok: boolean }>('/api/auth/logout', { method: 'POST', body: '{}' })
}

export async function actualizarNombreAdministrador(name: string, phone?: string | null): Promise<AdminAutenticado> {
  const response = await solicitud<{ user: AdminAutenticado }>('/api/auth/profile', {
    method: 'PATCH',
    body: JSON.stringify({ name, phone }),
  })
  return response.user
}

export async function actualizarContrasenaAdministrador(currentPassword: string, newPassword: string): Promise<void> {
  await solicitud<{ ok: boolean }>('/api/auth/password', {
    method: 'PATCH',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  })
}

export async function solicitarAcceso(data: {
  name: string
  email: string
  phone: string
  department: string
  reason: string
  password: string
}): Promise<AccessRequest> {
  const response = await solicitud<{ request: AccessRequest }>('/api/access-requests', { method: 'POST', body: JSON.stringify(data) })
  return response.request
}

export async function obtenerSolicitudesAcceso(): Promise<AccessRequest[]> {
  const response = await solicitud<{ requests: AccessRequest[] }>('/api/access-requests')
  return response.requests
}

export async function obtenerUsuarios(): Promise<ManagedUser[]> {
  const response = await solicitud<{ users: ManagedUser[] }>('/api/users')
  return response.users
}

export async function revisarSolicitudAcceso(id: string, decision: 'approve' | 'reject', role?: 'Coordinador'): Promise<{ request: AccessRequest; user?: AdminAutenticado }> {
  return solicitud<{ request: AccessRequest; user?: AdminAutenticado }>(`/api/access-requests/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify({ decision, role }),
  })
}
