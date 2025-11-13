'use client'

import React from 'react'
import AnnotatableText from '../../components/AnnotatableText'

interface FormattedRawResultProps {
  data: any
  extractor: string
  annotations?: Array<{ id?: string; start?: number; end?: number; comment?: string; text?: string; selection_start_char?: number; selection_end_char?: number; uuid?: string; segment_number?: number; extraction_job_uuid?: string }>
  onCreate?: (a: { start: number; end: number; comment: string; formattedText: string }) => Promise<{ id?: string } | void> | { id?: string } | void
  onDelete?: (id: string) => Promise<void> | void
  currentSegment?: number
  extractionJobUuid?: string
  highlightedAnnotationId?: string | null
}

export function FormattedRawResult({ 
  data, 
  extractor, 
  annotations = [],
  onCreate,
  onDelete,
  currentSegment,
  extractionJobUuid,
  highlightedAnnotationId
}: FormattedRawResultProps) {
  
  // Map external annotations to positions - use stored character positions directly
  const mapAnnotationsToFormattedText = (formattedText: string, externalAnnotations: Array<{ id?: string; start?: number; end?: number; comment?: string; text?: string; selection_start_char?: number; selection_end_char?: number; uuid?: string; segment_number?: number; extraction_job_uuid?: string }>): Array<{ id?: string; start: number; end: number; comment: string }> => {
    return externalAnnotations.map(anno => {
      const cleanComment = (anno.comment || '').replace(/\s*\[POS:[^\]]*\]/g, '').trim()
      const annoId = anno.id || anno.uuid || ''
      
      // If we have stored character positions, use them directly (no text matching needed)
      if (anno.selection_start_char != null && anno.selection_end_char != null) {
        const start = Math.max(0, Math.min(anno.selection_start_char, formattedText.length))
        const end = Math.max(start, Math.min(anno.selection_end_char, formattedText.length))
        return { id: annoId, start, end, comment: cleanComment }
      }
      
      // Fallback for pre-mapped annotations (already have start/end)
      if (anno.start != null && anno.end != null) {
        const start = Math.max(0, Math.min(anno.start, formattedText.length))
        const end = Math.max(start, Math.min(anno.end, formattedText.length))
        return { id: annoId, start, end, comment: cleanComment }
      }
      
      // Fallback for old annotations without selection positions
      console.warn('[FormattedRawResult] Old annotation format (no selection positions):', annoId)
      return { id: annoId, start: 0, end: 0, comment: cleanComment }
    })
  }
  
  const formatContent = (): string => {
    if (!data) return ''

    if (extractor === 'assemblyai') {
      return formatAssemblyAI(data)
    } else if (extractor === 'aws-transcribe') {
      return formatAWSTranscribe(data)
    } else if (extractor === 'whisper-openai') {
      return formatWhisper(data)
    }
    
    return JSON.stringify(data, null, 2)
  }

  const formatAssemblyAI = (data: any): string => {
    let result = ''
    
    // Add text
    if (data.text) {
      result += `Text: ${data.text}\n\n`
    }
    
    // Add items (previously words)
    if (data.items && Array.isArray(data.items) && data.items.length > 0) {
      result += '"items": [\n'
      data.items.forEach((item: any, index: number) => {
        result += '    {\n'
        // Escape quotes in text
        const escapedItemText = (item.text || '').replace(/"/g, '\\"')
        result += `        "text": "${escapedItemText}",\n`
        result += `        "start": ${item.start !== undefined ? item.start : 'null'},\n`
        result += `        "end": ${item.end !== undefined ? item.end : 'null'},\n`
        result += `        "confidence": ${item.confidence !== undefined ? item.confidence : 'null'}\n`
        result += '    }'
        if (index < data.items.length - 1) {
          result += ','
        }
        result += '\n'
      })
      result += ']'
    }
    
    return result
  }

  const formatAWSTranscribe = (data: any): string => {
    let result = ''
    
    const results = data.results || {}
    
    // Add text from transcript segments
    if (results.text && Array.isArray(results.text)) {
      const transcriptText = results.text
        .map((transcript: any) => transcript.transcript || '')
        .join(' ')
        .trim()
      if (transcriptText) {
        result += `Text: ${transcriptText}\n\n`
      }
    }
    
    // Add items - filter to only pronunciation items
    if (results.items && Array.isArray(results.items)) {
      // Filter pronunciation items first
      const pronunciationItems = results.items.filter((item: any) => 
        item.type === 'pronunciation' && 
        item.alternatives && 
        Array.isArray(item.alternatives) && 
        item.alternatives.length > 0
      )
      
      if (pronunciationItems.length > 0) {
        result += '"items": [\n'
        pronunciationItems.forEach((item: any, index: number) => {
          const alt = item.alternatives[0] // Use first alternative
          result += '    {\n'
          // Escape quotes in text
          const escapedText = (alt.text || '').replace(/"/g, '\\"')
          result += `        "text": "${escapedText}",\n`
          // Convert start/end to string format (they're already in seconds as strings from AWS)
          const startTime = item.start !== undefined ? (typeof item.start === 'string' ? item.start : String(item.start)) : 'null'
          const endTime = item.end !== undefined ? (typeof item.end === 'string' ? item.end : String(item.end)) : 'null'
          result += `        "start": "${startTime}",\n`
          result += `        "end": "${endTime}",\n`
          const confidence = alt.confidence !== undefined ? (typeof alt.confidence === 'string' ? alt.confidence : String(alt.confidence)) : 'null'
          result += `        "confidence": "${confidence}"\n`
          result += '    }'
          if (index < pronunciationItems.length - 1) {
            result += ','
          }
          result += '\n'
        })
        result += ']'
      }
    }
    
    return result
  }

  const formatWhisper = (data: any): string => {
    let result = ''
    
    // If data is an array of segments
    if (Array.isArray(data)) {
      // First, combine all text from segments (like AWS and Assembly)
      const combinedText = data
        .map((seg: any) => {
          const content = seg.content || {}
          return content.COMBINED || content.TEXT || content.text || ''
        })
        .filter((text: string) => text.trim())
        .join(' ')
        .trim()
      
      // Add combined text at the top (like AWS and Assembly)
      if (combinedText) {
        result += `Text: ${combinedText}\n\n`
      }
      
      // Extract items from segments - need to break down segments into word-level items
      const items: any[] = []
      
      data.forEach((seg: any) => {
        const content = seg.content || {}
        const metadata = seg.metadata || {}
        
        // Whisper now stores text in content.COMBINED, content.TEXT, or content.text
        const text = content.COMBINED || content.TEXT || content.text || ''
        
        // Skip empty segments
        if (!text.trim() && !metadata.is_empty) return
        
        // Get start and end from top-level (API returns start/end for whisper, not start_ms/end_ms)
        // Also check for start_ms/end_ms as fallback
        const startMs = seg.start !== undefined ? seg.start : 
                       (seg.start_ms !== undefined ? seg.start_ms : 
                       (metadata.start_ms !== undefined ? metadata.start_ms : null))
        const endMs = seg.end !== undefined ? seg.end :
                     (seg.end_ms !== undefined ? seg.end_ms :
                     (metadata.end_ms !== undefined ? metadata.end_ms : null))
        
        // If we have timestamps, split into word-level items
        if (startMs !== null && endMs !== null) {
          // Split text into words and create items for each word
          // For simplicity, we'll distribute time evenly across words
          const words = text.trim().split(/\s+/).filter((w: string) => w.length > 0)
          if (words.length > 0) {
            const duration = (endMs - startMs) / words.length
            words.forEach((word: string, wordIndex: number) => {
              const wordStart = (startMs + wordIndex * duration) / 1000
              const wordEnd = (startMs + (wordIndex + 1) * duration) / 1000
              items.push({
                text: word,
                start: wordStart.toFixed(3),
                end: wordEnd.toFixed(3)
              })
            })
          }
        } else if (text.trim()) {
          // If we have text but no timestamps, create a single item with placeholder timestamps
          items.push({
            text: text.trim(),
            start: "0.000",
            end: "0.000"
          })
        }
      })
      
      // Format output
      if (items.length > 0) {
        result += '"items": [\n'
        items.forEach((item: any, index: number) => {
          result += '    {\n'
          // Escape quotes in text
          const escapedText = (item.text || '').replace(/"/g, '\\"')
          result += `        "text": "${escapedText}",\n`
          result += `        "start": "${item.start}",\n`
          result += `        "end": "${item.end}"\n`
          result += '    }'
          if (index < items.length - 1) {
            result += ','
          }
          result += '\n'
        })
        result += ']'
      }
    } else if (data.segments && Array.isArray(data.segments)) {
      // Handle if data has a segments property
      return formatWhisper(data.segments)
    } else if (data.text) {
      // Handle simple text format - create a single item
      result += `Text: ${data.text}\n\n`
      result += '"items": [\n'
      result += '    {\n'
      const escapedText = (data.text || '').replace(/"/g, '\\"')
      result += `        "text": "${escapedText}",\n`
      result += '        "start": "0.000",\n'
      result += '        "end": "0.000"\n'
      result += '    }\n'
      result += ']'
    }
    
    return result
  }

  const formattedText = formatContent()
  
  // Filter annotations for current segment/job (same as document filters by page/job)
  const filteredAnnotations = annotations.filter(a => {
    // For whisper, filter by job UUID only
    if (extractor === 'whisper-openai') {
      return !extractionJobUuid || a.extraction_job_uuid === extractionJobUuid
    }
    // For others, filter by segment and job
    return (!currentSegment || a.segment_number === currentSegment) && 
           (!extractionJobUuid || a.extraction_job_uuid === extractionJobUuid)
  })
  
  // Map annotations to this component's formatted text
  const mappedAnnotations = mapAnnotationsToFormattedText(formattedText, filteredAnnotations)

  // Wrap onCreate to inject the correct formatted text for position calculation
  const wrappedOnCreate = onCreate ? async (args: { start: number; end: number; comment: string }) => {
    // Pass the formattedText so parent uses the SAME text for extracting selection
    return onCreate({ ...args, formattedText })
  } : undefined

  return (
    <div className="w-full h-full p-4">
      <AnnotatableText
        text={formattedText}
        className="font-mono text-sm whitespace-pre-wrap"
        initialAnnotations={mappedAnnotations}
        onCreate={wrappedOnCreate}
        onDelete={onDelete}
        highlightedAnnotationId={highlightedAnnotationId}
      />
    </div>
  )
}

