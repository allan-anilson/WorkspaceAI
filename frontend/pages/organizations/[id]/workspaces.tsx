import React, {useEffect, useState} from 'react'
import {useRouter} from 'next/router'
import {getOrgWorkspaces, createWorkspace} from '../../../lib/api'
import {useAuth} from '../../../context/auth'
import Link from 'next/link'

export default function WorkspacesPage(){
  const router = useRouter()
  const {id: orgIdParam} = router.query
  const orgId = Array.isArray(orgIdParam)? orgIdParam[0] : orgIdParam
  const {token} = useAuth()
  const [wsList,setWsList] = useState<any[]>([])
  const [name,setName] = useState('')

  useEffect(()=>{
    if(!orgId || !token) { if(!token) router.push('/login'); return }
    getOrgWorkspaces(orgId as string, token).then((res:any)=> setWsList(res)).catch(()=>{})
  },[orgId,token])

  async function handleCreate(e:React.FormEvent){
    e.preventDefault()
    if(!name) return
    try{
      const added = await createWorkspace(orgId as string, {name}, token || undefined)
      setWsList(prev=>[added,...prev])
      setName('')
    }catch(e){ console.error(e) }
  }

  return (
    <main className="max-w-4xl mx-auto mt-8">
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-semibold">Workspaces</h2>
          <form onSubmit={handleCreate} className="flex gap-2">
            <input className="border rounded p-2" placeholder="Workspace name" value={name} onChange={e=>setName(e.target.value)} />
            <button className="bg-indigo-600 text-white px-3 py-2 rounded" type="submit">Create</button>
          </form>
        </div>

        <ul className="space-y-2">
          {wsList.map(w=> (
            <li key={w.id} className="p-3 border rounded hover:shadow">
              <Link className="text-indigo-600 font-medium" href={`/workspaces/${w.id}/chat`}>{w.name}</Link>
            </li>
          ))}
        </ul>
      </div>
    </main>
  )
}
