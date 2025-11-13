'use client'

import { useState } from "react";
import { Button } from "../components/ui/button";
import { FileText, Plus } from "lucide-react";
import Layout from "../components/Layout";
import NewProjectModal from "./components/new-project/NewProjectModal";
import ProtectedRoute from "../components/ProtectedRoute";
import { useAuth } from "../contexts/AuthContext";
import { pdfApi, Project } from "../services/pdfApi";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ConfirmationDialog } from "../components/ui/confirmation-dialog";
import { ProjectCard } from "./components/project-card";

function DocumentHomePageContent() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean;
    project: Project | null;
  }>({ open: false, project: null });
  const { token } = useAuth();
  const queryClient = useQueryClient();

  // Fetch projects
  const { data: projects = [], isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: () => pdfApi.getProjects(token!),
    enabled: !!token,
  });

  // Show all projects from /projects endpoint (they are all PDF projects)
  const docProjects = projects || [];

  // Create project mutation
  const createProjectMutation = useMutation({
    mutationFn: (projectData: any) => pdfApi.createProject(projectData, token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setIsModalOpen(false);
    },
  });

  // Delete project mutation
  const deleteProjectMutation = useMutation({
    mutationFn: (projectUuid: string) => pdfApi.deleteProject(projectUuid, token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setDeleteDialog({ open: false, project: null });
    },
  });

  const handleCreateProject = (projectData: any) => {
    createProjectMutation.mutate(projectData);
  };

  const handleDeleteProject = (project: Project) => {
    setDeleteDialog({ open: true, project });
  };

  const confirmDeleteProject = () => {
    if (deleteDialog.project) {
      deleteProjectMutation.mutate(deleteDialog.project.uuid);
    }
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="container mx-auto px-6 py-8">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="container mx-auto px-6 py-8">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-red-600 mb-4">Error loading projects</h2>
            <p className="text-gray-600">Please try refreshing the page.</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">Pdf Projects</h1>
            </div>
            <div className="flex items-center gap-2">
              <Button 
                onClick={() => setIsModalOpen(true)}
                className="gap-2"
              >
                <Plus className="h-4 w-4" />
                New Project
              </Button>
            </div>
          </div>
        </div>

        {docProjects.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No projects yet</h3>
            <p className="text-muted-foreground mb-4">Create your first project to get started with document extraction.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {docProjects.map((project) => (
              <ProjectCard
                key={project.uuid}
                project={project}
                onDelete={handleDeleteProject}
                deleting={deleteProjectMutation.isPending}
              />
            ))}
          </div>
        )}
      </div>
      
      <NewProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateProject}
        loading={createProjectMutation.isPending}
      />

      <ConfirmationDialog
        open={deleteDialog.open}
        onOpenChange={(open) => setDeleteDialog({ open, project: null })}
        title="Delete Project"
        description={`Are you sure you want to delete "${deleteDialog.project?.name}"? This will also delete all documents and cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="destructive"
        onConfirm={confirmDeleteProject}
        loading={deleteProjectMutation.isPending}
      />
    </Layout>
  );
}

export default function DocumentHomePage() {
  return (
    <ProtectedRoute>
      <DocumentHomePageContent />
    </ProtectedRoute>
  );
}

