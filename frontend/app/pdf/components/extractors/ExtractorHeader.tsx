/**
 * Header component for the extractor page
 * Displays project and document information with navigation
 */

import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';

interface ExtractorHeaderProps {
  projectId: string;
  projectName?: string;
  documentName?: string;
}

export function ExtractorHeader({
  projectId,
  projectName,
  documentName,
}: ExtractorHeaderProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Link href={`/pdf/projects/${projectId}`}>
                <Button variant="ghost" size="sm" className="gap-2">
                  <ArrowLeft className="h-4 w-4" />
                  Back to Project
                </Button>
              </Link>
            </div>
            {projectName && (
              <p className="text-sm text-muted-foreground">Project: {projectName}</p>
            )}
            {documentName && (
              <CardTitle className="text-2xl">{documentName}</CardTitle>
            )}
          </div>
        </div>
      </CardHeader>
    </Card>
  );
}
