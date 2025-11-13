import { useState, useEffect, useRef } from 'react';

export function useImageViewer(imageUrl: string, token: string | null, activeTab: string) {
  const [imageError, setImageError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!imageUrl) {
      setLoading(false);
      setObjectUrl(null);
      objectUrlRef.current = null;
      return;
    }

    setLoading(true);
    setImageError(null);

    // Fetch image with authentication and create object URL
    const controller = new AbortController();
    let currentUrl: string | null = null;
    
    fetch(imageUrl, { 
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal: controller.signal
    })
      .then(res => {
        if (!res.ok) {
          throw new Error(`Failed to load image (${res.status})`);
        }
        return res.blob();
      })
      .then(blob => {
        const url = URL.createObjectURL(blob);
        currentUrl = url;
        objectUrlRef.current = url;
        setObjectUrl(url);
        
        // Test if the image actually loads
        const img = new Image();
        img.onload = () => {
          setImageError(null);
          setLoading(false);
        };
        
        img.onerror = () => {
          setImageError('Failed to load image');
          setLoading(false);
          URL.revokeObjectURL(url);
          if (objectUrlRef.current === url) {
            objectUrlRef.current = null;
          }
          setObjectUrl(null);
        };
        
        img.src = url;
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          setImageError(err.message || 'Failed to fetch image');
          setLoading(false);
          setObjectUrl(null);
          objectUrlRef.current = null;
        }
      });

    return () => {
      controller.abort();
      if (currentUrl) {
        URL.revokeObjectURL(currentUrl);
      }
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    };
  }, [imageUrl, token, activeTab]);

  return {
    imageError,
    loading,
    imageUrl: objectUrl
  };
}

