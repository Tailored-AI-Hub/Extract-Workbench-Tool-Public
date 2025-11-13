'use client'

import React, { useEffect, useState } from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { Loader2, AlertCircle } from 'lucide-react'
import { audioApi, UserRatingBreakdown } from '../../services/audioApi'

interface AudioRatingBreakdownRowProps {
  projectId: string
  audioId: string
  jobUuid: string
  token: string | null
}

export function AudioRatingBreakdownRow({ projectId, audioId, jobUuid, token }: AudioRatingBreakdownRowProps) {
  const [breakdown, setBreakdown] = useState<UserRatingBreakdown[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchBreakdown = async () => {
      if (!token) return

      try {
        setLoading(true)
        setError(null)
        const data = await audioApi.getAudioRatingBreakdown(projectId, audioId, jobUuid, token)
        setBreakdown(data)
      } catch (err) {
        console.error('Error fetching audio rating breakdown:', err)
        setError(err instanceof Error ? err.message : 'Failed to load breakdown')
      } finally {
        setLoading(false)
      }
    }

    fetchBreakdown()
  }, [projectId, audioId, jobUuid, token])

  if (loading) {
    return (
      <TableRow>
        <TableCell colSpan={7} className="bg-gray-50">
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
            <span className="text-sm text-muted-foreground">Loading user ratings...</span>
          </div>
        </TableCell>
      </TableRow>
    )
  }

  if (error) {
    return (
      <TableRow>
        <TableCell colSpan={7} className="bg-gray-50">
          <div className="flex items-center justify-center py-4 text-red-600">
            <AlertCircle className="h-4 w-4 mr-2" />
            <span className="text-sm">{error}</span>
          </div>
        </TableCell>
      </TableRow>
    )
  }

  if (breakdown.length === 0) {
    return (
      <TableRow>
        <TableCell colSpan={7} className="bg-gray-50">
          <div className="py-4 text-center text-sm text-muted-foreground">No user ratings yet</div>
        </TableCell>
      </TableRow>
    )
  }

  return (
    <TableRow>
      <TableCell colSpan={7} className="bg-gray-50 p-0">
        <div className="px-4 py-3">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">User</TableHead>
                <TableHead className="text-xs">Average Rating</TableHead>
                <TableHead className="text-xs">Segments Rated</TableHead>
                <TableHead className="text-xs">Total Ratings</TableHead>
                <TableHead className="text-xs">Last Rated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {breakdown.map((item) => (
                <TableRow key={item.user_id || 'unknown'} className="hover:bg-white/50">
                  <TableCell className="text-xs font-medium">{item.user_name || 'Unknown User'}</TableCell>
                  <TableCell className="text-xs">
                    <div className="flex items-center gap-1">
                      <span className="text-yellow-500">★</span>
                      <span>{item.average_rating.toFixed(1)}/5</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-xs">{item.pages_rated}</TableCell>
                  <TableCell className="text-xs">{item.total_ratings}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{new Date(item.latest_rated_at).toLocaleDateString()}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </TableCell>
    </TableRow>
  )
}


