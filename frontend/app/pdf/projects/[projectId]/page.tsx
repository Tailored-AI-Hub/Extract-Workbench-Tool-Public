'use client'

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";
import { Upload, ArrowLeft } from "lucide-react";
import Layout from "../../../components/Layout";
import UploadFileModal from "../../components/documents/UploadFileModal";
import ProtectedRoute from "../../../components/ProtectedRoute";
import { useAuth } from "../../../contexts/AuthContext";
import { pdfApi, Document, PaginatedDocumentsResponse, PaginationMeta } from "../../../services/pdfApi";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ConfirmationDialog } from "../../../components/ui/confirmation-dialog";
import { DocumentsTable } from "../../components/documents";
import { DocumentSortField, SortDirection, DocumentSortFieldType, SortDirectionType } from "../../types";
import { toast } from "../../../components/ui/sonner";

function ProjectPageContent() {
  const params = useParams();
  const projectId = params?.projectId as string;
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean;
    document: Document | null;
  }>({ open: false, document: null });
  const [sortField, setSortField] = useState<DocumentSortFieldType | null>('uploaded_at');
  const [sortDirection, setSortDirection] = useState<SortDirectionType>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const { token } = useAuth();
  const queryClient = useQueryClient();

  // Fetch project details
  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => pdfApi.getProject(projectId, token!),
    enabled: !!token && !!projectId,
  });

  // Fetch project documents with pagination and sorting
  const { data: documentsData, isLoading: documentsLoading } = useQuery({
    queryKey: ['documents', projectId, currentPage, pageSize, sortField, sortDirection],
    queryFn: () => pdfApi.getProjectDocuments(
      projectId, 
      token!, 
      currentPage, 
      pageSize, 
      sortField || "uploaded_at", 
      sortDirection
    ),
    enabled: !!token && !!projectId,
  });

  const documents = documentsData?.documents || [];
  const pagination = documentsData?.pagination;

  // Upload documents mutation - handles both single and multiple files
  const uploadMutation = useMutation({
    mutationFn: ({ files, selectedExtractors, ownerName }: { files: File[]; selectedExtractors: string[]; ownerName: string }) =>
      pdfApi.uploadDocuments(projectId, files, selectedExtractors, token!, ownerName),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['documents', projectId] });
      setIsUploadModalOpen(false);
      
      const totalFiles = variables.files.length;
      const successfulUploads = data.document_uuids.length;
      const failedUploads = data.failed_uploads.length;
      
      if (failedUploads > 0) {
        // Show detailed error messages for each failed file
        const errorMessages = data.failed_uploads.map(
          (failure) => `${failure.filename}: ${failure.error}`
        ).join('\n');
        
        toast.error(
          `Some files failed to upload (${failedUploads} of ${totalFiles})`,
          {
            description: errorMessages,
            duration: 6000,
          }
        );
        
        // Still show success message if some files uploaded successfully
        if (successfulUploads > 0) {
          toast.success(
            `Successfully uploaded ${successfulUploads} file${successfulUploads !== 1 ? 's' : ''}`
          );
        }
      } else {
        // Show success message if all files uploaded successfully
        toast.success(
          `Successfully uploaded ${successfulUploads} file${successfulUploads !== 1 ? 's' : ''}`
        );
      }
    },
    onError: (error) => {
      toast.error(
        'Upload failed',
        {
          description: error instanceof Error ? error.message : 'An unexpected error occurred while uploading files',
          duration: 5000,
        }
      );
    },
  });

  // Delete document mutation (owner only)
  const deleteMutation = useMutation({
    mutationFn: ({ documentUuid }: { documentUuid: string }) =>
      pdfApi.deleteDocument(projectId, documentUuid, token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', projectId] });
      setDeleteDialog({ open: false, document: null });
    },
  });

  const handleDelete = (document: Document) => {
    if (!project?.is_owner) return;
    setDeleteDialog({ open: true, document });
  };

  const confirmDeleteDocument = () => {
    if (deleteDialog.document) {
      deleteMutation.mutate({ documentUuid: deleteDialog.document.uuid });
    }
  };

  const handleUploadSubmit = (files: File[], selectedExtractors: string[], ownerName: string) => {
    if (files.length > 0) {
      uploadMutation.mutate({ files, selectedExtractors, ownerName });
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize);
    setCurrentPage(1); // Reset to first page when changing page size
  };

  // Sorting functionality
  const handleSort = (field: DocumentSortFieldType) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
    // Reset to first page when sorting changes
    setCurrentPage(1);
  };

  if (projectLoading || documentsLoading) {
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

  if (!project) {
    return (
      <Layout>
        <div className="container mx-auto px-6 py-8">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-red-600 mb-4">Project not found</h2>
            <p className="text-gray-600">The project you&apos;re looking for doesn&apos;t exist.</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mx-auto px-6 py-8">
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back
                </Button>
              </Link>
              <div>
                <h1 className="text-3xl font-bold text-foreground">{project.name}</h1>
              </div>
            </div>
            <Button 
              onClick={() => setIsUploadModalOpen(true)}
              className="gap-2"
              disabled={uploadMutation.isPending}
            >
              <Upload className="h-4 w-4" />
              {uploadMutation.isPending ? 'Uploading...' : 'Upload Files'}
            </Button>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl font-semibold">Documents</CardTitle>
          </CardHeader>
          <CardContent>
            <DocumentsTable
              projectId={projectId}
              documents={documents}
              isOwner={project?.is_owner || false}
              onDelete={handleDelete}
              deleting={deleteMutation.isPending}
              sortField={sortField}
              sortDirection={sortDirection}
              onSort={handleSort}
              uploading={uploadMutation.isPending}
              pagination={pagination}
              onPageChange={handlePageChange}
              onPageSizeChange={handlePageSizeChange}
            />
          </CardContent>
        </Card>
      </div>
      
      <UploadFileModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSubmit={handleUploadSubmit}
        loading={uploadMutation.isPending}
        projectType="pdf"
      />

      <ConfirmationDialog
        open={deleteDialog.open}
        onOpenChange={(open) => setDeleteDialog({ open, document: null })}
        title="Delete Document"
        description={`Are you sure you want to delete "${deleteDialog.document?.filename}"? This cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="destructive"
        onConfirm={confirmDeleteDocument}
        loading={deleteMutation.isPending}
      />
    </Layout>
  );
}

export default function ProjectDetailPage() {
  return (
    <ProtectedRoute>
      <ProjectPageContent />
    </ProtectedRoute>
  );
}
