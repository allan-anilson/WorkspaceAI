import React from 'react'
import Nav from './Nav'
import Sidebar from './Sidebar'

export default function Layout({children}:{children:React.ReactNode}){
  return (
    <div className="min-h-screen flex flex-col">
      <Nav />
      <div className="flex flex-1">
        <Sidebar />
        <div className="flex-1 bg-gray-50 p-6">
          {children}
        </div>
      </div>
    </div>
  )
}
