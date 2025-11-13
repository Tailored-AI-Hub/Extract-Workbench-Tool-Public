'use client'

import { useParams } from 'next/navigation'
import Layout from '../../../components/Layout'
import { useAuth } from '../../../contexts/AuthContext'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { imageApi, ImageItem, PaginatedImagesResponse } from '../../../services/imageApi'
import { useState } from 'react'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import UploadImageModal from '../../components/UploadImageModal'
import Link from 'next/link'
import { ImageFilesTable } from '../../components/ImageFilesTable'
import { ArrowLeft } from 'lucide-react'
import { toast } from '../../../components/ui/sonner'

export default function ImageProjectPage() {
  const params = useParams()
  const projectId = params?.projectId as string
  const { token } = useAuth()
  const queryClient = useQueryClient()
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)

  const { data: project } = useQuery({
    queryKey: ['image-project', projectId],
    queryFn: () => imageApi.getProject(projectId, token!),
    enabled: !!token && !!projectId,
  })

  const [sortField, setSortField] = useState<'filename' | 'owner_name' | 'uploaded_at' | 'width' | 'height' | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  const { data: imagesData } = useQuery({
    queryKey: ['image-list', projectId, currentPage, pageSize, sortField, sortDirection],
    queryFn: () =>
      imageApi.getProjectImages(projectId, token!, currentPage, pageSize, sortField || 'uploaded_at', sortDirection),
    enabled: !!token && !!projectId,
  })

  const uploadMutation = useMutation({
    mutationFn: ({ files, selectedExtractors }: { files: File[]; selectedExtractors: string[] }) =>
      imageApi.uploadImages(projectId, files, selectedExtractors, token!),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['image-list', projectId] })
      setIsUploadModalOpen(false)

      const totalFiles = variables.files.length
      const successfulUploads = data.image_uuids.length
      const failedUploads = data.failed_uploads.length

      if (failedUploads > 0) {
        const errorMessages = data.failed_uploads.map((failure) => `${failure.filename}: ${failure.error}`).join('\n')

        toast.error(`Some files failed to upload (${failedUploads} of ${totalFiles})`, {
          description: errorMessages,
          duration: 6000,
        })

        if (successfulUploads > 0) {
          toast.success(`Successfully uploaded ${successfulUploads} file${successfulUploads !== 1 ? 's' : ''}`)
        }
      } else {
        toast.success(`Successfully uploaded ${successfulUploads} file${successfulUploads !== 1 ? 's' : ''}`)
      }
    },
    onError: (error) => {
      toast.error('Upload failed', {
        description: error instanceof Error ? error.message : 'An unexpected error occurred while uploading files',
        duration: 5000,
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (imageUuid: string) => imageApi.deleteImage(projectId, imageUuid, token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-list', projectId] })
    },
  })

  const images: ImageItem[] = imagesData?.images || []

  return (
    <Layout>
      <div className="container mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Link href="/image">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            </Link>
            <h1 className="text-2xl font-semibold">{project?.name || 'Project'}</h1>
          </div>
          <Button onClick={() => setIsUploadModalOpen(true)}>Upload Image</Button>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="text-xl font-semibold">Image Files</CardTitle>
          </CardHeader>
          <CardContent>
            <ImageFilesTable
              projectId={projectId}
              images={images}
              sortField={sortField}
              sortDirection={sortDirection}
              onSort={(field) => {
                if (sortField === field) {
                  setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                } else {
                  setSortField(field)
                  setSortDirection('asc')
                }
                setCurrentPage(1)
              }}
              uploading={uploadMutation.isPending}
              pagination={imagesData?.pagination}
              onPageChange={setCurrentPage}
              onPageSizeChange={(ps) => {
                setPageSize(ps)
                setCurrentPage(1)
              }}
              onDelete={(imageUuid) => deleteMutation.mutate(imageUuid)}
              isProjectOwner={project?.is_owner}
            />
          </CardContent>
        </Card>
      </div>

      <UploadImageModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSubmit={(files, selectedExtractors) => uploadMutation.mutate({ files, selectedExtractors })}
        loading={uploadMutation.isPending}
      />
    </Layout>
  )
}

