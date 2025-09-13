"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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

interface CredentialsTableProps {
  data: ParsedData;
}

export function CredentialsTable({ data }: CredentialsTableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [showPasswords, setShowPasswords] = useState(false);

  // Flatten all credentials from all systems
  const allCredentials: Array<{
    software?: string;
    host?: string;
    username?: string;
    password?: string;
    domain?: string;
    local_part?: string;
    email_domain?: string;
    filepath?: string;
    stealer_name?: string;
    systemIndex: number;
    credIndex: number;
    systemName: string;
  }> = [];
  
  data.systems_data.forEach((system, systemIndex) => {
    system.credentials.forEach((cred, credIndex) => {
      allCredentials.push({
        ...cred,
        systemIndex,
        credIndex,
        systemName: system.system?.computer_name || `System ${systemIndex + 1}`,
      });
    });
  });

  // Filter credentials based on search term
  const filteredCredentials = allCredentials.filter((cred) => {
    const searchLower = searchTerm.toLowerCase();
    return (
      (cred.software?.toLowerCase().includes(searchLower) || false) ||
      (cred.host?.toLowerCase().includes(searchLower) || false) ||
      (cred.username?.toLowerCase().includes(searchLower) || false) ||
      (cred.domain?.toLowerCase().includes(searchLower) || false) ||
      (cred.stealer_name?.toLowerCase().includes(searchLower) || false) ||
      (cred.systemName.toLowerCase().includes(searchLower))
    );
  });

  const getRiskLevel = (domain?: string) => {
    if (!domain) return "low";
    
    const highRiskDomains = [
      "gmail.com", "outlook.com", "yahoo.com", "facebook.com", "twitter.com",
      "linkedin.com", "instagram.com", "apple.com", "microsoft.com", "google.com",
      "amazon.com", "paypal.com", "bank", "banking"
    ];
    
    const isHighRisk = highRiskDomains.some(risky => 
      domain.toLowerCase().includes(risky)
    );
    
    return isHighRisk ? "high" : "medium";
  };

  return (
    <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
      <CardHeader>
        <CardTitle className="text-purple-100">Extracted Credentials</CardTitle>
        <CardDescription className="text-purple-300">
          All credentials found across compromised systems ({filteredCredentials.length} total)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Search and Controls */}
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <Input
              placeholder="Search by domain, software, username..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-black/20 border-purple-500/30 text-purple-100 placeholder-purple-400"
            />
          </div>
          <Button
            variant={showPasswords ? "default" : "outline"}
            onClick={() => setShowPasswords(!showPasswords)}
            className={showPasswords 
              ? "bg-purple-500 hover:bg-purple-600" 
              : "border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
            }
          >
            {showPasswords ? "Hide" : "Show"} Passwords
          </Button>
        </div>

        {/* Credentials Table */}
        <div className="rounded-lg border border-purple-500/20 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-purple-500/20 bg-purple-500/5">
                <TableHead className="text-purple-300">System</TableHead>
                <TableHead className="text-purple-300">Software</TableHead>
                <TableHead className="text-purple-300">Domain</TableHead>
                <TableHead className="text-purple-300">Username</TableHead>
                <TableHead className="text-purple-300">Password</TableHead>
                <TableHead className="text-purple-300">Risk</TableHead>
                <TableHead className="text-purple-300">Stealer</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCredentials.length === 0 ? (
                <TableRow>
                  <TableCell 
                    colSpan={7} 
                    className="text-center text-purple-400 py-8"
                  >
                    {searchTerm ? "No credentials match your search" : "No credentials found"}
                  </TableCell>
                </TableRow>
              ) : (
                filteredCredentials.map((cred, index) => {
                  const riskLevel = getRiskLevel(cred.domain);
                  
                  return (
                    <TableRow 
                      key={`${cred.systemIndex}-${cred.credIndex}-${index}`}
                      className="border-purple-500/10 hover:bg-purple-500/5"
                    >
                      <TableCell className="text-purple-200 font-medium">
                        {cred.systemName}
                      </TableCell>
                      
                      <TableCell>
                        <Badge 
                          variant="outline" 
                          className="border-blue-500/30 text-blue-300 bg-blue-500/10"
                        >
                          {cred.software || "Unknown"}
                        </Badge>
                      </TableCell>
                      
                      <TableCell className="text-purple-200">
                        {cred.domain || cred.host || "N/A"}
                      </TableCell>
                      
                      <TableCell className="text-purple-200 font-mono text-sm">
                        {cred.username || "N/A"}
                      </TableCell>
                      
                      <TableCell className="font-mono text-sm">
                        {cred.password ? (
                          showPasswords ? (
                            <span className="text-purple-200 bg-purple-900/20 px-2 py-1 rounded">
                              {cred.password}
                            </span>
                          ) : (
                            <span className="text-purple-400">••••••••</span>
                          )
                        ) : (
                          <span className="text-purple-500">N/A</span>
                        )}
                      </TableCell>
                      
                      <TableCell>
                        <Badge 
                          variant="outline"
                          className={
                            riskLevel === "high" 
                              ? "border-red-500/30 text-red-300 bg-red-500/10"
                              : riskLevel === "medium"
                              ? "border-amber-500/30 text-amber-300 bg-amber-500/10"
                              : "border-green-500/30 text-green-300 bg-green-500/10"
                          }
                        >
                          {riskLevel.toUpperCase()}
                        </Badge>
                      </TableCell>
                      
                      <TableCell>
                        {cred.stealer_name && (
                          <Badge 
                            variant="outline" 
                            className="border-red-500/30 text-red-300 bg-red-500/10"
                          >
                            {cred.stealer_name}
                          </Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>

        {/* Summary Stats */}
        {filteredCredentials.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
              <div className="text-lg font-bold text-red-300">
                {filteredCredentials.filter(c => getRiskLevel(c.domain) === "high").length}
              </div>
              <div className="text-sm text-red-400">High Risk Credentials</div>
            </div>
            
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4">
              <div className="text-lg font-bold text-amber-300">
                {filteredCredentials.filter(c => getRiskLevel(c.domain) === "medium").length}
              </div>
              <div className="text-sm text-amber-400">Medium Risk Credentials</div>
            </div>
            
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
              <div className="text-lg font-bold text-green-300">
                {filteredCredentials.filter(c => getRiskLevel(c.domain) === "low").length}
              </div>
              <div className="text-sm text-green-400">Low Risk Credentials</div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}