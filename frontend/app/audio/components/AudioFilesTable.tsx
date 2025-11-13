'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { Button } from '../../components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../../components/ui/tooltip'
import { FileAudio, ExternalLink, ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight, Trash2 } from 'lucide-react'
import { AudioItem, AudioPaginationMeta } from '../../services/audioApi'
import { ConfirmationDialog } from '../../components/ui/confirmation-dialog'
import { formatDate } from '../../pdf/utils/formatters'

type AudioSortField = 'filename' | 'owner_name' | 'uploaded_at' | 'duration_seconds'
type SortDirection = 'asc' | 'desc'

interface AudioFilesTableProps {
  projectId: string
  audios: AudioItem[]
  sortField: AudioSortField | null
  sortDirection: SortDirection
  onSort: (field: AudioSortField) => void
  uploading?: boolean
  pagination?: AudioPaginationMeta
  onPageChange?: (page: number) => void
  onPageSizeChange?: (pageSize: number) => void
  onDelete?: (audioUuid: string) => void
  isProjectOwner?: boolean
}

export function AudioFilesTable({
  projectId,
  audios,
  sortField,
  sortDirection,
  onSort,
  uploading = false,
  pagination,
  onPageChange,
  onPageSizeChange,
  onDelete,
  isProjectOwner = false,
}: AudioFilesTableProps) {
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; audio: AudioItem | null }>({ isOpen: false, audio: null })

  const renderSortIcon = (field: AudioSortField) => {
    if (sortField === field) {
      return sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
    }
    return <ArrowUpDown className="h-4 w-4 opacity-50" />
  }

  const handleDelete = (audio: AudioItem, e: React.MouseEvent) => {
    e.stopPropagation()
    setDeleteConfirm({ isOpen: true, audio })
  }

  const confirmDelete = () => {
    if (deleteConfirm.audio && onDelete) {
      onDelete(deleteConfirm.audio.uuid)
    }
    setDeleteConfirm({ isOpen: false, audio: null })
  }

  const SortableHeader = ({ field, children, className }: { field: AudioSortField; children: React.ReactNode; className?: string }) => (
    <TableHead
      className={`cursor-pointer hover:bg-gray-50 select-none ${className || ''}`}
      onClick={() => onSort(field)}
    >
      <div className="flex items-center gap-1">
        {children}
        {renderSortIcon(field)}
      </div>
    </TableHead>
  )

  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <SortableHeader field="filename" className="max-w-xs">File Name</SortableHeader>
            <SortableHeader field="duration_seconds">Duration (s)</SortableHeader>
            <SortableHeader field="owner_name">Uploaded By</SortableHeader>
            <SortableHeader field="uploaded_at">Uploaded At</SortableHeader>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {uploading && (
            <TableRow className="bg-blue-50/50">
              <TableCell className="font-medium">
                <div className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                  <span className="text-blue-600 font-medium">Uploading files...</span>
                </div>
              </TableCell>
              <TableCell className="text-muted-foreground"><div className="animate-pulse bg-gray-200 h-4 w-8 rounded"></div></TableCell>
              <TableCell className="text-muted-foreground"><div className="animate-pulse bg-gray-200 h-4 w-16 rounded"></div></TableCell>
              <TableCell className="text-muted-foreground"><div className="animate-pulse bg-gray-200 h-4 w-20 rounded"></div></TableCell>
              <TableCell>
                <div className="flex items-center justify-end gap-3">
                  <div className="animate-pulse bg-gray-200 h-4 w-4 rounded"></div>
                  <div className="animate-pulse bg-gray-200 h-4 w-4 rounded"></div>
                </div>
              </TableCell>
            </TableRow>
          )}

          {audios.length === 0 && !uploading ? (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                <div className="flex flex-col items-center gap-2">
                  <FileAudio className="h-12 w-12 text-muted-foreground" />
                  <h3 className="text-lg font-semibold">No audio files yet</h3>
                  <p className="text-sm">Upload your first audio file to get started.</p>
                </div>
              </TableCell>
            </TableRow>
          ) : (
            audios.map((a) => (
              <TableRow key={a.uuid} className="cursor-pointer hover:bg-muted/50">
                <TableCell className="font-medium max-w-xs">
                  <div className="flex items-center gap-2">
                    <FileAudio className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="text-foreground truncate" title={a.filename}>{a.filename}</span>
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {a.duration_seconds != null ? Math.round(a.duration_seconds) : '-'}
                </TableCell>
                <TableCell className="text-muted-foreground">{a.owner_name || '-'}</TableCell>
                <TableCell className="text-muted-foreground" title={new Date(a.uploaded_at).toLocaleString()}>
                  {formatDate(a.uploaded_at)}
                </TableCell>
                <TableCell>
                  <div className="flex items-center justify-end gap-3">
                    <Link href={`/audio/projects/${projectId}/audios/${a.uuid}/extractors`}>
                      <ExternalLink className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                    </Link>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div>
                            <button
                              onClick={(e) => handleDelete(a, e)}
                              disabled={onDelete && !isProjectOwner}
                              className="text-destructive disabled:text-muted-foreground disabled:opacity-70 disabled:cursor-not-allowed"
                              title={isProjectOwner ? "Delete audio" : undefined}
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </TooltipTrigger>
                        {!isProjectOwner && onDelete && (
                          <TooltipContent>
                            <p>Only project owners can delete files</p>
                          </TooltipContent>
                        )}
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {pagination && onPageChange && onPageSizeChange && (
        <div className="flex items-center justify-between px-2 py-4 border-t">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>
              Showing {((pagination.page - 1) * pagination.page_size) + 1} to {Math.min(pagination.page * pagination.page_size, pagination.total_count)} of {pagination.total_count} audio files
            </span>
            <div className="flex items-center gap-2">
              <span>Rows per page:</span>
              <select
                value={pagination.page_size}
                onChange={(e) => onPageSizeChange(Number(e.target.value))}
                className="px-2 py-1 border rounded text-sm"
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(pagination.page - 1)}
              disabled={!pagination.has_previous}
              className="gap-1"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>

            <div className="flex items-center gap-1">
              <span className="text-sm text-muted-foreground">Page {pagination.page} of {pagination.total_pages}</span>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(pagination.page + 1)}
              disabled={!pagination.has_next}
              className="gap-1"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
      <ConfirmationDialog
        open={deleteConfirm.isOpen}
        onOpenChange={(open) => !open && setDeleteConfirm({ isOpen: false, audio: null })}
        onConfirm={confirmDelete}
        title="Delete Audio"
        description={`Are you sure you want to delete "${deleteConfirm.audio?.filename}"? This action cannot be undone.`}
        variant="destructive"
        confirmText="Delete"
        cancelText="Cancel"
      />
    </div>
  )
}


