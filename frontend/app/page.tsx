'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import ProtectedRoute from './components/ProtectedRoute'

function HomePage() {
  const router = useRouter()
  
  useEffect(() => {
    router.replace('/pdf')
  }, [router])

  return (
    <ProtectedRoute>
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    </ProtectedRoute>
  )
}

export default HomePage
