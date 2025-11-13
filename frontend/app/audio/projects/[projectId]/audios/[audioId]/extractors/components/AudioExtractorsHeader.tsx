'use client'

import Link from 'next/link'
import { Button } from '../../../../../../../components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '../../../../../../../components/ui/tabs'
import { ArrowLeft } from 'lucide-react'

interface AudioExtractorsHeaderProps {
  projectId: string
  filename?: string
  activeTab: string
  hasSuccessfulExtractors: boolean
  onTabChange: (value: string) => void
}

export function AudioExtractorsHeader({
  projectId,
  filename,
  activeTab,
  hasSuccessfulExtractors,
  onTabChange
}: AudioExtractorsHeaderProps) {
  return (
    <div className="flex items-center gap-6 w-full min-w-0 overflow-hidden">
      <div className="flex items-center gap-4 min-w-0 flex-1 overflow-hidden">
        <Link href={`/audio/projects/${projectId}`}>
          <Button variant="ghost" size="sm" className="flex-shrink-0">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </Link>
        <h1 className="text-3xl font-bold text-foreground truncate min-w-0">
          {filename || 'Audio File'}
        </h1>
      </div>
      <Tabs value={activeTab} onValueChange={onTabChange} className="flex-shrink-0">
        <TabsList>
          <TabsTrigger value="summary">Summary</TabsTrigger>
          <TabsTrigger 
            value="annotation" 
            disabled={!hasSuccessfulExtractors}
            className={!hasSuccessfulExtractors ? "opacity-50 cursor-not-allowed" : ""}
          >
            Annotation
          </TabsTrigger>
          <TabsTrigger 
            value="annotations-list" 
            disabled={!hasSuccessfulExtractors}
            className={!hasSuccessfulExtractors ? "opacity-50 cursor-not-allowed" : ""}
          >
            Annotations List
          </TabsTrigger>
        </TabsList>
      </Tabs>
    </div>
  )
}

