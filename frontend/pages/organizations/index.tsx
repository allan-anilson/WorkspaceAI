import React, {useEffect, useState} from 'react'
import {getOrganizations, createOrganization} from '../../lib/api'
import {useAuth} from '../../context/auth'
import Link from 'next/link'
import {useRouter} from 'next/router'

export default function OrgsPage(){
  const {token} = useAuth()
  const router = useRouter()
  const [orgs,setOrgs] = useState<any[]>([])
  const [name,setName] = useState('')

  useEffect(()=>{
    if(!token) { router.push('/login'); return }
    getOrganizations(token).then((res:any)=> setOrgs(res)).catch(()=>{})
  },[token])

  async function handleCreate(e:React.FormEvent){
    e.preventDefault()
    if(!name) return
    try{
      const added = await createOrganization({name}, token || undefined)
      setOrgs(prev=>[added,...prev])
      setName('')
    }catch(e){ console.error(e) }
  }

  return (
    <main className="max-w-4xl mx-auto mt-8">
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-semibold">Your Organizations</h2>
          <form onSubmit={handleCreate} className="flex gap-2">
            <input className="border rounded p-2" placeholder="Organization name" value={name} onChange={e=>setName(e.target.value)} />
            <button className="bg-indigo-600 text-white px-3 py-2 rounded" type="submit">Create</button>
          </form>
        </div>

        <ul className="space-y-2">
          {orgs.map(o=> (
            <li key={o.id} className="p-3 border rounded hover:shadow">
              <Link className="text-indigo-600 font-medium" href={`/organizations/${o.id}/workspaces`}>{o.name}</Link>
            </li>
          ))}
        </ul>
      </div>
    </main>
  )
}
