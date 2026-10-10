import Link from 'next/link'
import React from 'react'
import {useAuth} from '../context/auth'

export default function Nav(){
  const {user,logout} = useAuth()
  return (
    <nav className="bg-white border-b">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center gap-6">
            <div className="text-xl font-semibold text-indigo-600">WorkspaceAI</div>
            {user && <Link className="text-sm text-gray-600 hover:text-indigo-600" href="/organizations">Organizations</Link>}
          </div>
          <div>
            {user ? (
              <div className="flex items-center gap-4">
                <div className="text-sm text-gray-700">{user.full_name || user.email}</div>
                <button onClick={logout} className="text-sm text-red-600 hover:underline">Logout</button>
              </div>
            ) : (
              <Link className="text-sm text-indigo-600 hover:underline" href="/login">Sign in</Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
