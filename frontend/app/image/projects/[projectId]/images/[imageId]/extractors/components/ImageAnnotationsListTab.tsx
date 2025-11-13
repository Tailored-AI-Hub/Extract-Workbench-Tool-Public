'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../../../../../../../components/ui/card'
import { AlertCircle } from 'lucide-react'
import { ImageExtractionJob } from '../../../../../../../services/imageApi'
import { ImageAnnotationsListTable } from '../../../../../../components/ImageAnnotationsListTable'

interface ImageAnnotationsListTabProps {
  hasSuccessfulExtractors: boolean
  projectId: string
  imageId: string
  token: string | null
  jobs: ImageExtractionJob[]
  onAnnotationClick: (extractorUuid: string, annotationUuid: string) => void
}

export function ImageAnnotationsListTab({
  hasSuccessfulExtractors,
  projectId,
  imageId,
  token,
  jobs,
  onAnnotationClick
}: ImageAnnotationsListTabProps) {
  if (!hasSuccessfulExtractors) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-muted-foreground mb-2">
              No Successful Extractors Available
            </h3>
            <p className="text-muted-foreground">
              Please wait for at least one extractor to complete successfully before viewing annotations.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-semibold">All Annotations</CardTitle>
      </CardHeader>
      <CardContent>
        <ImageAnnotationsListTable
          projectId={projectId}
          imageId={imageId}
          token={token}
          extractionJobs={jobs}
          onAnnotationClick={onAnnotationClick}
        />
      </CardContent>
    </Card>
  )
}

