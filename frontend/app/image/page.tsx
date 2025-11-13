'use client'

import { useState } from 'react'
import Layout from '../components/Layout'
import { Button } from '../components/ui/button'
import { useAuth } from '../contexts/AuthContext'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { imageApi, ImageProject } from '../services/imageApi'
import { Image as ImageIcon, Plus } from 'lucide-react'
import Link from 'next/link'
import NewImageProjectModal from './components/NewImageProjectModal'
import { ImageProjectCard } from './components/ImageProjectCard'

export default function ImageHomePage() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const { token } = useAuth()
  const queryClient = useQueryClient()

  const { data: projects = [] } = useQuery({
    queryKey: ['image-projects'],
    queryFn: () => imageApi.getProjects(token!),
    enabled: !!token,
  })

  const createProjectMutation = useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      imageApi.createProject({ name: data.name, description: data.description }, token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-projects'] })
      setIsModalOpen(false)
    },
  })

  const deleteProjectMutation = useMutation({
    mutationFn: (projectUuid: string) => imageApi.deleteProject(projectUuid, token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-projects'] })
    },
  })

  return (
    <Layout>
      <div className="container mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">Image Projects</h1>
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
            <ImageIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No image projects yet</h3>
            <p className="text-muted-foreground mb-4">Create your first image project to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project: ImageProject) => (
              <ImageProjectCard
                key={project.uuid}
                project={project}
                deleting={deleteProjectMutation.isPending}
                onDelete={(p) => deleteProjectMutation.mutate(p.uuid)}
              />
            ))}
          </div>
        )}
      </div>

      <NewImageProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={(data) => createProjectMutation.mutate(data)}
        loading={createProjectMutation.isPending}
      />
    </Layout>
  )
}

