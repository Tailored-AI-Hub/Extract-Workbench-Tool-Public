'use client'

import React from 'react';
import { Button } from "../../../components/ui/button";
import { Badge } from "../../../components/ui/badge";
import { Label } from "../../../components/ui/label";
import { X } from "lucide-react";

interface ExtractionKey {
  id: string;
  type: "key-value" | "value" | "image";
  keyName: string;
  dataType: string;
  description?: string;
  imageFile?: File;
  location?: string;
}

interface ExtractionKeyListProps {
  keys: ExtractionKey[];
  onRemoveKey: (keyId: string) => void;
}

export function ExtractionKeyList({ keys, onRemoveKey }: ExtractionKeyListProps) {
  if (keys.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <Label>Added Keys ({keys.length})</Label>
      <div className="space-y-2">
        {keys.map((key) => (
          <div
            key={key.id}
            className="flex items-start justify-between p-3 rounded-lg border border-border bg-background"
          >
            <div className="space-y-1 flex-1">
              <div className="flex items-center gap-2">
                <Badge variant="outline">{key.type}</Badge>
                <span className="font-medium">{key.keyName}</span>
              </div>
              <div className="text-sm text-muted-foreground space-y-0.5">
                <div>Data Type: {key.dataType}</div>
                {key.description && <div>Description: {key.description}</div>}
                {key.imageFile && <div>Image: {key.imageFile.name}</div>}
                {key.location && <div>Location: {key.location}</div>}
              </div>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => onRemoveKey(key.id)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}

