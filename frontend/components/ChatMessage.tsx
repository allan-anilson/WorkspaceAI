import React from 'react'
import {useAuth} from '../context/auth'

export default function ChatMessage({m}:{m:any}){
  const {user} = useAuth()
  const mine = user && m.sender_id && user.id && String(m.sender_id) === String(user.id)
  return (
    <div className={`mb-3 flex ${mine ? 'justify-end' : 'justify-start'}`}>
      <div className={`${mine ? 'bg-indigo-600 text-white' : 'bg-white text-gray-900'} rounded-lg p-3 shadow max-w-[80%]`}>
        <div className="text-sm whitespace-pre-wrap">{m.content}</div>
        <div className="text-xs text-gray-400 mt-1 text-right">{m.created_at}</div>
      </div>
    </div>
  )
}
