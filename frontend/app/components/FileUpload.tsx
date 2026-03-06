"use client";

import { useState, useRef } from "react";
import { createClient } from "@/lib/supabase/client";
import { BACKEND_URL } from "@/lib/backend";
import type { DocumentRef } from "@/lib/api-types";
import { Button } from "@/components/ui/button";
import { Upload, Loader2 } from "lucide-react";

// Security: File size limit (10MB)
const MAX_FILE_SIZE_MB = 10;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

interface FileUploadProps {
  conversationId: string;
  onFileUploaded: (document: { documentId: string; url: string; filename: string }) => void;
  disabled?: boolean;
}

export function FileUpload({ conversationId, onFileUploaded, disabled }: FileUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Security: Validate file size before upload
    if (file.size > MAX_FILE_SIZE_BYTES) {
      alert(`File too large. Maximum size is ${MAX_FILE_SIZE_MB}MB.`);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    setIsUploading(true);

    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error("Authentication required");
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("conversation_id", conversationId);

      const response = await fetch(`${BACKEND_URL}/api/v1/documents/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
        body: formData,
      });

      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail || "Failed to upload file");
      }

      const document: DocumentRef = payload;
      onFileUploaded({
        documentId: document.document_id,
        url: document.document_url,
        filename: document.filename || file.name,
      });
    } catch (error) {
      console.error("Upload error:", error);
      alert(error instanceof Error ? error.message : "Failed to upload file");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="w-full">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
        onChange={handleFileChange}
        className="hidden"
        disabled={disabled || isUploading}
      />

      <Button
        variant="outline"
        onClick={handleClick}
        disabled={disabled || isUploading}
        className="w-full h-12 text-sm border-dashed border-slate-300 text-slate-500 hover:text-slate-700 hover:border-slate-400 hover:bg-slate-50"
      >
        {isUploading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Uploading...
          </>
        ) : (
          <>
            <Upload className="mr-2 h-4 w-4" />
            Upload Document
          </>
        )}
      </Button>
    </div>
  );
}
