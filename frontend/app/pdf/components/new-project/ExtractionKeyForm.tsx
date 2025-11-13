'use client'

import React from 'react';
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../../components/ui/select";
import { Plus, X } from "lucide-react";

type ExtractionKeyType = "key-value" | "value" | "image";

interface ExtractionKeyFormProps {
  currentType: ExtractionKeyType;
  currentKeyName: string;
  currentDataType: string;
  currentDescription: string;
  currentImageFile: File | null;
  onTypeChange: (type: ExtractionKeyType) => void;
  onKeyNameChange: (name: string) => void;
  onDataTypeChange: (type: string) => void;
  onDescriptionChange: (desc: string) => void;
  onImageFileChange: (file: File | null) => void;
  onAddKey: () => void;
}

export function ExtractionKeyForm({
  currentType,
  currentKeyName,
  currentDataType,
  currentDescription,
  currentImageFile,
  onTypeChange,
  onKeyNameChange,
  onDataTypeChange,
  onDescriptionChange,
  onImageFileChange,
  onAddKey
}: ExtractionKeyFormProps) {
  return (
    <div className="space-y-4 p-4 rounded-lg border border-border bg-muted/30">
      {/* First Line: Type dropdown and Key Name input */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <Select value={currentType} onValueChange={(value) => onTypeChange(value as ExtractionKeyType)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="key-value">Key:Value</SelectItem>
              <SelectItem value="value">Value</SelectItem>
              <SelectItem value="image">Image</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex-1">
          <Input
            placeholder="Field name"
            value={currentKeyName}
            onChange={(e) => onKeyNameChange(e.target.value)}
          />
        </div>
        <div className="w-4 h-4 flex items-center justify-center">
          <span className="text-red-500 text-sm">*</span>
        </div>
      </div>

      {/* Second Line: Field Type dropdown and Description/Upload */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <Select value={currentDataType} onValueChange={onDataTypeChange}>
            <SelectTrigger>
              <SelectValue placeholder="Field type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="string">String</SelectItem>
              <SelectItem value="number">Number</SelectItem>
              <SelectItem value="boolean">Boolean</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex-1">
          {currentType === "image" ? (
            <div className="flex items-center gap-2">
              <Input
                type="file"
                accept="image/*"
                onChange={(e) => onImageFileChange(e.target.files?.[0] || null)}
                className="cursor-pointer"
              />
              {currentImageFile && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => onImageFileChange(null)}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          ) : (
            <Input
              placeholder="Field description"
              value={currentDescription}
              onChange={(e) => onDescriptionChange(e.target.value)}
            />
          )}
        </div>
        <div className="w-4 h-4 flex items-center justify-center">
          <span className="text-red-500 text-sm">*</span>
        </div>
      </div>

      <Button type="button" onClick={onAddKey} className="w-full">
        <Plus className="h-4 w-4 mr-2" />
        Add Extraction Key
      </Button>
    </div>
  );
}

