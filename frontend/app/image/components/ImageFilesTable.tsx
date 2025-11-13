'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { Button } from '../../components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../../components/ui/tooltip'
import { Image as ImageIcon, ExternalLink, ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight, Trash2 } from 'lucide-react'
import { ImageItem, ImagePaginationMeta } from '../../services/imageApi'
import { ConfirmationDialog } from '../../components/ui/confirmation-dialog'
import { formatDate } from '../../pdf/utils/formatters'

type ImageSortField = 'filename' | 'owner_name' | 'uploaded_at' | 'width' | 'height'
type SortDirection = 'asc' | 'desc'

interface ImageFilesTableProps {
  projectId: string
  images: ImageItem[]
  sortField: ImageSortField | null
  sortDirection: SortDirection
  onSort: (field: ImageSortField) => void
  uploading?: boolean
  pagination?: ImagePaginationMeta
  onPageChange?: (page: number) => void
  onPageSizeChange?: (pageSize: number) => void
  onDelete?: (imageUuid: string) => void
  isProjectOwner?: boolean
}

export function ImageFilesTable({
  projectId,
  images,
  sortField,
  sortDirection,
  onSort,
  uploading = false,
  pagination,
  onPageChange,
  onPageSizeChange,
  onDelete,
  isProjectOwner = false,
}: ImageFilesTableProps) {
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; image: ImageItem | null }>({ isOpen: false, image: null })

  const renderSortIcon = (field: ImageSortField) => {
    if (sortField === field) {
      return sortDirection === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />
    }
    return <ArrowUpDown className="h-4 w-4 opacity-50" />
  }

  const handleDelete = (image: ImageItem, e: React.MouseEvent) => {
    e.stopPropagation()
    setDeleteConfirm({ isOpen: true, image })
  }

  const confirmDelete = () => {
    if (deleteConfirm.image && onDelete) {
      onDelete(deleteConfirm.image.uuid)
    }
    setDeleteConfirm({ isOpen: false, image: null })
  }

  const SortableHeader = ({ field, children, className }: { field: ImageSortField; children: React.ReactNode; className?: string }) => (
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
            <SortableHeader field="width">Dimensions</SortableHeader>
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
              <TableCell className="text-muted-foreground"><div className="animate-pulse bg-gray-200 h-4 w-16 rounded"></div></TableCell>
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

          {images.length === 0 && !uploading ? (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                <div className="flex flex-col items-center gap-2">
                  <ImageIcon className="h-12 w-12 text-muted-foreground" />
                  <h3 className="text-lg font-semibold">No image files yet</h3>
                  <p className="text-sm">Upload your first image file to get started.</p>
                </div>
              </TableCell>
            </TableRow>
          ) : (
            images.map((img) => (
              <TableRow key={img.uuid} className="cursor-pointer hover:bg-muted/50">
                <TableCell className="font-medium max-w-xs">
                  <div className="flex items-center gap-2">
                    <ImageIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="text-foreground truncate" title={img.filename}>{img.filename}</span>
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {img.width && img.height ? `${img.width}×${img.height}` : '-'}
                </TableCell>
                <TableCell className="text-muted-foreground">{img.owner_name || '-'}</TableCell>
                <TableCell className="text-muted-foreground" title={new Date(img.uploaded_at).toLocaleString()}>
                  {formatDate(img.uploaded_at)}
                </TableCell>
                <TableCell>
                  <div className="flex items-center justify-end gap-3">
                    <Link href={`/image/projects/${projectId}/images/${img.uuid}/extractors`}>
                      <ExternalLink className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                    </Link>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div>
                            <button
                              onClick={(e) => handleDelete(img, e)}
                              disabled={onDelete && !isProjectOwner}
                              className="text-destructive disabled:text-muted-foreground disabled:opacity-70 disabled:cursor-not-allowed"
                              title={isProjectOwner ? "Delete image" : undefined}
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
              Showing {((pagination.page - 1) * pagination.page_size) + 1} to {Math.min(pagination.page * pagination.page_size, pagination.total_count)} of {pagination.total_count} images
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
        onOpenChange={(open) => !open && setDeleteConfirm({ isOpen: false, image: null })}
        onConfirm={confirmDelete}
        title="Delete Image"
        description={`Are you sure you want to delete "${deleteConfirm.image?.filename}"? This action cannot be undone.`}
        variant="destructive"
        confirmText="Delete"
        cancelText="Cancel"
      />
    </div>
  )
}

