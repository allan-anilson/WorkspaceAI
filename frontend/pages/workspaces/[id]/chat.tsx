import React, {useEffect, useState, useRef} from 'react'
import {useRouter} from 'next/router'
import {syncMessages, connectWorkspaceWs} from '../../../lib/api'
import {useAuth} from '../../../context/auth'
import type { NextPage } from 'next'
import ChatMessage from '../../../components/ChatMessage'
import WorkspaceTabs from '../../../components/WorkspaceTabs'

const ChatPage: NextPage = ()=>{
  const router = useRouter()
  const {id: workspaceIdParam} = router.query
  const workspaceId = Array.isArray(workspaceIdParam)? workspaceIdParam[0] : workspaceIdParam
  const [messages,setMessages] = useState<any[]>([])
  const [input,setInput] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const [connected,setConnected] = useState(false)
  const [typing,setTyping] = useState(false)
  const [loading,setLoading] = useState(false)
  const messagesRef = useRef<HTMLDivElement | null>(null)
  const {user} = useAuth()

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
      // handle typing events separately
      try{
        if(msg && msg.event === 'typing'){
          setTyping(true)
          // clear typing after a timeout in case no reply arrives
          setTimeout(()=> setTyping(false), 15000)
          return
        }
      }catch(_){ }

      // normal message payload
      setTyping(false)
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
        <WorkspaceTabs workspaceId={workspaceId as string} />
        <div ref={messagesRef} className="h-96 overflow-auto border rounded p-3 mb-3 bg-gray-50">
          {loading ? (
            <div>Loading...</div>
          ) : (
            messages.map((m,i)=> {
              const prev = i>0 ? messages[i-1] : null
              const showName = !prev || String(prev.sender_id) !== String(m.sender_id) || Boolean(m.is_bot)
              const senderName = m.is_bot ? 'AI Bot' : (m.sender_name || m.sender_email || 'Unknown')
              const mine = user && m.sender_id && String(m.sender_id) === String(user.id)
              return (
                <div key={m.id || i}>
                  {showName && (
                    <div className={`text-sm text-gray-600 mb-1 ${mine ? 'text-right' : ''}`}>{senderName}</div>
                  )}
                  <ChatMessage m={m} />
                </div>
              )
            })
          )}

          {typing && (
            <div className="mb-3 flex justify-start">
              <div className="bg-white text-gray-700 rounded-lg p-3 shadow max-w-[40%]">
                <div className="text-sm"><strong>AI Bot</strong></div>
                <div className="text-sm text-gray-600 mt-2">Thinking<span className="animate-pulse">...</span></div>
              </div>
            </div>
          )}
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
