import React, {useEffect, useState} from 'react'
import {useRouter} from 'next/router'
import {listDocuments, uploadDocument, queryRAG} from '../../../lib/api'
import type { NextPage } from 'next'

const DocumentsPage: NextPage = ()=>{
  const router = useRouter()
  const {id: workspaceIdParam} = router.query
  const workspaceId = Array.isArray(workspaceIdParam)? workspaceIdParam[0] : workspaceIdParam
  const [docs,setDocs] = useState<any[]>([])
  const [file,setFile] = useState<File | null>(null)
  const [query,setQuery] = useState('')
  const [answer,setAnswer] = useState<string | null>(null)

  useEffect(()=>{
    if(!workspaceId) return
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    if(!token) { router.push('/login'); return }
    listDocuments(workspaceId, token).then((res:any)=> setDocs(res)).catch(()=>{})
  },[workspaceId])

  async function handleUpload(e: React.FormEvent){
    e.preventDefault()
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    if(!file) return
    try{
      const added = await uploadDocument(workspaceId as string, file, token || undefined)
      setDocs(prev=>[added,...prev])
      setFile(null)
    }catch(e){ console.error(e) }
  }

  async function handleQuery(e: React.FormEvent){
    e.preventDefault()
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    setAnswer('Thinking...')
    try{
      const res: any = await queryRAG(workspaceId as string, query, token || undefined)
      setAnswer(res.answer || JSON.stringify(res))
    }catch(e){ setAnswer('Error') }
  }

  return (
    <main style={{padding:16}}>
      <h2>Documents: {workspaceId}</h2>
      <form onSubmit={handleUpload} style={{marginBottom:12}}>
        <input type="file" onChange={e=>setFile(e.target.files ? e.target.files[0] : null)} />
        <button type="submit">Upload</button>
      return (
        <main className="max-w-4xl mx-auto mt-8">
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">Documents: {workspaceId}</h2>
            <form onSubmit={handleUpload} className="mb-4 flex gap-2 items-center">
              <input type="file" onChange={e=>setFile(e.target.files ? e.target.files[0] : null)} />
              <button type="submit" className="bg-indigo-600 text-white px-3 py-2 rounded">Upload</button>
            </form>

            <h3 className="font-medium">Files</h3>
            <ul className="mt-2 mb-4">
              {docs.map(d=> <li key={d.id} className="py-2 border-b">{d.name} — {d.size || ''}</li>)}
            </ul>

            <h3 className="font-medium">Ask RAG</h3>
            <form onSubmit={handleQuery} className="flex gap-2">
              <input value={query} onChange={e=>setQuery(e.target.value)} className="flex-1 border rounded p-2" />
              <button type="submit" className="bg-indigo-600 text-white px-3 py-2 rounded">Ask</button>
            </form>
            {answer && <div className="mt-4 whitespace-pre-wrap">{answer}</div>}
          </div>
        </main>
      )
