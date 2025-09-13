"use client";

import { useState, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface FileUploadSectionProps {
  onFileUpload: (file: File, password?: string) => Promise<void>;
}

export function FileUploadSection({ onFileUpload }: FileUploadSectionProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState("");

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0 && files[0]) {
      validateAndSetFile(files[0]);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      validateAndSetFile(files[0]);
    }
  };

  const validateAndSetFile = (file: File) => {
    setError("");
    
    // Check file extension
    const allowedExtensions = ['.zip', '.rar', '.7z'];
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!allowedExtensions.includes(fileExtension)) {
      setError("Invalid file type. Only .zip, .rar, and .7z files are supported.");
      return;
    }
    
    // Check file size (max 100MB for demo)
    const maxSize = 100 * 1024 * 1024; // 100MB
    if (file.size > maxSize) {
      setError("File size too large. Maximum allowed size is 100MB.");
      return;
    }
    
    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    
    try {
      await onFileUpload(selectedFile, password || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent mb-4">
          Upload Stealer Archive
        </h2>
        <p className="text-purple-300 text-lg max-w-2xl mx-auto">
          Securely analyze infostealer malware logs to extract credentials, system information, 
          and browser cookies. Supports encrypted archives with password protection.
        </p>
      </div>

      <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-purple-100">File Upload</CardTitle>
          <CardDescription className="text-purple-300">
            Choose a stealer log archive file (.zip, .rar, .7z) to begin analysis
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Drag & Drop Area */}
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200 ${
              isDragOver
                ? "border-purple-400 bg-purple-500/10"
                : "border-purple-500/30 hover:border-purple-400 hover:bg-purple-500/5"
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                <span className="text-2xl">📁</span>
              </div>
              
              {!selectedFile ? (
                <>
                  <div>
                    <p className="text-purple-200 text-lg font-medium">
                      Drag and drop your archive here
                    </p>
                    <p className="text-purple-400 text-sm mt-1">
                      or click to browse files
                    </p>
                  </div>
                  
                  <div className="flex flex-wrap gap-2 justify-center text-xs text-purple-400">
                    <span className="px-2 py-1 bg-purple-500/20 rounded">.zip</span>
                    <span className="px-2 py-1 bg-purple-500/20 rounded">.rar</span>
                    <span className="px-2 py-1 bg-purple-500/20 rounded">.7z</span>
                  </div>
                </>
              ) : (
                <div className="space-y-2">
                  <p className="text-green-400 font-medium">File Selected</p>
                  <p className="text-purple-200">{selectedFile.name}</p>
                  <p className="text-purple-400 text-sm">
                    Size: {formatFileSize(selectedFile.size)}
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedFile(null)}
                    className="border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
                  >
                    Remove File
                  </Button>
                </div>
              )}
            </div>
            
            <input
              type="file"
              accept=".zip,.rar,.7z"
              onChange={handleFileSelect}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
          </div>

          {/* Password Input */}
          <div className="space-y-2">
            <Label htmlFor="password" className="text-purple-200">
              Archive Password (Optional)
            </Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password if archive is encrypted"
              className="bg-black/20 border-purple-500/30 text-purple-100 placeholder-purple-400 focus:border-purple-400"
            />
            <p className="text-xs text-purple-400">
              Leave empty if archive is not password protected
            </p>
          </div>

          {/* Error Display */}
          {error && (
            <Alert className="border-red-500/50 bg-red-500/10">
              <AlertDescription className="text-red-300">
                {error}
              </AlertDescription>
            </Alert>
          )}

          {/* Upload Button */}
          <Button
            onClick={handleUpload}
            disabled={!selectedFile}
            className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white font-medium py-3"
          >
            {selectedFile ? "Begin Analysis" : "Select a File to Continue"}
          </Button>

          {/* Info Section */}
          <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4">
            <h3 className="text-purple-200 font-medium mb-2">Supported Features</h3>
            <ul className="space-y-1 text-sm text-purple-300">
              <li>• Extract credentials from major browsers (Chrome, Firefox, Edge)</li>
              <li>• Parse system information and machine details</li>
              <li>• Analyze browser cookies and session data</li>
              <li>• Identify stealer malware variants</li>
              <li>• Generate comprehensive security reports</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}