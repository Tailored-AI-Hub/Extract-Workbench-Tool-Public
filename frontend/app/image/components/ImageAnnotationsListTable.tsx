'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { Input } from '../../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Loader2, AlertCircle, Search, Image as ImageIcon } from 'lucide-react'
import { imageApi, ImageExtractionJob, ImageAnnotation } from '../../services/imageApi'

interface ImageAnnotationsListTableProps {
  projectId: string
  imageId: string
  token: string | null
  extractionJobs: ImageExtractionJob[]
  onAnnotationClick: (extractorUuid: string, annotationUuid: string) => void
}

// Helper to find extractor name from job UUID
function findExtractorName(jobUuid: string, jobs: ImageExtractionJob[]): string {
  const job = jobs.find(j => j.uuid === jobUuid)
  return job?.extractor_display_name || job?.extractor || jobUuid
}

function extractSelectedText(annotation: ImageAnnotation): string {
  const source = annotation.text || ''
  if (!source) return ''

  if (annotation.selection_start_char != null && annotation.selection_end_char != null) {
    const start = Math.max(0, Math.min(annotation.selection_start_char, source.length))
    const end = Math.max(start, Math.min(annotation.selection_end_char, source.length))
    return source.slice(start, end).trim() || source.slice(start, end)
  }

  return source
}

export function ImageAnnotationsListTable({
  projectId,
  imageId,
  token,
  extractionJobs,
  onAnnotationClick,
}: ImageAnnotationsListTableProps) {
  const [annotations, setAnnotations] = useState<ImageAnnotation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Filter state
  const [selectedExtractor, setSelectedExtractor] = useState<string>('all')
  const [searchText, setSearchText] = useState<string>('')

  useEffect(() => {
    const fetchAnnotations = async () => {
      if (!token) return
      
      try {
        setLoading(true)
        setError(null)
        
        const extractorUuid = selectedExtractor !== 'all' ? selectedExtractor : undefined
        const data = await imageApi.getImageAnnotations(imageId, token, extractorUuid)
        
        setAnnotations(data)
      } catch (err) {
        console.error('Error fetching annotations list:', err)
        setError(err instanceof Error ? err.message : 'Failed to load annotations')
      } finally {
        setLoading(false)
      }
    }

    fetchAnnotations()
  }, [imageId, token, selectedExtractor])

  const filteredAnnotations = useMemo(() => {
    if (!searchText.trim()) return annotations
    const query = searchText.toLowerCase()
    return annotations.filter(annotation => {
      const selected = extractSelectedText(annotation).toLowerCase()
      const comment = annotation.comment?.toLowerCase() || ''
      const fullText = annotation.text?.toLowerCase() || ''
      return selected.includes(query) || comment.includes(query) || fullText.includes(query)
    })
  }, [annotations, searchText])

  const truncateText = (text: string, maxLength: number) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  const successfulJobs = extractionJobs.filter(job => job.status === 'Success')

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Loading annotations...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12 text-red-600">
        <AlertCircle className="h-6 w-6 mr-2" />
        <span>{error}</span>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4 items-center">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search in text or comments..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        <div className="w-64">
          <Select value={selectedExtractor} onValueChange={setSelectedExtractor}>
            <SelectTrigger>
              <SelectValue placeholder="Filter by extractor" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Extractors</SelectItem>
              {successfulJobs.map(job => (
                <SelectItem key={job.uuid} value={job.uuid}>
                  {job.extractor}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Table */}
      {filteredAnnotations.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <ImageIcon className="h-16 w-16 mb-4 opacity-50" />
          <h3 className="text-lg font-semibold mb-2">No annotations found</h3>
          <p className="text-sm">
            {searchText || selectedExtractor !== 'all' 
              ? 'Try adjusting your filters' 
              : 'Start annotating text in the Annotation tab'}
          </p>
        </div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-32">Extractor</TableHead>
                <TableHead>Selected Text</TableHead>
                <TableHead>Comment</TableHead>
                <TableHead className="w-32">User</TableHead>
                <TableHead className="w-32">Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAnnotations.map((annotation) => {
                const extractorName = findExtractorName(annotation.extraction_job_uuid, extractionJobs)
                const selectedText = extractSelectedText(annotation)
                
                return (
                  <TableRow
                    key={annotation.uuid}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => onAnnotationClick(annotation.extraction_job_uuid, annotation.uuid)}
                  >
                    <TableCell className="font-medium">{extractorName}</TableCell>
                    <TableCell className="max-w-md">
                      <div className="text-sm" title={selectedText}>
                        {truncateText(selectedText, 100)}
                      </div>
                    </TableCell>
                    <TableCell className="max-w-xs">
                      <div className="text-sm text-muted-foreground" title={annotation.comment}>
                        {annotation.comment ? truncateText(annotation.comment, 80) : '-'}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {annotation.user_name || 'Unknown'}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(annotation.created_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
      
      {filteredAnnotations.length > 0 && (
        <div className="text-sm text-muted-foreground text-center">
          Showing {filteredAnnotations.length} annotation{filteredAnnotations.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  )
}

