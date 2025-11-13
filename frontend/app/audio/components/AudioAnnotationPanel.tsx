'use client'

import React, { useState } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'
import AnnotatableText from '../../components/AnnotatableText'
import { audioApi, AudioExtractionJob, AudioAnnotation, AudioSegmentContent } from '../../services/audioApi'
import { ConfirmationDialog } from '../../components/ui/confirmation-dialog'

interface AudioAnnotationPanelProps {
  content: string
  loading: boolean
  error: string | null
  annotations: AudioAnnotation[]
  selectedExtractor: string
  extractionJobs: AudioExtractionJob[]
  currentSegment: number
  audioUuid: string
  token: string | null
  onAnnotationsChange: (annotations: AudioAnnotation[]) => void
}

export function AudioAnnotationPanel({
  content,
  loading,
  error,
  annotations,
  selectedExtractor,
  extractionJobs,
  currentSegment,
  audioUuid,
  token,
  onAnnotationsChange
}: AudioAnnotationPanelProps) {
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
          <span>Loading segment content...</span>
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

  const currentJob = extractionJobs.find(job => job.extractor === selectedExtractor)
  
  // Filter and map annotations for the current segment - use stored character positions directly
  const initialAnnotations = annotations
    .filter(a => a.segment_number === currentSegment)
    .map(a => {
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
    <>
      <AnnotatableText
        text={content}
        initialAnnotations={initialAnnotations}
        onCreate={async ({ start, end, comment }) => {
          if (!audioUuid || !token) return
          const selectedJob = extractionJobs.find(job => job.extractor === selectedExtractor)
          if (!selectedJob) return
          
          // Store like document annotations:
          // - text: FULL formatted text being displayed
          // - selectionStartChar/selectionEndChar: character positions within that text
          const created = await audioApi.createAudioAnnotation({
            audioId: audioUuid,
            extractionJobUuid: selectedJob.uuid,
            segmentNumber: currentSegment,
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
          // Find the annotation to show in confirmation dialog
          const annotation = annotations.find(a => a.uuid === id)
          if (annotation) {
            setDeleteConfirm({ 
              isOpen: true, 
              annotationId: id, 
              annotationText: annotation.text || annotation.comment || 'this annotation' 
            })
          }
        }}
      />
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


