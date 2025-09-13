"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { CredentialsTable } from "@/components/CredentialsTable";
import { SystemInfo } from "@/components/SystemInfo";
import { CookiesTable } from "@/components/CookiesTable";
import { AnalyticsOverview } from "@/components/AnalyticsOverview";

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

interface AnalysisDashboardProps {
  data: ParsedData;
  onReset: () => void;
}

export function AnalysisDashboard({ data, onReset }: AnalysisDashboardProps) {
  const [activeTab, setActiveTab] = useState("overview");

  // Calculate summary statistics
  const totalSystems = data.systems_data.length;
  const totalCredentials = data.systems_data.reduce((sum, system) => sum + system.credentials.length, 0);
  const totalCookies = data.systems_data.reduce((sum, system) => sum + system.cookies.length, 0);
  
  // Get unique domains and services
  const uniqueDomains = new Set<string>();
  const uniqueSoftware = new Set<string>();
  const stealerTypes = new Set<string>();
  
  data.systems_data.forEach(system => {
    system.credentials.forEach(cred => {
      if (cred.domain) uniqueDomains.add(cred.domain);
      if (cred.software) uniqueSoftware.add(cred.software);
      if (cred.stealer_name) stealerTypes.add(cred.stealer_name);
    });
    system.cookies.forEach(cookie => {
      uniqueDomains.add(cookie.domain);
      if (cookie.stealer_name) stealerTypes.add(cookie.stealer_name);
    });
  });

  const handleExport = (format: string) => {
    let content: string;
    let filename: string;
    let mimeType: string;

    switch (format) {
      case 'json':
        content = JSON.stringify(data, null, 2);
        filename = `${data.filename}_analysis.json`;
        mimeType = 'application/json';
        break;
      case 'csv':
        // Simple CSV export of credentials
        const csvRows = ['Software,Host,Username,Password,Domain,Stealer'];
        data.systems_data.forEach(system => {
          system.credentials.forEach(cred => {
            csvRows.push([
              cred.software || '',
              cred.host || '',
              cred.username || '',
              cred.password || '',
              cred.domain || '',
              cred.stealer_name || ''
            ].map(field => `"${field}"`).join(','));
          });
        });
        content = csvRows.join('\n');
        filename = `${data.filename}_credentials.csv`;
        mimeType = 'text/csv';
        break;
      default:
        return;
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            Analysis Results
          </h2>
          <p className="text-purple-300 mt-2">
            Analysis complete for: <span className="text-purple-100 font-medium">{data.filename}</span>
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            onClick={() => handleExport('json')}
            className="border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
          >
            Export JSON
          </Button>
          <Button
            variant="outline"
            onClick={() => handleExport('csv')}
            className="border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
          >
            Export CSV
          </Button>
          <Button
            variant="outline"
            onClick={onReset}
            className="border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
          >
            New Analysis
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-purple-300">Compromised Systems</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-100">{totalSystems}</div>
            <p className="text-xs text-purple-400 mt-1">Unique machines identified</p>
          </CardContent>
        </Card>

        <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-purple-300">Total Credentials</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-100">{totalCredentials}</div>
            <p className="text-xs text-purple-400 mt-1">Passwords and logins found</p>
          </CardContent>
        </Card>

        <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-purple-300">Browser Cookies</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-100">{totalCookies}</div>
            <p className="text-xs text-purple-400 mt-1">Session tokens extracted</p>
          </CardContent>
        </Card>

        <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-purple-300">Unique Domains</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-100">{uniqueDomains.size}</div>
            <p className="text-xs text-purple-400 mt-1">Services compromised</p>
          </CardContent>
        </Card>
      </div>

      {/* Stealer Information */}
      {stealerTypes.size > 0 && (
        <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-purple-100">Detected Stealer Malware</CardTitle>
            <CardDescription className="text-purple-300">
              Identified information stealer variants in this archive
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {Array.from(stealerTypes).map((stealer, index) => (
                <Badge 
                  key={`stealer-${index}`}
                  variant="outline"
                  className="border-red-500/30 text-red-300 bg-red-500/10"
                >
                  {String(stealer)}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-black/40 border border-purple-500/20">
          <TabsTrigger value="overview" className="data-[state=active]:bg-purple-500/20">
            Overview
          </TabsTrigger>
          <TabsTrigger value="credentials" className="data-[state=active]:bg-purple-500/20">
            Credentials ({totalCredentials})
          </TabsTrigger>
          <TabsTrigger value="systems" className="data-[state=active]:bg-purple-500/20">
            Systems ({totalSystems})
          </TabsTrigger>
          <TabsTrigger value="cookies" className="data-[state=active]:bg-purple-500/20">
            Cookies ({totalCookies})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <AnalyticsOverview 
            data={data}
            uniqueDomains={Array.from(uniqueDomains)}
            uniqueSoftware={Array.from(uniqueSoftware)}
            stealerTypes={Array.from(stealerTypes)}
          />
        </TabsContent>

        <TabsContent value="credentials">
          <CredentialsTable data={data} />
        </TabsContent>

        <TabsContent value="systems">
          <SystemInfo data={data} />
        </TabsContent>

        <TabsContent value="cookies">
          <CookiesTable data={data} />
        </TabsContent>
      </Tabs>
    </div>
  );
}