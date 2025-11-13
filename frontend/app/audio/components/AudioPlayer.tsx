'use client'

import { useEffect, useRef, useState } from 'react'

interface AudioPlayerProps {
  src: string
  token: string | null
  className?: string
}

export function AudioPlayer({ src, token, className }: AudioPlayerProps) {
  const [audioBlob, setAudioBlob] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    if (!src || !token) return

    const fetchAudio = async () => {
      try {
        setLoading(true)
        const response = await fetch(src, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })

        if (!response.ok) {
          throw new Error('Failed to load audio')
        }

        const blob = await response.blob()
        const audioUrl = URL.createObjectURL(blob)
        setAudioBlob(audioUrl)
      } catch (error) {
        console.error('Error loading audio:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchAudio()

    // Cleanup: revoke the blob URL when component unmounts or src/token changes
    return () => {
      setAudioBlob((prevBlob) => {
        if (prevBlob) {
          URL.revokeObjectURL(prevBlob)
        }
        return null
      })
    }
  }, [src, token])

  if (loading) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="w-80 h-10 bg-gray-200 rounded flex items-center justify-center">
          <span className="text-sm text-gray-600">Loading audio...</span>
        </div>
      </div>
    )
  }

  if (!audioBlob) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="w-80 h-10 bg-red-100 rounded flex items-center justify-center">
          <span className="text-sm text-red-600">Failed to load audio</span>
        </div>
      </div>
    )
  }

  return (
    <audio
      ref={audioRef}
      src={audioBlob}
      controls
      className={className}
      preload="metadata"
    >
      Your browser does not support the audio tag.
    </audio>
  )
}

