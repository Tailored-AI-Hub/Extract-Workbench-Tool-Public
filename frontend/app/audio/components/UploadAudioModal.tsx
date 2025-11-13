'use client'

import { useState, useCallback } from 'react'
import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Checkbox } from '../../components/ui/checkbox'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog'
import { DropdownMenu, DropdownMenuTrigger } from '../../components/ui/dropdown-menu'
import { X, Upload, CheckCircle, FileText } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../contexts/AuthContext'
import { cn } from '../../lib/utils'
import { API_BASE_URL } from '../../services/api'

interface UploadAudioModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (files: File[], selectedExtractors: string[], ownerName: string) => void
  loading?: boolean
}

export default function UploadAudioModal({ isOpen, onClose, onSubmit, loading = false }: UploadAudioModalProps) {
  const { user } = useAuth()
  const [files, setFiles] = useState<File[]>([])
  const [selectedExtractors, setSelectedExtractors] = useState<string[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [ownerName, setOwnerName] = useState<string>(user?.name || '')

  const { data: extractors, isLoading: extractorsLoading } = useQuery({ 
    queryKey: ['audio-extractors'], 
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/audio/extractors`)
      if (!res.ok) throw new Error('Failed to fetch audio extractors')
      return res.json() as Promise<{ audio_extractors: Array<{ category: string; extractors: Array<{ id: string; name: string; description: string; cost_per_page: number; support_tags: string[] }> }> }>
    }
  })

  const relevantExtractors = (extractors?.audio_extractors || [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    
    const droppedFiles = Array.from(e.dataTransfer.files)
    const validFiles = droppedFiles.filter(file => {
      return /\.(mp3|wav|m4a|flac|ogg|webm)$/i.test(file.name) || file.type.startsWith('audio/')
    })
    
    setFiles(prev => [...prev, ...validFiles])
  }, [])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || [])
    const validFiles = selectedFiles.filter(file => {
      return /\.(mp3|wav|m4a|flac|ogg|webm)$/i.test(file.name) || file.type.startsWith('audio/')
    })
    setFiles(prev => [...prev, ...validFiles])
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleExtractorToggle = (extractorId: string) => {
    setSelectedExtractors(prev => 
      prev.includes(extractorId) 
        ? prev.filter(id => id !== extractorId)
        : [...prev, extractorId]
    )
  }

  // Helper functions for category selection
  const getCategoryExtractors = (categoryName: string): string[] => {
    const category = relevantExtractors.find(cat => cat.category === categoryName)
    return category ? category.extractors.map(ext => ext.id) : []
  }

  const isCategoryFullySelected = (categoryName: string): boolean => {
    const categoryExtractors = getCategoryExtractors(categoryName)
    return categoryExtractors.length > 0 && categoryExtractors.every(id => selectedExtractors.includes(id))
  }

  const isCategoryPartiallySelected = (categoryName: string): boolean => {
    const categoryExtractors = getCategoryExtractors(categoryName)
    const selectedInCategory = categoryExtractors.filter(id => selectedExtractors.includes(id))
    return selectedInCategory.length > 0 && selectedInCategory.length < categoryExtractors.length
  }

  const handleCategoryToggle = (categoryName: string) => {
    const categoryExtractors = getCategoryExtractors(categoryName)
    const isFullySelected = isCategoryFullySelected(categoryName)
    
    if (isFullySelected) {
      // Deselect all extractors in this category
      setSelectedExtractors(prev => prev.filter(id => !categoryExtractors.includes(id)))
    } else {
      // Select all extractors in this category
      setSelectedExtractors(prev => {
        const newSelection = [...prev]
        categoryExtractors.forEach(id => {
          if (!newSelection.includes(id)) {
            newSelection.push(id)
          }
        })
        return newSelection
      })
    }
  }

  const handleSelectAllExtractors = () => {
    const allExtractorIds = relevantExtractors.flatMap(category => 
      category.extractors.map(extractor => extractor.id)
    )
    setSelectedExtractors(allExtractorIds)
  }

  const handleDeselectAllExtractors = () => {
    setSelectedExtractors([])
  }

  // Calculate total cost
  const calculateTotalCost = (): number => {
    return selectedExtractors.reduce((total, extractorId) => {
      const extractor = relevantExtractors
        .flatMap(cat => cat.extractors)
        .find(ext => ext.id === extractorId)
      return total + (extractor?.cost_per_page || 0)
    }, 0)
  }

  const handleSubmit = () => {
    if (files.length > 0 && selectedExtractors.length > 0) {
      // Use ownerName if provided, otherwise fallback to user name or 'Unknown'
      const finalOwnerName = ownerName.trim() || user?.name || 'Unknown'
      onSubmit(files, selectedExtractors, finalOwnerName)
      setFiles([])
      setSelectedExtractors([])
      setOwnerName(user?.name || '')
      onClose()
    }
  }

  const handleClose = () => {
    setFiles([])
    setSelectedExtractors([])
    setSelectedCategories([])
    onClose()
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            Upload Files
          </DialogTitle>
          <DialogDescription>
            Upload one or more files and select extractors to process them.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-6">
          {/* File Upload Area */}
          <div
            className={cn(
              "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
              isDragOver 
                ? "border-blue-500 bg-blue-50" 
                : "border-gray-300 hover:border-gray-400"
            )}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <p className="text-lg font-medium text-gray-900 mb-2">
              Drag and drop files here, or click to select
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Supports audio files (MP3, WAV, M4A, FLAC, OGG, WebM)
            </p>
            <input
              type="file"
              multiple
              accept=".mp3,.wav,.m4a,.flac,.ogg,.webm,audio/*"
              onChange={handleFileInput}
              className="hidden"
              id="audio-file-upload"
            />
            <Button asChild>
              <label htmlFor="audio-file-upload" className="cursor-pointer">
                Choose Files
              </label>
            </Button>
          </div>

          {/* Selected Files */}
          {files.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-900 mb-2">
                Selected Files ({files.length})
              </h4>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {files.map((file, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-gray-500" />
                      <span className="text-sm text-gray-900">{file.name}</span>
                      <span className="text-xs text-gray-500">
                        ({(file.size / 1024 / 1024).toFixed(2)} MB)
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(index)}
                      className="h-6 w-6 p-0"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Extractor Selection */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Select Extractors</CardTitle>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSelectAllExtractors}
                    disabled={extractorsLoading}
                  >
                    Select All
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDeselectAllExtractors}
                    disabled={extractorsLoading}
                  >
                    Deselect All
                  </Button>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                    </DropdownMenuTrigger>
                  </DropdownMenu> 
                </div>
               </div>
             </CardHeader>
            <CardContent>
              {extractorsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                </div>
              ) : (
                <div className="space-y-6">
                  {relevantExtractors.map((category) => (
                    <div key={category.category} className="border rounded-lg p-4">
                      {/* Category Header with Select All/Deselect All */}
                      <div className="flex items-center justify-between mb-4 pb-2 border-b">
                        <div className="flex items-center space-x-3">
                          <Checkbox
                            id={`category-${category.category}`}
                            checked={isCategoryFullySelected(category.category)}
                            onCheckedChange={() => handleCategoryToggle(category.category)}
                          />
                          <label
                            htmlFor={`category-${category.category}`}
                            className="text-sm font-semibold text-gray-900 cursor-pointer"
                          >
                            {category.category}
                          </label>
                          <span className="text-xs text-gray-500">
                            ({category.extractors.length} extractors)
                          </span>
                        </div>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              const categoryExtractors = getCategoryExtractors(category.category)
                              setSelectedExtractors(prev => {
                                const newSelection = [...prev]
                                categoryExtractors.forEach(id => {
                                  if (!newSelection.includes(id)) {
                                    newSelection.push(id)
                                  }
                                })
                                return newSelection
                              })
                            }}
                            className="text-xs h-6 px-2"
                          >
                            Select All
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              const categoryExtractors = getCategoryExtractors(category.category)
                              setSelectedExtractors(prev => prev.filter(id => !categoryExtractors.includes(id)))
                            }}
                            className="text-xs h-6 px-2"
                          >
                            Deselect All
                          </Button>
                        </div>
                      </div>
                      
                      {/* Individual Extractors */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {category.extractors.map((extractor) => (
                          <div
                            key={extractor.id}
                            className="flex items-start space-x-3 p-3 border rounded-lg hover:bg-gray-50 transition-colors"
                          >
                            <Checkbox
                              id={extractor.id}
                              checked={selectedExtractors.includes(extractor.id)}
                              onCheckedChange={() => handleExtractorToggle(extractor.id)}
                            />
                            <div className="flex-1 min-w-0">
                              <label
                                htmlFor={extractor.id}
                                className="text-sm font-medium text-gray-900 cursor-pointer"
                              >
                                {extractor.name}
                              </label>
                              <div className="flex items-center gap-2 mt-1">
                                <span className="text-xs text-blue-600 font-medium">
                                  ${extractor.cost_per_page.toFixed(4)}/minute
                                </span>
                                {extractor.support_tags.length > 0 && (
                                  <div className="flex gap-1">
                                    {extractor.support_tags.map((tag) => (
                                      <span
                                        key={tag}
                                        className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded"
                                      >
                                        {tag}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                  {relevantExtractors.length === 0 && (
                    <div className="text-sm text-muted-foreground">No extractors available</div>
                  )}
                </div>
              )}
              
              {/* Selection Summary */}
              {selectedExtractors.length > 0 && (
                <div className="mt-6 p-3 bg-blue-50 rounded-lg">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-blue-900">
                      {selectedExtractors.length} extractor{selectedExtractors.length !== 1 ? 's' : ''} selected
                    </span>
                    <span className="font-semibold text-blue-900">
                      Estimated cost: ${calculateTotalCost().toFixed(4)}/minute
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit}
            disabled={files.length === 0 || selectedExtractors.length === 0 || loading}
            className="gap-2"
            type="button"
          >
            <CheckCircle className="h-4 w-4" />
            {loading ? 'Processing...' : 'Process'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}


