import Link from 'next/link'
import {useRouter} from 'next/router'
import React from 'react'

export default function WorkspaceTabs({workspaceId}:{workspaceId?:string}){
  const router = useRouter()
  const base = `/workspaces/${workspaceId}`
  const active = (p:string)=> router.asPath?.startsWith(p)
  return (
    <div className="mb-4">
      <div className="flex gap-2">
        <Link href={`${base}/chat`} className={`px-3 py-2 rounded ${active(`${base}/chat`) ? 'bg-indigo-600 text-white' : 'bg-white border'}`}>Chat</Link>
        <Link href={`${base}/documents`} className={`px-3 py-2 rounded ${active(`${base}/documents`) ? 'bg-indigo-600 text-white' : 'bg-white border'}`}>Documents</Link>
      </div>
    </div>
  )
}
