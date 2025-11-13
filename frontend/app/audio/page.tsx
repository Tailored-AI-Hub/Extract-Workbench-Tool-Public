'use client'

import { useState } from 'react'
import Layout from '../components/Layout'
import { Button } from '../components/ui/button'
import { useAuth } from '../contexts/AuthContext'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { audioApi, AudioProject } from '../services/audioApi'
import { FileAudio, Plus } from 'lucide-react'
import Link from 'next/link'
import NewAudioProjectModal from './components/NewAudioProjectModal'
import { AudioProjectCard } from './components/AudioProjectCard'

export default function AudioHomePage() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const { token } = useAuth()
  const queryClient = useQueryClient()

  const { data: projects = [] } = useQuery({
    queryKey: ['audio-projects'],
    queryFn: () => audioApi.getProjects(token!),
    enabled: !!token,
  })

  const createProjectMutation = useMutation({
    mutationFn: (data: { name: string; description?: string }) => audioApi.createProject({ name: data.name, description: data.description }, token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audio-projects'] })
      setIsModalOpen(false)
    },
  })

  const deleteProjectMutation = useMutation({
    mutationFn: (projectUuid: string) => audioApi.deleteProject(projectUuid, token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audio-projects'] })
    },
  })

  return (
    <Layout>
      <div className="container mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">Audio Projects</h1>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={() => setIsModalOpen(true)} className="gap-2">
                <Plus className="h-4 w-4" />
                New Project
              </Button>
            </div>
          </div>
        </div>

        {projects.length === 0 ? (
          <div className="text-center py-12">
            <FileAudio className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No audio projects yet</h3>
            <p className="text-muted-foreground mb-4">Create your first audio project to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project: AudioProject) => (
              <AudioProjectCard
                key={project.uuid}
                project={project}
                deleting={deleteProjectMutation.isPending}
                onDelete={(p) => deleteProjectMutation.mutate(p.uuid)}
              />
            ))}
          </div>
        )}
      </div>

      <NewAudioProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={(data) => createProjectMutation.mutate(data)}
        loading={createProjectMutation.isPending}
      />
    </Layout>
  )
}


