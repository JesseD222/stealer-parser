"use client";

import { useState } from "react";
import { FileUploadSection } from "@/components/FileUploadSection";
import { AnalysisDashboard } from "@/components/AnalysisDashboard";
import { Header } from "@/components/Header";
import { ProcessingStatus } from "@/components/ProcessingStatus";

interface ParsedData {
  filename: string;
  systems_data: Array<{
    system: {
      machine_id?: string;
      computer_name?: string;
      hardware_id?: string;
      machine_user?: string;
      ip_address?: string;
      country?: string;
      log_date?: string;
    } | null;
    credentials: Array<{
      software?: string;
      host?: string;
      username?: string;
      password?: string;
      domain?: string;
      local_part?: string;
      email_domain?: string;
      filepath?: string;
      stealer_name?: string;
    }>;
    cookies: Array<{
      domain: string;
      name: string;
      value: string;
      browser?: string;
      secure: boolean;
      expiry: string;
      filepath?: string;
      stealer_name?: string;
    }>;
  }>;
}

interface ProcessingState {
  isProcessing: boolean;
  progress: number;
  currentStep: string;
  error?: string;
}

export default function HomePage() {
  const [parsedData, setParsedData] = useState<ParsedData | null>(null);
  const [processingState, setProcessingState] = useState<ProcessingState>({
    isProcessing: false,
    progress: 0,
    currentStep: "",
  });

  const handleFileUpload = async (file: File, password?: string) => {
    setProcessingState({
      isProcessing: true,
      progress: 0,
      currentStep: "Uploading file...",
    });

    try {
      // Import API client dynamically to avoid SSR issues
      const { apiClient } = await import('@/lib/api');
      
      // Upload file and get job ID
      const { job_id } = await apiClient.uploadFile(file, password);
      
      // Poll for status updates
      let jobCompleted = false;
      let attempts = 0;
      const maxAttempts = 300; // 5 minutes max
      
      while (!jobCompleted && attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
        
        try {
          const status = await apiClient.getJobStatus(job_id);
          
          setProcessingState({
            isProcessing: status.status === 'processing' || status.status === 'pending',
            progress: status.progress,
            currentStep: status.current_step,
            error: status.error,
          });
          
          if (status.status === 'completed') {
            // Get the result
            const result = await apiClient.getJobResult(job_id);
            setParsedData(result);
            jobCompleted = true;
            
            // Clean up job
            await apiClient.deleteJob(job_id);
            
          } else if (status.status === 'failed') {
            throw new Error(status.error || 'Processing failed');
          }
          
        } catch (statusError) {
          console.error('Status check error:', statusError);
          // Continue polling unless it's a critical error
        }
        
        attempts++;
      }
      
      if (!jobCompleted) {
        throw new Error('Processing timeout - job took too long to complete');
      }
      
    } catch (error) {
      console.error('Upload error:', error);
      setProcessingState({
        isProcessing: false,
        progress: 0,
        currentStep: "",
        error: error instanceof Error ? error.message : "Unknown error occurred",
      });
    }
  };

  const handleReset = () => {
    setParsedData(null);
    setProcessingState({
      isProcessing: false,
      progress: 0,
      currentStep: "",
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="min-h-screen bg-black/20 backdrop-blur-sm">
        <Header />
        
        <main className="container mx-auto px-4 py-8">
          {!parsedData && !processingState.isProcessing && (
            <FileUploadSection onFileUpload={handleFileUpload} />
          )}

          {processingState.isProcessing && (
            <ProcessingStatus
              progress={processingState.progress}
              currentStep={processingState.currentStep}
              error={processingState.error}
            />
          )}

          {parsedData && !processingState.isProcessing && (
            <AnalysisDashboard 
              data={parsedData} 
              onReset={handleReset}
            />
          )}
        </main>

        <footer className="border-t border-purple-500/20 mt-16 py-8">
          <div className="container mx-auto px-4 text-center text-purple-300">
            <p className="text-sm">
              Stealer Data Record Parser - Advanced Security Analysis Tool
            </p>
            <p className="text-xs mt-2 opacity-60">
              Safely analyze infostealer malware logs for security research
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
}