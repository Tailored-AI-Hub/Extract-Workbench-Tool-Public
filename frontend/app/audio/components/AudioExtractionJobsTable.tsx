'use client'

import React, { useState } from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { Badge } from '../../components/ui/badge'
import { ArrowUpDown, ArrowUp, ArrowDown, ExternalLink, RotateCcw, ChevronRight, ChevronDown, Loader2 } from 'lucide-react'
import { AudioExtractionJob } from '../../services/audioApi'
import { AudioRatingBreakdownRow } from './AudioRatingBreakdownRow'

type SortField = keyof AudioExtractionJob | null
type SortDirection = 'asc' | 'desc'

interface AudioExtractionJobsTableProps {
  jobs: AudioExtractionJob[]
  sortField: SortField
  sortDirection: SortDirection
  onSort: (field: keyof AudioExtractionJob) => void
  onViewExtractor: (extractor: string) => void
  onRetryJob?: (jobUuid: string) => void
  retryingJobs?: Set<string>
  projectId?: string
  audioId?: string
  token?: string | null
}

export function AudioExtractionJobsTable({ jobs, sortField, sortDirection, onSort, onViewExtractor, onRetryJob, retryingJobs = new Set(), projectId, audioId, token }: AudioExtractionJobsTableProps) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  const toggleRow = (jobUuid: string) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(jobUuid)) {
      newExpanded.delete(jobUuid)
    } else {
      newExpanded.add(jobUuid)
    }
    setExpandedRows(newExpanded)
  }

  const renderSortIcon = (field: keyof AudioExtractionJob) =>
    sortField === field ? (sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />) : <ArrowUpDown className="h-4 w-4 opacity-50" />

  const SortableHead = ({ field, label }: { field: keyof AudioExtractionJob; label: string }) => (
    <TableHead className="cursor-pointer hover:bg-gray-50 select-none" onClick={() => onSort(field)}>
      <div className="flex items-center gap-1">
        <span>{label}</span>
        {renderSortIcon(field)}
      </div>
    </TableHead>
  )

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <SortableHead field="extractor" label="Extractor" />
          <SortableHead field="status" label="Status" />
          <SortableHead field="latency_ms" label="Latency (s)" />
          <SortableHead field="cost" label="Cost ($)" />
          <TableHead className="cursor-pointer" onClick={() => onSort('total_rating')}>
            <div className="flex items-center gap-1">
              Average Rating
              {renderSortIcon('total_rating')}
            </div>
          </TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {jobs.length === 0 ? (
          <TableRow>
            <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
              <div className="flex flex-col items-center gap-2">
                <RotateCcw className="h-12 w-12 text-muted-foreground" />
                <h3 className="text-lg font-semibold">No extraction jobs found</h3>
                <p className="text-sm">Jobs will appear once processing starts.</p>
              </div>
            </TableCell>
          </TableRow>
        ) : (
          jobs.map(job => {
            const hasRating = job.total_rating && job.total_feedback_count > 0
            const isExpanded = expandedRows.has(job.uuid)
            
            return (
              <React.Fragment key={job.uuid}>
                <TableRow className="hover:bg-muted/50">
                  <TableCell className="font-medium">{job.extractor_display_name}</TableCell>
                  <TableCell><Badge variant={job.status === 'Success' ? 'default' : job.status === 'Failure' ? 'destructive' : 'secondary'}>{job.status}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">{(job.latency_ms ?? 0) / 1000}s</TableCell>
                  <TableCell className="text-muted-foreground">{(job.cost ?? 0).toFixed(4)}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {hasRating ? (
                      <button
                        onClick={() => toggleRow(job.uuid)}
                        className="flex items-center gap-1 hover:text-foreground"
                        title={isExpanded ? 'Hide breakdown' : 'Show breakdown'}
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-3 w-3" />
                        ) : (
                          <ChevronRight className="h-3 w-3" />
                        )}
                        <span className="text-yellow-500">★</span>
                        <span>{job.total_rating}/5</span>
                        <span className="text-muted-foreground text-xs">({job.total_feedback_count})</span>
                      </button>
                    ) : (
                      "-"
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      {job.status === 'Success' && (
                        <button className="text-muted-foreground hover:text-foreground" title="View extractor" onClick={() => onViewExtractor(job.extractor)}>
                          <ExternalLink className="h-4 w-4" />
                        </button>
                      )}
                      {(job.status === 'Failure' || job.status === 'Failed') && onRetryJob && (
                        <button
                          aria-label="Retry job"
                          title="Retry job"
                          disabled={retryingJobs.has(job.uuid)}
                          onClick={() => onRetryJob(job.uuid)}
                          className="text-muted-foreground hover:text-foreground disabled:opacity-50 disabled:cursor-not-allowed disabled:text-gray-400"
                        >
                          {retryingJobs.has(job.uuid) ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <RotateCcw className="h-4 w-4" />
                          )}
                        </button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
                {isExpanded && projectId && audioId && (
                  <AudioRatingBreakdownRow
                    projectId={projectId}
                    audioId={audioId}
                    jobUuid={job.uuid}
                    token={token ?? null}
                  />
                )}
              </React.Fragment>
            )
          })
        )}
      </TableBody>
    </Table>
  )
}


