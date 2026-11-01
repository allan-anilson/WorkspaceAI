import React, {useEffect, useState, useRef} from 'react'
import {useRouter} from 'next/router'
import {downloadDocument, listDocuments, queryRAG, uploadDocument} from '../../../lib/api'
import WorkspaceTabs from '../../../components/WorkspaceTabs'
import type { NextPage } from 'next'

const DocumentsPage: NextPage = ()=>{
  const router = useRouter()
  const {id: workspaceIdParam} = router.query
  const workspaceId = Array.isArray(workspaceIdParam)? workspaceIdParam[0] : workspaceIdParam
  const [docs,setDocs] = useState<any[]>([])
  const [file,setFile] = useState<File | null>(null)
  const [query,setQuery] = useState('')
  const [answer,setAnswer] = useState<string | null>(null)
  const [uploadError,setUploadError] = useState<string | null>(null)
  const [isUploading,setIsUploading] = useState(false)

  const refreshDocuments = async () => {
    if(!workspaceId) return
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    if(!token) { router.push('/login'); return }
    try {
      const res:any = await listDocuments(workspaceId, token)
      setDocs(res)
    } catch (err) {
      console.error('Failed to list documents', err)
    }
  }

  useEffect(()=>{
    refreshDocuments()
  },[workspaceId])

  const hasPendingDocuments = docs.some((doc) => {
    const status = String(doc.status || '').toLowerCase()
    return status === 'pending' || status === 'processing'
  })

  useEffect(()=>{
    if(!workspaceId || !hasPendingDocuments) return
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    if(!token) return

    const interval = setInterval(() => {
      refreshDocuments()
    }, 5000)

    return () => clearInterval(interval)
  },[workspaceId, hasPendingDocuments])

  const fileInputRef = useRef<HTMLInputElement | null>(null)

  async function handleUpload(e: React.FormEvent){
    e.preventDefault()
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    if(!file || !workspaceId) return

    setUploadError(null)
    setIsUploading(true)

    try{
      const added = await uploadDocument(workspaceId, file, token || undefined)
      setDocs(prev => [added, ...prev.filter((doc) => doc.id !== added?.id)])
      setFile(null)
      try{ if(fileInputRef.current) fileInputRef.current.value = '' }catch(_){/* ignore */}
      await refreshDocuments()
    }catch(e:any){
      console.error(e)
      setUploadError(e?.message || 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  async function handleDownload(documentId: string) {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    try {
      await downloadDocument(workspaceId as string, documentId, token || undefined)
    } catch (e:any) {
      console.error(e)
      setUploadError(e?.message || 'Download failed')
    }
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
    <main className="max-w-4xl mx-auto mt-8">
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Documents: {workspaceId}</h2>
        <WorkspaceTabs workspaceId={workspaceId as string} />
        <form onSubmit={handleUpload} className="mb-4 flex gap-2 items-center">
          <input ref={fileInputRef} type="file" onChange={e=>setFile(e.target.files ? e.target.files[0] : null)} />
          <button type="submit" disabled={isUploading || !file} className="bg-indigo-600 text-white px-3 py-2 rounded disabled:opacity-60">
            {isUploading ? 'Uploading...' : 'Upload'}
          </button>
        </form>
        {uploadError && <div className="mb-4 text-sm text-red-600">{uploadError}</div>}

        <h3 className="font-medium">Files</h3>
        <ul className="mt-2 mb-4">
          {docs.map(d=> {
            const status = String(d.status || 'pending').toLowerCase()
            const isReady = status === 'completed'
            return (
              <li key={d.id} className="py-2 border-b flex items-center justify-between gap-4">
                <div>
                  <div className="font-medium">{d.filename ?? d.name ?? '—'}</div>
                  <div className="text-sm text-gray-500">
                    {(d.file_size_bytes ?? d.size) ? `${(d.file_size_bytes ?? d.size)} bytes` : ''}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    status === 'completed' ? 'bg-green-100 text-green-700' :
                    status === 'failed' ? 'bg-red-100 text-red-700' :
                    'bg-yellow-100 text-yellow-700'
                  }`}>
                    {status}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleDownload(d.id)}
                    disabled={!isReady}
                    className="bg-slate-100 text-slate-700 px-2 py-1 rounded disabled:opacity-40"
                  >
                    Download
                  </button>
                </div>
              </li>
            )
          })}
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
}

export default DocumentsPage
