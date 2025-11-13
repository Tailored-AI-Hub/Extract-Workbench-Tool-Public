'use client'

import { useParams } from 'next/navigation'
import Layout from '../../../components/Layout'
import { useAuth } from '../../../contexts/AuthContext'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { audioApi, AudioItem, PaginatedAudiosResponse } from '../../../services/audioApi'
import { useState } from 'react'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import UploadAudioModal from '../../components/UploadAudioModal'
import Link from 'next/link'
import { AudioFilesTable } from '../../components/AudioFilesTable'
import { ArrowLeft } from 'lucide-react'
import { toast } from '../../../components/ui/sonner'

export default function AudioProjectPage() {
  const params = useParams()
  const projectId = params?.projectId as string
  const { token } = useAuth()
  const queryClient = useQueryClient()
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)

  const { data: project } = useQuery({
    queryKey: ['audio-project', projectId],
    queryFn: () => audioApi.getProject(projectId, token!),
    enabled: !!token && !!projectId,
  })

  const [sortField, setSortField] = useState<'filename' | 'owner_name' | 'uploaded_at' | 'duration_seconds' | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  const { data: audiosData } = useQuery({
    queryKey: ['audio-list', projectId, currentPage, pageSize, sortField, sortDirection],
    queryFn: () => audioApi.getProjectAudios(projectId, token!, currentPage, pageSize, sortField || 'uploaded_at', sortDirection),
    enabled: !!token && !!projectId,
  })

  const uploadMutation = useMutation({
    mutationFn: ({ files, selectedExtractors, ownerName }: { files: File[]; selectedExtractors: string[]; ownerName: string }) =>
      audioApi.uploadAudios(projectId, files, selectedExtractors, token!, ownerName),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['audio-list', projectId] })
      setIsUploadModalOpen(false)
      
      const totalFiles = variables.files.length
      const successfulUploads = data.audio_uuids.length
      const failedUploads = data.failed_uploads.length
      
      if (failedUploads > 0) {
        // Show detailed error messages for each failed file
        const errorMessages = data.failed_uploads.map(
          (failure) => `${failure.filename}: ${failure.error}`
        ).join('\n')
        
        toast.error(
          `Some files failed to upload (${failedUploads} of ${totalFiles})`,
          {
            description: errorMessages,
            duration: 6000,
          }
        )
        
        // Still show success message if some files uploaded successfully
        if (successfulUploads > 0) {
          toast.success(
            `Successfully uploaded ${successfulUploads} file${successfulUploads !== 1 ? 's' : ''}`
          )
        }
      } else {
        // Show success message if all files uploaded successfully
        toast.success(
          `Successfully uploaded ${successfulUploads} file${successfulUploads !== 1 ? 's' : ''}`
        )
      }
    },
    onError: (error) => {
      toast.error(
        'Upload failed',
        {
          description: error instanceof Error ? error.message : 'An unexpected error occurred while uploading files',
          duration: 5000,
        }
      )
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (audioUuid: string) => audioApi.deleteAudio(projectId, audioUuid, token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audio-list', projectId] })
    },
  })

  const audios: AudioItem[] = audiosData?.audios || []

  return (
    <Layout>
      <div className="container mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Link href="/audio">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            </Link>
            <h1 className="text-2xl font-semibold">{project?.name || 'Project'}</h1>
          </div>
          <Button onClick={() => setIsUploadModalOpen(true)}>Upload Audio</Button>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="text-xl font-semibold">Audio Files</CardTitle>
          </CardHeader>
          <CardContent>
            <AudioFilesTable
              projectId={projectId}
              audios={audios}
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
              pagination={audiosData?.pagination}
              onPageChange={setCurrentPage}
              onPageSizeChange={(ps) => { setPageSize(ps); setCurrentPage(1) }}
              onDelete={(audioUuid) => deleteMutation.mutate(audioUuid)}
              isProjectOwner={project?.is_owner}
            />
          </CardContent>
        </Card>
      </div>

      <UploadAudioModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSubmit={(files, selectedExtractors, ownerName) => uploadMutation.mutate({ files, selectedExtractors, ownerName })}
        loading={uploadMutation.isPending}
      />
    </Layout>
  )
}


