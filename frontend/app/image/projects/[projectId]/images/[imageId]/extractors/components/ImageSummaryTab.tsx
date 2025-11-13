'use client'

import { ImageExtractionJob } from '../../../../../../../services/imageApi'
import { ImageExtractionJobsTable } from '../../../../../../components/ImageExtractionJobsTable'
import { Card, CardContent, CardHeader, CardTitle } from '../../../../../../../components/ui/card'

type SortField = keyof ImageExtractionJob | null
type SortDirection = 'asc' | 'desc'

interface ImageSummaryTabProps {
  sortedJobs: ImageExtractionJob[]
  sortField: SortField
  sortDirection: SortDirection
  onSort: (field: keyof ImageExtractionJob) => void
  projectId: string
  imageId: string
  token: string | null
  onViewExtractor: (extractor: string) => void
  onRetryJob?: (jobUuid: string) => void
  retryingJobs?: Set<string>
}

export function ImageSummaryTab({
  sortedJobs,
  sortField,
  sortDirection,
  onSort,
  projectId,
  imageId,
  token,
  onViewExtractor,
  onRetryJob,
  retryingJobs
}: ImageSummaryTabProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-semibold">Extractor Performance</CardTitle>
      </CardHeader>
      <CardContent>
        <ImageExtractionJobsTable
          jobs={sortedJobs}
          sortField={sortField}
          sortDirection={sortDirection}
          onSort={onSort}
          onViewExtractor={onViewExtractor}
          onRetryJob={onRetryJob}
          retryingJobs={retryingJobs}
          projectId={projectId}
          imageId={imageId}
          token={token}
        />
      </CardContent>
    </Card>
  )
}

