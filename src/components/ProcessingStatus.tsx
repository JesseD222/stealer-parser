"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface ProcessingStatusProps {
  progress: number;
  currentStep: string;
  error?: string;
}

export function ProcessingStatus({ progress, currentStep, error }: ProcessingStatusProps) {
  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <Card className="bg-black/40 border-red-500/20 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-red-400 flex items-center space-x-2">
              <span className="text-2xl">❌</span>
              <span>Processing Failed</span>
            </CardTitle>
            <CardDescription className="text-red-300">
              An error occurred while processing the archive
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Alert className="border-red-500/50 bg-red-500/10">
              <AlertDescription className="text-red-300">
                {error}
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
        <CardHeader className="text-center">
          <CardTitle className="text-purple-100 flex items-center justify-center space-x-3">
            <div className="w-8 h-8 border-2 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
            <span>Processing Archive</span>
          </CardTitle>
          <CardDescription className="text-purple-300">
            Analyzing stealer logs and extracting data...
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-purple-300">Progress</span>
              <span className="text-purple-200 font-medium">{Math.round(progress)}%</span>
            </div>
            <Progress 
              value={progress} 
              className="h-3 bg-purple-900/20"
            />
          </div>

          {/* Current Step */}
          <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4">
            <div className="flex items-center space-x-3">
              <div className="w-6 h-6 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
              </div>
              <div>
                <p className="text-purple-200 font-medium">Current Step</p>
                <p className="text-purple-100 text-sm">{currentStep}</p>
              </div>
            </div>
          </div>

          {/* Processing Steps Overview */}
          <div className="space-y-3">
            <h3 className="text-purple-200 font-medium text-sm">Processing Pipeline</h3>
            <div className="grid grid-cols-1 gap-2 text-xs">
              {[
                { step: "File Upload", desc: "Receiving and validating archive" },
                { step: "Archive Extraction", desc: "Decompressing archive contents" },
                { step: "File Scanning", desc: "Identifying log files and structure" },
                { step: "Credential Parsing", desc: "Extracting saved passwords and logins" },
                { step: "System Analysis", desc: "Processing machine and user data" },
                { step: "Cookie Processing", desc: "Analyzing browser session data" },
                { step: "Report Generation", desc: "Compiling results and statistics" },
              ].map((item, index) => {
                const stepProgress = (index + 1) * (100 / 7);
                const isCompleted = progress > stepProgress;
                const isCurrent = progress >= (index * (100 / 7)) && progress < stepProgress;
                
                return (
                  <div 
                    key={index}
                    className={`flex items-center space-x-3 p-2 rounded ${
                      isCompleted 
                        ? "bg-green-500/10 border border-green-500/20" 
                        : isCurrent
                        ? "bg-purple-500/10 border border-purple-500/20"
                        : "bg-gray-500/10 border border-gray-500/20"
                    }`}
                  >
                    <div className={`w-4 h-4 rounded-full flex items-center justify-center ${
                      isCompleted 
                        ? "bg-green-500" 
                        : isCurrent
                        ? "bg-purple-500 animate-pulse"
                        : "bg-gray-500"
                    }`}>
                      {isCompleted && <span className="text-white text-xs">✓</span>}
                    </div>
                    <div className="flex-1">
                      <p className={`font-medium ${
                        isCompleted 
                          ? "text-green-300" 
                          : isCurrent
                          ? "text-purple-200"
                          : "text-gray-400"
                      }`}>
                        {item.step}
                      </p>
                      <p className={`text-xs ${
                        isCompleted 
                          ? "text-green-400" 
                          : isCurrent
                          ? "text-purple-300"
                          : "text-gray-500"
                      }`}>
                        {item.desc}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Security Notice */}
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
            <div className="flex items-center space-x-2">
              <span className="text-amber-400">🔒</span>
              <p className="text-amber-200 text-sm">
                Processing in secure sandboxed environment
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}