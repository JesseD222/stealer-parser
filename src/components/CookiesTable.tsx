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

interface CookiesTableProps {
  data: ParsedData;
}

export function CookiesTable({ data }: CookiesTableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [showValues, setShowValues] = useState(false);

  // Flatten all cookies from all systems
  const allCookies: Array<{
    domain: string;
    name: string;
    value: string;
    browser?: string;
    secure: boolean;
    expiry: string;
    filepath?: string;
    stealer_name?: string;
    systemIndex: number;
    cookieIndex: number;
    systemName: string;
  }> = [];
  
  data.systems_data.forEach((system, systemIndex) => {
    system.cookies.forEach((cookie, cookieIndex) => {
      allCookies.push({
        ...cookie,
        systemIndex,
        cookieIndex,
        systemName: system.system?.computer_name || `System ${systemIndex + 1}`,
      });
    });
  });

  // Filter cookies based on search term
  const filteredCookies = allCookies.filter((cookie) => {
    const searchLower = searchTerm.toLowerCase();
    return (
      cookie.domain.toLowerCase().includes(searchLower) ||
      cookie.name.toLowerCase().includes(searchLower) ||
      (cookie.browser?.toLowerCase().includes(searchLower) || false) ||
      (cookie.stealer_name?.toLowerCase().includes(searchLower) || false) ||
      cookie.systemName.toLowerCase().includes(searchLower)
    );
  });

  const formatExpiry = (expiryString: string) => {
    try {
      const date = new Date(expiryString);
      return date.toLocaleString();
    } catch {
      return expiryString;
    }
  };

  const isExpired = (expiryString: string) => {
    try {
      const expiry = new Date(expiryString);
      return expiry < new Date();
    } catch {
      return false;
    }
  };

  const getDomainCategory = (domain: string) => {
    const categories = {
      social: ["facebook.com", "twitter.com", "instagram.com", "linkedin.com", "tiktok.com"],
      email: ["gmail.com", "outlook.com", "yahoo.com", "protonmail.com"],
      financial: ["paypal.com", "stripe.com", "bank", "banking"],
      cloud: ["google.com", "microsoft.com", "apple.com", "amazon.com", "dropbox.com"],
      shopping: ["amazon.com", "ebay.com", "shopify.com", "etsy.com"]
    };

    for (const [category, domains] of Object.entries(categories)) {
      if (domains.some(d => domain.toLowerCase().includes(d))) {
        return category;
      }
    }
    return "other";
  };

  const getCategoryColor = (category: string) => {
    const colors = {
      social: "border-blue-500/30 text-blue-300 bg-blue-500/10",
      email: "border-green-500/30 text-green-300 bg-green-500/10",
      financial: "border-red-500/30 text-red-300 bg-red-500/10",
      cloud: "border-purple-500/30 text-purple-300 bg-purple-500/10",
      shopping: "border-amber-500/30 text-amber-300 bg-amber-500/10",
      other: "border-gray-500/30 text-gray-300 bg-gray-500/10"
    };
    return colors[category as keyof typeof colors] || colors.other;
  };

  return (
    <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
      <CardHeader>
        <CardTitle className="text-purple-100">Browser Cookies</CardTitle>
        <CardDescription className="text-purple-300">
          Session data and stored cookies from compromised browsers ({filteredCookies.length} total)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Search and Controls */}
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <Input
              placeholder="Search by domain, name, browser..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-black/20 border-purple-500/30 text-purple-100 placeholder-purple-400"
            />
          </div>
          <Button
            variant={showValues ? "default" : "outline"}
            onClick={() => setShowValues(!showValues)}
            className={showValues 
              ? "bg-purple-500 hover:bg-purple-600" 
              : "border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
            }
          >
            {showValues ? "Hide" : "Show"} Values
          </Button>
        </div>

        {/* Cookies Table */}
        <div className="rounded-lg border border-purple-500/20 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-purple-500/20 bg-purple-500/5">
                <TableHead className="text-purple-300">System</TableHead>
                <TableHead className="text-purple-300">Domain</TableHead>
                <TableHead className="text-purple-300">Cookie Name</TableHead>
                <TableHead className="text-purple-300">Value</TableHead>
                <TableHead className="text-purple-300">Browser</TableHead>
                <TableHead className="text-purple-300">Security</TableHead>
                <TableHead className="text-purple-300">Expiry</TableHead>
                <TableHead className="text-purple-300">Category</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCookies.length === 0 ? (
                <TableRow>
                  <TableCell 
                    colSpan={8} 
                    className="text-center text-purple-400 py-8"
                  >
                    {searchTerm ? "No cookies match your search" : "No cookies found"}
                  </TableCell>
                </TableRow>
              ) : (
                filteredCookies.map((cookie, index) => {
                  const category = getDomainCategory(cookie.domain);
                  const expired = isExpired(cookie.expiry);
                  
                  return (
                    <TableRow 
                      key={`${cookie.systemIndex}-${cookie.cookieIndex}-${index}`}
                      className="border-purple-500/10 hover:bg-purple-500/5"
                    >
                      <TableCell className="text-purple-200 font-medium">
                        {cookie.systemName}
                      </TableCell>
                      
                      <TableCell className="text-purple-200 font-mono text-sm">
                        {cookie.domain}
                      </TableCell>
                      
                      <TableCell className="text-purple-200 font-mono text-sm">
                        {cookie.name}
                      </TableCell>
                      
                      <TableCell className="font-mono text-sm max-w-32">
                        {showValues ? (
                          <div className="text-purple-200 bg-purple-900/20 px-2 py-1 rounded truncate">
                            {cookie.value}
                          </div>
                        ) : (
                          <span className="text-purple-400">••••••••</span>
                        )}
                      </TableCell>
                      
                      <TableCell>
                        {cookie.browser && (
                          <Badge 
                            variant="outline" 
                            className="border-blue-500/30 text-blue-300 bg-blue-500/10"
                          >
                            {cookie.browser}
                          </Badge>
                        )}
                      </TableCell>
                      
                      <TableCell>
                        <div className="flex flex-col space-y-1">
                          <Badge 
                            variant="outline"
                            className={cookie.secure 
                              ? "border-green-500/30 text-green-300 bg-green-500/10" 
                              : "border-amber-500/30 text-amber-300 bg-amber-500/10"
                            }
                          >
                            {cookie.secure ? "Secure" : "Insecure"}
                          </Badge>
                        </div>
                      </TableCell>
                      
                      <TableCell className="text-sm">
                        <div className={`${expired ? "text-red-300" : "text-purple-200"}`}>
                          {formatExpiry(cookie.expiry)}
                        </div>
                        {expired && (
                          <Badge 
                            variant="outline" 
                            className="border-red-500/30 text-red-300 bg-red-500/10 text-xs mt-1"
                          >
                            Expired
                          </Badge>
                        )}
                      </TableCell>
                      
                      <TableCell>
                        <Badge 
                          variant="outline"
                          className={getCategoryColor(category)}
                        >
                          {category.charAt(0).toUpperCase() + category.slice(1)}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>

        {/* Summary Stats */}
        {filteredCookies.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
              <div className="text-lg font-bold text-green-300">
                {filteredCookies.filter(c => c.secure).length}
              </div>
              <div className="text-sm text-green-400">Secure Cookies</div>
            </div>
            
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4">
              <div className="text-lg font-bold text-amber-300">
                {filteredCookies.filter(c => !c.secure).length}
              </div>
              <div className="text-sm text-amber-400">Insecure Cookies</div>
            </div>
            
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
              <div className="text-lg font-bold text-red-300">
                {filteredCookies.filter(c => isExpired(c.expiry)).length}
              </div>
              <div className="text-sm text-red-400">Expired Cookies</div>
            </div>
            
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
              <div className="text-lg font-bold text-blue-300">
                {new Set(filteredCookies.map(c => c.domain)).size}
              </div>
              <div className="text-sm text-blue-400">Unique Domains</div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}