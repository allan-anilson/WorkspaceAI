import React, {useEffect, useState} from 'react'
import Link from 'next/link'
import {useAuth} from '../context/auth'
import {getOrganizations} from '../lib/api'

export default function Sidebar(){
  const {token} = useAuth()
  const [orgs,setOrgs] = useState<any[]>([])

  useEffect(()=>{
    if(!token) return
    let mounted = true
    getOrganizations(token).then((res:any)=>{ if(mounted) setOrgs(res) }).catch(()=>{})
    return ()=>{ mounted=false }
  },[token])

  return (
    <aside className="w-64 bg-white border-r p-4 hidden md:block">
      <div className="text-sm text-gray-500 mb-3">Organizations</div>
      <ul className="space-y-2">
        {orgs.length===0 && <li className="text-xs text-gray-400">No organizations</li>}
        {orgs.map(o=> (
          <li key={o.id}>
            <Link href={`/organizations/${o.id}/workspaces`} className="block p-2 rounded hover:bg-gray-50 text-gray-800">{o.name}</Link>
          </li>
        ))}
      </ul>
    </aside>
  )
}
