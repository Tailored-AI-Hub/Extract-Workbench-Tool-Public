"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "../../services/api";

type UseSecureImageOptions = {
  /** If true, attempt direct URL first, then fall back to proxy */
  tryDirectFirst?: boolean;
  /** If true, store successful proxy responses in Cache API */
  enableCache?: boolean;
};

export function useSecureImage(
  imageUrl: string | null | undefined,
  options: UseSecureImageOptions = {}
) {
  const { tryDirectFirst = false, enableCache = false } = options;
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const currentObjectUrlRef = useRef<string | null>(null);

  useEffect(() => {
    let aborted = false;

    async function fetchAsBlob(finalUrl: string): Promise<Blob> {
      if (enableCache && "caches" in window) {
        try {
          const cache = await caches.open("secure-images-v1");
          const req = new Request(finalUrl, { credentials: "include" });
          const cached = await cache.match(req);
          if (cached) {
            const blob = await cached.clone().blob();
            return blob;
          }
          const res = await fetch(req);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          await cache.put(req, res.clone());
          const blob = await res.blob();
          return blob;
        } catch (e) {
          // Fallback to network without cache
        }
      }

      const res = await fetch(finalUrl, { credentials: "include" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.blob();
    }

    async function load() {
      if (!imageUrl) {
        setBlobUrl(null);
        setError(null);
        setLoading(false);
        return;
      }
      // If the input is already a blob: or data: URL, use it directly and skip proxy/fetch.
      // The backend proxy only accepts http/https to specific hosts and will 400 on blob: URLs.
      if (imageUrl.startsWith("blob:") || imageUrl.startsWith("data:")) {
        // Revoke any object URL we previously created since we're switching to an external one
        if (currentObjectUrlRef.current) {
          URL.revokeObjectURL(currentObjectUrlRef.current);
          currentObjectUrlRef.current = null;
        }
        setBlobUrl(imageUrl);
        setError(null);
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);

      const direct = imageUrl;
      const proxy = `${API_BASE_URL}/proxy/image?url=${encodeURIComponent(imageUrl)}`;

      try {
        let blob: Blob | null = null;
        if (tryDirectFirst) {
          try {
            blob = await fetchAsBlob(direct);
          } catch {
            blob = await fetchAsBlob(proxy);
          }
        } else {
          blob = await fetchAsBlob(proxy);
        }

        if (aborted) return;
        const newUrl = URL.createObjectURL(blob);
        if (currentObjectUrlRef.current) {
          URL.revokeObjectURL(currentObjectUrlRef.current);
        }
        currentObjectUrlRef.current = newUrl;
        setBlobUrl(newUrl);
      } catch (e: any) {
        if (aborted) return;
        setError(e?.message || "Failed to load image");
        setBlobUrl(null);
      } finally {
        if (!aborted) setLoading(false);
      }
    }

    load();

    return () => {
      aborted = true;
      if (currentObjectUrlRef.current) {
        URL.revokeObjectURL(currentObjectUrlRef.current);
        currentObjectUrlRef.current = null;
      }
    };
  }, [imageUrl, tryDirectFirst, enableCache]);

  return { src: blobUrl, loading, error };
}


