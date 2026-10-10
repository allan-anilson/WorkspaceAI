import React, {useState} from 'react'
import {useRouter} from 'next/router'
import {login, ping} from '../lib/api'
import type { NextPage } from 'next'

const Login: NextPage = ()=>{
  const [email,setEmail]=useState('')
  const [password,setPassword]=useState('')
  const [error,setError]=useState<string | null>(null)
  const [pingResult,setPingResult]=useState<string | null>(null)
  const router = useRouter()

  async function handleSubmit(e: React.FormEvent){
    e.preventDefault()
    setError(null)
    try{
      const data: any = await login({email,password})
      localStorage.setItem('access_token', data.access_token)
      router.push('/')
    }catch(err: any){
      setError(err.message || 'Login failed')
    }
  }

  async function handlePing(){
    setPingResult(null)
    try{
      const res = await ping()
      setPingResult(JSON.stringify(res))
    }catch(err:any){
      setPingResult(String(err.message || err))
    }
  }

  return (
    <main className="max-w-2xl mx-auto mt-12">
      <div className="card max-w-md mx-auto">
        <h1 className="text-3xl font-bold mb-4">Sign in</h1>
        <form onSubmit={handleSubmit} className="grid gap-3">
          <input className="border rounded p-2" placeholder="Email" value={email} onChange={(e)=>setEmail(e.target.value)} />
          <input className="border rounded p-2" placeholder="Password" type="password" value={password} onChange={(e)=>setPassword(e.target.value)} />
          <div className="flex gap-3 items-center">
            <button className="bg-indigo-600 text-white px-4 py-2 rounded" type="submit">Sign in</button>
            <button type="button" onClick={handlePing} className="text-sm text-gray-600 underline">Test backend</button>
          </div>
          {error && <div className="text-red-600">{error}</div>}
          {pingResult && <pre className="text-xs text-gray-700 bg-gray-50 p-2 rounded">{pingResult}</pre>}
        </form>
      </div>
      <p className="mt-4 text-sm text-gray-600">After login, open a workspace chat at <code>/workspaces/&lt;workspace-id&gt;/chat</code>.</p>
    </main>
  )
}

export default Login
