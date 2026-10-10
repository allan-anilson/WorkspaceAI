import React, {useEffect, useState, useRef} from 'react'
import {useRouter} from 'next/router'
import {syncMessages, connectWorkspaceWs} from '../../../lib/api'
import type { NextPage } from 'next'
import ChatMessage from '../../../components/ChatMessage'

const ChatPage: NextPage = ()=>{
  const router = useRouter()
  const {id: workspaceIdParam} = router.query
  const workspaceId = Array.isArray(workspaceIdParam)? workspaceIdParam[0] : workspaceIdParam
  const [messages,setMessages] = useState<any[]>([])
  const [input,setInput] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const [connected,setConnected] = useState(false)
  const [loading,setLoading] = useState(false)
  const messagesRef = useRef<HTMLDivElement | null>(null)

  useEffect(()=>{
    if(!workspaceId) return
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    if(!token) { router.push('/login'); return }

    let mounted = true
    setLoading(true)
    syncMessages(workspaceId,0,50,token).then((res:any)=>{
      if(!mounted) return
      setMessages(res.messages || [])
      // scroll after initial load
      setTimeout(()=> messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: 'auto' }), 50)
    }).catch(()=>{}).finally(()=>setLoading(false))

    const ws = connectWorkspaceWs(workspaceId, token, (msg)=>{
      setMessages(prev => [...prev, msg])
      // auto scroll on new message
      setTimeout(()=> messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: 'smooth' }), 50)
    }, ()=>setConnected(true), ()=>setConnected(false), ()=>{})
    wsRef.current = ws
    return ()=>{ mounted=false; try{ ws.close() }catch(e){} }
  },[workspaceId])

  function send(){
    if(!wsRef.current || wsRef.current.readyState!==1) return
    if(!input.trim()) return
    wsRef.current.send(input)
    setInput('')
  }

  return (
    <main className="max-w-4xl mx-auto mt-8">
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Workspace Chat: {workspaceId}</h2>
        <div ref={messagesRef} className="h-96 overflow-auto border rounded p-3 mb-3 bg-gray-50">
          {loading ? <div>Loading...</div> : messages.map((m,i)=> (
            <ChatMessage key={m.id || i} m={m} />
          ))}
        </div>

        <div className="flex gap-2">
          <input value={input} onChange={e=>setInput(e.target.value)} className="flex-1 border rounded p-2" onKeyDown={e=>{ if(e.key==='Enter'){ e.preventDefault(); send() } }} />
          <button onClick={send} disabled={!connected} className="bg-indigo-600 text-white px-4 py-2 rounded disabled:opacity-50">Send</button>
        </div>
        <div className="mt-2 text-sm text-gray-600">WebSocket: {connected ? 'connected' : 'disconnected'}</div>
      </div>
    </main>
  )
}

export default ChatPage
