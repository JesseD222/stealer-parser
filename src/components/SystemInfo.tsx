"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

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

interface SystemInfoProps {
  data: ParsedData;
}

export function SystemInfo({ data }: SystemInfoProps) {
  const formatDate = (dateString?: string) => {
    if (!dateString) return "Unknown";
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const getCountryFlag = (countryCode?: string) => {
    if (!countryCode) return "🌍";
    
    const flags: Record<string, string> = {
      "US": "🇺🇸", "GB": "🇬🇧", "CA": "🇨🇦", "DE": "🇩🇪", "FR": "🇫🇷",
      "IT": "🇮🇹", "ES": "🇪🇸", "JP": "🇯🇵", "KR": "🇰🇷", "CN": "🇨🇳",
      "RU": "🇷🇺", "BR": "🇧🇷", "IN": "🇮🇳", "AU": "🇦🇺", "NL": "🇳🇱",
      "SE": "🇸🇪", "NO": "🇳🇴", "DK": "🇩🇰", "FI": "🇫🇮", "PL": "🇵🇱"
    };
    
    return flags[countryCode.toUpperCase()] || "🌍";
  };

  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <h3 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
          Compromised Systems Analysis
        </h3>
        <p className="text-purple-300 mt-2">
          Detailed information about each compromised machine
        </p>
      </div>

      <div className="grid gap-6">
        {data.systems_data.map((systemData, index) => {
          const system = systemData.system;
          const credentialsCount = systemData.credentials.length;
          const cookiesCount = systemData.cookies.length;
          
          return (
            <Card key={index} className="bg-black/40 border-purple-500/20 backdrop-blur-md">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-purple-100 flex items-center space-x-2">
                      <span className="text-2xl">💻</span>
                      <span>{system?.computer_name || `System ${index + 1}`}</span>
                    </CardTitle>
                    <CardDescription className="text-purple-300 mt-1">
                      {credentialsCount} credentials • {cookiesCount} cookies
                    </CardDescription>
                  </div>
                  <div className="flex items-center space-x-2">
                    {system?.country && (
                      <Badge variant="outline" className="border-purple-500/30 text-purple-300">
                        {getCountryFlag(system.country)} {system.country}
                      </Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              
              <CardContent className="space-y-6">
                {/* System Details Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-4">
                    <h4 className="text-purple-200 font-medium border-b border-purple-500/20 pb-2">
                      Machine Information
                    </h4>
                    
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-purple-400 text-sm">Computer Name:</span>
                        <span className="text-purple-100 font-mono text-sm">
                          {system?.computer_name || "Unknown"}
                        </span>
                      </div>
                      
                      <div className="flex justify-between items-center">
                        <span className="text-purple-400 text-sm">Machine User:</span>
                        <span className="text-purple-100 font-mono text-sm">
                          {system?.machine_user || "Unknown"}
                        </span>
                      </div>
                      
                      <div className="flex justify-between items-center">
                        <span className="text-purple-400 text-sm">IP Address:</span>
                        <span className="text-purple-100 font-mono text-sm">
                          {system?.ip_address || "Unknown"}
                        </span>
                      </div>
                      
                      <div className="flex justify-between items-center">
                        <span className="text-purple-400 text-sm">Country:</span>
                        <span className="text-purple-100 text-sm">
                          {system?.country ? (
                            <span className="flex items-center space-x-1">
                              <span>{getCountryFlag(system.country)}</span>
                              <span>{system.country}</span>
                            </span>
                          ) : (
                            "Unknown"
                          )}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <h4 className="text-purple-200 font-medium border-b border-purple-500/20 pb-2">
                      System Identifiers
                    </h4>
                    
                    <div className="space-y-3">
                      <div className="flex justify-between items-start">
                        <span className="text-purple-400 text-sm">Machine ID:</span>
                        <span className="text-purple-100 font-mono text-xs text-right max-w-48 truncate">
                          {system?.machine_id || "Unknown"}
                        </span>
                      </div>
                      
                      <div className="flex justify-between items-start">
                        <span className="text-purple-400 text-sm">Hardware ID:</span>
                        <span className="text-purple-100 font-mono text-xs text-right max-w-48 truncate">
                          {system?.hardware_id || "Unknown"}
                        </span>
                      </div>
                      
                      <div className="flex justify-between items-center">
                        <span className="text-purple-400 text-sm">Log Date:</span>
                        <span className="text-purple-100 text-sm">
                          {formatDate(system?.log_date)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Data Summary */}
                <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4">
                  <h4 className="text-purple-200 font-medium mb-3">Extracted Data Summary</h4>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-100">{credentialsCount}</div>
                      <div className="text-xs text-purple-400">Credentials</div>
                    </div>
                    
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-100">{cookiesCount}</div>
                      <div className="text-xs text-purple-400">Cookies</div>
                    </div>
                    
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-100">
                        {new Set(systemData.credentials.map(c => c.software).filter(Boolean)).size}
                      </div>
                      <div className="text-xs text-purple-400">Software</div>
                    </div>
                    
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-100">
                        {new Set(systemData.credentials.map(c => c.domain).filter(Boolean)).size}
                      </div>
                      <div className="text-xs text-purple-400">Domains</div>
                    </div>
                  </div>
                </div>

                {/* Detected Software */}
                {systemData.credentials.length > 0 && (
                  <div>
                    <h4 className="text-purple-200 font-medium mb-3">Compromised Software</h4>
                    <div className="flex flex-wrap gap-2">
                      {Array.from(new Set(systemData.credentials.map(c => c.software).filter(Boolean)))
                        .map((software) => (
                          <Badge 
                            key={software} 
                            variant="outline"
                            className="border-blue-500/30 text-blue-300 bg-blue-500/10"
                          >
                            {software}
                          </Badge>
                        ))
                      }
                    </div>
                  </div>
                )}

                {/* Risk Assessment */}
                <div className="bg-gradient-to-r from-red-500/10 to-amber-500/10 border border-red-500/20 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="text-red-400">🚨</span>
                    <span className="text-red-300 font-medium">Security Impact Assessment</span>
                  </div>
                  
                  <div className="text-sm text-red-200 space-y-1">
                    <p>• Machine compromised with {credentialsCount} extracted credentials</p>
                    <p>• {cookiesCount} browser cookies potentially exposing active sessions</p>
                    <p>• {Array.from(new Set(systemData.credentials.map(c => c.domain).filter(Boolean))).length} unique services at risk</p>
                    {system?.ip_address && (
                      <p>• Network location: {system.ip_address} ({system?.country || "Unknown location"})</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}