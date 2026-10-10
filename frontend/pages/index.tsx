import React, {useEffect} from 'react'
import type { NextPage } from 'next'
import {useRouter} from 'next/router'
import {useAuth} from '../context/auth'

const Home: NextPage = () => {
  const {token} = useAuth()
  const router = useRouter()
  useEffect(()=>{
    if(token) router.push('/organizations')
    else router.push('/login')
  },[token])
  return <div />
}

export default Home
