'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { Image as ImageIcon, Clock, Trash2, User } from 'lucide-react'
import { ImageProject } from '../../services/imageApi'
import { formatDate } from '../../pdf/utils/formatters'
import { ConfirmationDialog } from '../../components/ui/confirmation-dialog'

interface ImageProjectCardProps {
  project: ImageProject
  onDelete?: (project: ImageProject) => void
  deleting?: boolean
}

export function ImageProjectCard({ project, onDelete, deleting = false }: ImageProjectCardProps) {
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (project.is_owner !== false) {
      setDeleteConfirm(true)
    }
  }

  const confirmDelete = () => {
    if (onDelete && project.is_owner !== false) {
      onDelete(project)
    }
    setDeleteConfirm(false)
  }

  return (
    <>
      <Card className="h-full hover:shadow-md transition-shadow relative group">
        <Link href={`/image/projects/${project.uuid}`} className="block h-full">
          <CardHeader>
            <div className="flex items-start justify-between mb-2">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <ImageIcon className="h-5 w-5 text-primary" />
              </div>
              <div className="flex items-center gap-3">
                <Badge>Image</Badge>
                {onDelete && (
                  <button
                    aria-label="Delete project"
                    title="Delete project"
                    disabled={deleting || project.is_owner === false}
                    onClick={handleDeleteClick}
                    className="p-1.5 rounded-md transition-colors text-destructive disabled:text-muted-foreground disabled:opacity-70 disabled:cursor-not-allowed"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>

            <CardTitle className="text-xl break-words overflow-hidden" style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', lineHeight: '1.4', maxHeight: '2.8em' }}>
              {project.name}
            </CardTitle>
            <CardDescription className="break-words overflow-hidden" style={{ display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', lineHeight: '1.4', maxHeight: '4.2em' }}>
              {project.description || 'No description'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <User className="h-3.5 w-3.5" />
                <span>Owner: {project.owner_name || 'Unknown'}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground pt-2 border-t">
                <Clock className="h-3.5 w-3.5" />
                <span>Created {formatDate(project.created_at)}</span>
              </div>
            </div>
          </CardContent>
        </Link>
      </Card>
      <ConfirmationDialog
        open={deleteConfirm}
        onOpenChange={setDeleteConfirm}
        onConfirm={confirmDelete}
        title="Delete Image Project"
        description={`Are you sure you want to delete "${project.name}"? This action cannot be undone and will delete all associated images and annotations.`}
        variant="destructive"
        confirmText="Delete"
        cancelText="Cancel"
        loading={deleting}
      />
    </>
  )
}

