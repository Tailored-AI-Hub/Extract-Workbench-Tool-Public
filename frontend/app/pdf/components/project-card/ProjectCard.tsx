'use client'

import React from 'react';
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { FileText, Clock, User, Trash2 } from "lucide-react";
import { Project } from "../../../services/pdfApi";
import { formatDate } from '../../utils';

interface ProjectCardProps {
  project: Project;
  onDelete: (project: Project) => void;
  deleting: boolean;
}

export function ProjectCard({ project, onDelete, deleting }: ProjectCardProps) {
  return (
    <Card className="h-full hover:shadow-md transition-shadow relative group">
      <Link href={`/pdf/projects/${project.uuid}`} className="block h-full">
        <CardHeader>
          <div className="flex items-start justify-between mb-2">
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center" style={{ color: '#000000' }}>
              <FileText className="h-5 w-5" strokeWidth={1.5} />
            </div>
            <div className="flex items-center gap-3">
              <Badge variant="default">
                PDF
              </Badge>
              <button
                aria-label={project.is_owner ? "Delete project" : "Only owners can delete projects"}
                title={project.is_owner ? "Delete project" : "Only owners can delete projects"}
                disabled={!project.is_owner || deleting}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  if (project.is_owner) {
                    onDelete(project);
                  }
                }}
                className={`p-1.5 rounded-md transition-colors ${
                  project.is_owner 
                    ? 'text-red-600 hover:text-red-700 hover:bg-red-50' 
                    : 'text-gray-400 cursor-not-allowed'
                } disabled:opacity-50`}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
          <CardTitle className="text-xl break-words overflow-hidden" style={{
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            lineHeight: '1.4',
            maxHeight: '2.8em'
          }}>{project.name}</CardTitle>
          <CardDescription className="break-words overflow-hidden" style={{
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            lineHeight: '1.4',
            maxHeight: '4.2em'
          }}>{project.description || 'No description'}</CardDescription>
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
  );
}

