const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1'

function buildUrl(path: string) {
  // Ensure we always call the backend origin directly using the full API_BASE
  return `${API_BASE.replace(/\/$/, '')}${path}`
}

async function request(path: string, opts: RequestInit = {}) {
  const res = await fetch(buildUrl(path), opts)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    const err: any = new Error(res.statusText || 'API error')
    err.status = res.status
    err.body = text
    throw err
  }
  const contentType = res.headers.get('content-type') || ''
  if (contentType.includes('application/json')) return res.json()
  return res.text()
}

export async function ping(){
  return request('/')
}

export async function signup({email, password, full_name}: {email:string,password:string,full_name?:string}){
  return request('/auth/signup', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({email, password, full_name})
  })
}

export async function login({email, password}:{email:string,password:string}){
  const body = new URLSearchParams()
  body.append('username', email)
  body.append('password', password)

  try{
    const res = await fetch(buildUrl('/auth/login'), {
      method: 'POST',
      headers: {'Content-Type':'application/x-www-form-urlencoded'},
      body: body.toString(),
      mode: 'cors',
    })
    if (!res.ok) {
      const txt = await res.text().catch(()=>'')
      throw new Error(txt || `Login failed (${res.status})`)
    }
    return res.json()
  }catch(err:any){
    // Surface more helpful message for network / CORS failures
    const attempted = buildUrl('/auth/login')
    throw new Error(`Network error when calling ${attempted}: ${err?.message || err}`)
  }
}

export async function me(token?: string){
  return request('/auth/me', {
    headers: {Authorization: `Bearer ${token}`}
  })
}

export async function listDocuments(workspaceId: string, token?: string){
  return request(`/workspaces/${workspaceId}/documents`, {
    headers: {Authorization: `Bearer ${token}`}
  })
}

export async function uploadDocument(workspaceId: string, file: File, token?: string){
  const fd = new FormData()
  fd.append('file', file)
  return request(`/workspaces/${workspaceId}/documents`, {
    method: 'POST',
    headers: {Authorization: `Bearer ${token}`},
    body: fd
  })
}

export async function queryRAG(workspaceId: string, query: string, token?: string){
  return request(`/workspaces/${workspaceId}/rag/query`, {
    method: 'POST',
    headers: {Authorization: `Bearer ${token}`, 'Content-Type':'application/json'},
    body: JSON.stringify({query})
  })
}

export async function syncMessages(workspaceId: string, afterSeqId = 0, limit = 50, token?: string){
  const qs = `?after_seq_id=${afterSeqId}&limit=${limit}`
  return request(`/workspaces/${workspaceId}/messages/sync${qs}`, {
    headers: {Authorization: `Bearer ${token}`}
  })
}

export function connectWorkspaceWs(
  workspaceId: string,
  token: string,
  onMessage?: (data: any) => void,
  onOpen?: () => void,
  onClose?: (ev: CloseEvent) => void,
  onError?: (ev: Event) => void,
){
  // Build a WebSocket URL from the configured backend origin so the frontend
  // connects directly to the backend (no server-to-server proxying).
  try{
    const base = new URL(API_BASE)
    base.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
    // join path segments safely: preserve any /api/v1 prefix in API_BASE
    const prefix = base.pathname.replace(/\/$/, '')
    const wsPath = `${prefix}/workspaces/${encodeURIComponent(workspaceId)}/chat/ws`
    base.pathname = wsPath
    base.search = `token=${encodeURIComponent(token)}`
    const url = base.toString()

    const ws = new WebSocket(url)
    ws.onopen = () => onOpen && onOpen()
    ws.onmessage = (evt) => {
      try { onMessage && onMessage(JSON.parse(evt.data)) } catch(e){ onMessage && onMessage(evt.data) }
    }
    ws.onclose = (e) => onClose && onClose(e)
    ws.onerror = (e) => onError && onError(e)
    return ws
  }catch(err){
    // Fallback to simple string construction if URL parsing fails
    const wsBase = API_BASE.replace(/^http/, 'ws').replace(/\/$/, '')
    const url = `${wsBase}/workspaces/${workspaceId}/chat/ws?token=${encodeURIComponent(token)}`
    const ws = new WebSocket(url)
    ws.onopen = () => onOpen && onOpen()
    ws.onmessage = (evt) => {
      try { onMessage && onMessage(JSON.parse(evt.data)) } catch(e){ onMessage && onMessage(evt.data) }
    }
    ws.onclose = (e) => onClose && onClose(e)
    ws.onerror = (e) => onError && onError(e)
    return ws
  }
}

// Organizations & Workspaces
export async function getOrganizations(token?: string){
  return request('/organizations', { headers: { Authorization: `Bearer ${token}` } })
}

export async function createOrganization(data: {name:string, slug?:string}, token?: string){
  return request('/organizations', { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type':'application/json' }, body: JSON.stringify(data) })
}

export async function getOrgWorkspaces(orgId: string, token?: string){
  return request(`/organizations/${orgId}/workspaces`, { headers: { Authorization: `Bearer ${token}` } })
}

export async function createWorkspace(orgId: string, data: {name:string, slug?:string}, token?: string){
  return request(`/organizations/${orgId}/workspaces`, { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type':'application/json' }, body: JSON.stringify(data) })
}

export default null
