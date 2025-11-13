/**
 * Dynamic imports for modal components
 * Modals are loaded on-demand since they're not initially visible
 */

import dynamic from 'next/dynamic';

// Dynamically import modal components for better code splitting
export const DynamicUploadFileModal = dynamic(
  () => import('../pdf/components/documents/UploadFileModal'),
  {
    ssr: false, // Modals should only render on client
  }
);

export const DynamicNewProjectModal = dynamic(
  () => import('../pdf/components/new-project/NewProjectModal'),
  {
    ssr: false,
  }
);

export const DynamicChangePasswordModal = dynamic(
  () => import('./ChangePasswordModal'),
  {
    ssr: false,
  }
);
