import React, {createContext, useContext, useEffect, useState} from 'react'
import {me as apiMe} from '../lib/api'

type User = any

type AuthContextType = {
  token: string | null
  user: User | null
  login: (token: string)=>void
  logout: ()=>void
}

const AuthContext = createContext<AuthContextType|undefined>(undefined)

export function AuthProvider({children}:{children:React.ReactNode}){
  const [token,setToken] = useState<string | null>(typeof window !== 'undefined' ? localStorage.getItem('access_token') : null)
  const [user,setUser] = useState<User | null>(null)

  useEffect(()=>{
    if(!token){ setUser(null); return }
    let mounted = true
    apiMe(token).then((u:any)=>{ if(mounted) setUser(u) }).catch(()=>{ if(mounted) setUser(null) })
    return ()=>{ mounted=false }
  },[token])

  function login(t:string){
    setToken(t)
    if(typeof window !== 'undefined') localStorage.setItem('access_token', t)
  }
  function logout(){
    setToken(null)
    setUser(null)
    if(typeof window !== 'undefined') localStorage.removeItem('access_token')
  }

  return <AuthContext.Provider value={{token,user,login,logout}}>{children}</AuthContext.Provider>
}

export function useAuth(){
  const ctx = useContext(AuthContext)
  if(!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
