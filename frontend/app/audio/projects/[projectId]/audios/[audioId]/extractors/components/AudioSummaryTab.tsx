'use client'

import { AudioExtractionJob } from '../../../../../../../services/audioApi'
import { AudioExtractionJobsTable } from '../../../../../../components/AudioExtractionJobsTable'
import { Card, CardContent, CardHeader, CardTitle } from '../../../../../../../components/ui/card'

type SortField = keyof AudioExtractionJob | null
type SortDirection = 'asc' | 'desc'

interface AudioSummaryTabProps {
  sortedJobs: AudioExtractionJob[]
  sortField: SortField
  sortDirection: SortDirection
  onSort: (field: keyof AudioExtractionJob) => void
  projectId: string
  audioId: string
  token: string | null
  onViewExtractor: (extractor: string) => void
  onRetryJob?: (jobUuid: string) => void
  retryingJobs?: Set<string>
}

export function AudioSummaryTab({
  sortedJobs,
  sortField,
  sortDirection,
  onSort,
  projectId,
  audioId,
  token,
  onViewExtractor,
  onRetryJob,
  retryingJobs
}: AudioSummaryTabProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-semibold">Extractor Performance</CardTitle>
      </CardHeader>
      <CardContent>
        <AudioExtractionJobsTable
          jobs={sortedJobs}
          sortField={sortField}
          sortDirection={sortDirection}
          onSort={onSort}
          onViewExtractor={onViewExtractor}
          onRetryJob={onRetryJob}
          retryingJobs={retryingJobs}
          projectId={projectId}
          audioId={audioId}
          token={token}
        />
      </CardContent>
    </Card>
  )
}

