'use client'

import React, { useState } from 'react'
import { Loader2, AlertCircle, Clock } from 'lucide-react'
import AnnotatableText from '../../components/AnnotatableText'
import { audioApi, AudioExtractionJob, AudioAnnotation, AudioSegmentContent } from '../../services/audioApi'
import { ConfirmationDialog } from '../../components/ui/confirmation-dialog'
import { Card, CardContent } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'

interface AudioChunkedContentProps {
  segments: AudioSegmentContent[]
  loading: boolean
  error: string | null
  annotations: AudioAnnotation[]
  selectedExtractor: string
  extractionJobs: AudioExtractionJob[]
  audioUuid: string
  token: string | null
  onAnnotationsChange: (annotations: AudioAnnotation[]) => void
  highlightedAnnotationId?: string | null
}

function formatTimestamp(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '--:--'
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
}

export function AudioChunkedContent({
  segments,
  loading,
  error,
  annotations,
  selectedExtractor,
  extractionJobs,
  audioUuid,
  token,
  onAnnotationsChange,
  highlightedAnnotationId
}: AudioChunkedContentProps) {
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; annotationId: string | null; annotationText: string }>({ 
    isOpen: false, 
    annotationId: null, 
    annotationText: '' 
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Loading chunked content...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-red-600">
        <AlertCircle className="h-4 w-4" />
        <span>{error}</span>
      </div>
    )
  }

  const selectedJob = extractionJobs.find(job => job.extractor === selectedExtractor)

  return (
    <>
      <div className="space-y-4">
        {segments.map((segment) => {
          const content = segment.content?.COMBINED || segment.content?.TEXT || ''
          const isEmpty = !content.trim()
          const startMs = segment.start_ms
          const endMs = segment.end_ms

          // Filter annotations for this segment
          const segmentAnnotations = annotations.filter(a => a.segment_number === segment.segment_number)
          
          // Map annotations for AnnotatableText - use stored character positions directly
          const initialAnnotations = segmentAnnotations.map(a => {
            // If we have stored character positions, use them directly (no text matching needed)
            if (a.selection_start_char != null && a.selection_end_char != null) {
              const start = Math.max(0, Math.min(a.selection_start_char, content.length))
              const end = Math.max(start, Math.min(a.selection_end_char, content.length))
              return { id: a.uuid, start, end, comment: a.comment || '' }
            }
            // Fallback for old annotations
            const idx = content.indexOf(a.text)
            const start = idx >= 0 ? idx : 0
            const end = idx >= 0 ? idx + a.text.length : a.text.length
            return { id: a.uuid, start, end, comment: a.comment || '' }
          })

          return (
            <Card key={segment.uuid} className={isEmpty ? 'opacity-60 border-dashed' : ''}>
              <CardContent className="p-4">
                <div className="flex items-start gap-3 mb-3">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground flex-shrink-0">
                    <Clock className="h-4 w-4" />
                    <span className="font-mono">
                      {formatTimestamp(startMs)} - {formatTimestamp(endMs)}
                    </span>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    Segment {segment.segment_number}
                  </Badge>
                  {isEmpty && (
                    <Badge variant="secondary" className="text-xs">
                      Empty
                    </Badge>
                  )}
                </div>
                
                {isEmpty ? (
                  <div className="text-sm text-muted-foreground italic py-4">
                    [No transcription for this time period]
                  </div>
                ) : (
                  <AnnotatableText
                    text={content}
                    initialAnnotations={initialAnnotations}
                    onCreate={async ({ start, end, comment }) => {
                      if (!audioUuid || !token || !selectedJob) return
                      
                      // Store like document annotations:
                      // - text: FULL formatted text being displayed
                      // - selectionStartChar/selectionEndChar: character positions within that text
                      const created = await audioApi.createAudioAnnotation({
                        audioId: audioUuid,
                        extractionJobUuid: selectedJob.uuid,
                        segmentNumber: segment.segment_number,
                        text: content, // Store FULL formatted text (like currentText in documents)
                        comment: comment || '',
                        selectionStartChar: start, // Character position start
                        selectionEndChar: end,     // Character position end
                      }, token)
                      
                      onAnnotationsChange([...annotations, created])
                      return { id: created.uuid }
                    }}
                    onDelete={async (id) => {
                      if (!token) return
                      const annotation = annotations.find(a => a.uuid === id)
                      if (annotation) {
                        setDeleteConfirm({ 
                          isOpen: true, 
                          annotationId: id, 
                          annotationText: annotation.text || annotation.comment || 'this annotation' 
                        })
                      }
                    }}
                    highlightedAnnotationId={highlightedAnnotationId}
                  />
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>
      
      <ConfirmationDialog
        open={deleteConfirm.isOpen}
        onOpenChange={(open) => !open && setDeleteConfirm({ isOpen: false, annotationId: null, annotationText: '' })}
        onConfirm={async () => {
          if (deleteConfirm.annotationId && token) {
            try {
              await audioApi.deleteAudioAnnotation(deleteConfirm.annotationId, token)
              onAnnotationsChange(annotations.filter(a => a.uuid !== deleteConfirm.annotationId))
            } catch {}
          }
          setDeleteConfirm({ isOpen: false, annotationId: null, annotationText: '' })
        }}
        title="Delete Annotation"
        description={`Are you sure you want to delete this annotation? This action cannot be undone.`}
        variant="destructive"
        confirmText="Delete"
        cancelText="Cancel"
      />
    </>
  )
}

