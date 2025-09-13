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

interface AnalyticsOverviewProps {
  data: ParsedData;
  uniqueDomains: string[];
  uniqueSoftware: string[];
  stealerTypes: string[];
}

export function AnalyticsOverview({ 
  data, 
  uniqueDomains, 
  stealerTypes 
}: AnalyticsOverviewProps) {
  // Calculate additional analytics
  const totalCredentials = data.systems_data.reduce((sum, system) => sum + system.credentials.length, 0);
  const totalCookies = data.systems_data.reduce((sum, system) => sum + system.cookies.length, 0);
  
  // Get country distribution
  const countryStats: Record<string, number> = {};
  data.systems_data.forEach(system => {
    const country = system.system?.country;
    if (country) {
      countryStats[country] = (countryStats[country] || 0) + 1;
    }
  });

  // Get domain risk analysis
  const highRiskDomains = [
    "gmail.com", "outlook.com", "yahoo.com", "facebook.com", "twitter.com",
    "linkedin.com", "instagram.com", "apple.com", "microsoft.com", "google.com",
    "amazon.com", "paypal.com", "bank", "banking"
  ];
  
  const riskAnalysis = uniqueDomains.reduce((acc, domain) => {
    const isHighRisk = highRiskDomains.some(risky => 
      domain.toLowerCase().includes(risky.toLowerCase())
    );
    if (isHighRisk) {
      acc.high++;
    } else {
      acc.medium++;
    }
    return acc;
  }, { high: 0, medium: 0 });

  // Get browser distribution
  const browserStats: Record<string, number> = {};
  data.systems_data.forEach(system => {
    system.credentials.forEach(cred => {
      if (cred.software) {
        browserStats[cred.software] = (browserStats[cred.software] || 0) + 1;
      }
    });
    system.cookies.forEach(cookie => {
      if (cookie.browser) {
        browserStats[cookie.browser] = (browserStats[cookie.browser] || 0) + 1;
      }
    });
  });

  const getCountryFlag = (countryCode: string) => {
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
      {/* Executive Summary */}
      <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-purple-100 flex items-center space-x-2">
            <span className="text-2xl">📊</span>
            <span>Executive Summary</span>
          </CardTitle>
          <CardDescription className="text-purple-300">
            High-level overview of the security breach impact
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-gradient-to-r from-red-500/10 to-orange-500/10 border border-red-500/20 rounded-lg p-4">
            <h3 className="text-red-300 font-bold text-lg mb-3">Security Impact Assessment</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <p className="text-red-200">
                  <span className="font-medium">Breach Scope:</span> {data.systems_data.length} compromised systems
                </p>
                <p className="text-red-200">
                  <span className="font-medium">Data Exposure:</span> {totalCredentials} credentials + {totalCookies} cookies
                </p>
                <p className="text-red-200">
                  <span className="font-medium">Services at Risk:</span> {uniqueDomains.length} unique domains
                </p>
              </div>
              <div className="space-y-2">
                <p className="text-red-200">
                  <span className="font-medium">High-Risk Domains:</span> {riskAnalysis.high} identified
                </p>
                <p className="text-red-200">
                  <span className="font-medium">Geographic Spread:</span> {Object.keys(countryStats).length} countries
                </p>
                <p className="text-red-200">
                  <span className="font-medium">Malware Variants:</span> {stealerTypes.length} types detected
                </p>
              </div>
            </div>
          </div>

          {stealerTypes.length > 0 && (
            <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4">
              <h4 className="text-purple-200 font-medium mb-2">Threat Attribution</h4>
              <div className="flex flex-wrap gap-2">
                {stealerTypes.map((stealer) => (
                  <Badge 
                    key={stealer}
                    variant="outline"
                    className="border-red-500/30 text-red-300 bg-red-500/10"
                  >
                    🦠 {stealer}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Geographic Distribution */}
      {Object.keys(countryStats).length > 0 && (
        <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-purple-100 flex items-center space-x-2">
              <span className="text-2xl">🌍</span>
              <span>Geographic Distribution</span>
            </CardTitle>
            <CardDescription className="text-purple-300">
              Compromised systems by country
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {Object.entries(countryStats)
                .sort(([,a], [,b]) => b - a)
                .map(([country, count]) => (
                  <div 
                    key={country} 
                    className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-3 text-center"
                  >
                    <div className="text-2xl mb-1">{getCountryFlag(country)}</div>
                    <div className="text-lg font-bold text-purple-100">{count}</div>
                    <div className="text-xs text-purple-400">{country}</div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Software & Browser Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-purple-100 flex items-center space-x-2">
              <span className="text-2xl">💾</span>
              <span>Compromised Software</span>
            </CardTitle>
            <CardDescription className="text-purple-300">
              Applications with extracted credentials
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(browserStats)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 8)
                .map(([software, count]) => (
                  <div key={software} className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Badge variant="outline" className="border-blue-500/30 text-blue-300 bg-blue-500/10">
                        {software}
                      </Badge>
                    </div>
                    <div className="text-purple-200 font-medium">{count} items</div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-purple-100 flex items-center space-x-2">
              <span className="text-2xl">🎯</span>
              <span>Risk Assessment</span>
            </CardTitle>
            <CardDescription className="text-purple-300">
              Domain categorization by risk level
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-3">
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-red-300 font-medium">High Risk Domains</div>
                    <div className="text-red-400 text-sm">Financial, email, social media</div>
                  </div>
                  <div className="text-2xl font-bold text-red-300">{riskAnalysis.high}</div>
                </div>
              </div>
              
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-amber-300 font-medium">Medium Risk Domains</div>
                    <div className="text-amber-400 text-sm">Other web services</div>
                  </div>
                  <div className="text-2xl font-bold text-amber-300">{riskAnalysis.medium}</div>
                </div>
              </div>
            </div>
            
            <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-3">
              <p className="text-purple-200 text-sm">
                <span className="font-medium">Impact:</span> High-risk domains require immediate password resets 
                and multi-factor authentication verification.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Compromised Domains */}
      <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-purple-100 flex items-center space-x-2">
            <span className="text-2xl">🔗</span>
            <span>Most Targeted Domains</span>
          </CardTitle>
          <CardDescription className="text-purple-300">
            Services with the highest credential exposure
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {uniqueDomains.slice(0, 12).map((domain, index) => {
              const credCount = data.systems_data.reduce((sum, system) => 
                sum + system.credentials.filter(cred => cred.domain === domain).length, 0
              );
              
              const isHighRisk = highRiskDomains.some(risky => 
                domain.toLowerCase().includes(risky.toLowerCase())
              );
              
              return (
                <div 
                  key={domain} 
                  className={`p-3 rounded-lg border ${
                    isHighRisk 
                      ? "bg-red-500/10 border-red-500/20" 
                      : "bg-purple-500/10 border-purple-500/20"
                  }`}
                >
                  <div className="text-purple-200 font-medium text-sm truncate">
                    {domain}
                  </div>
                  <div className="text-xs text-purple-400 mt-1">
                    {credCount} credentials
                  </div>
                  {isHighRisk && (
                    <Badge 
                      variant="outline" 
                      className="border-red-500/30 text-red-300 bg-red-500/10 text-xs mt-1"
                    >
                      High Risk
                    </Badge>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Recommendations */}
      <Card className="bg-black/40 border-purple-500/20 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="text-purple-100 flex items-center space-x-2">
            <span className="text-2xl">🛡️</span>
            <span>Security Recommendations</span>
          </CardTitle>
          <CardDescription className="text-purple-300">
            Immediate actions to mitigate the security breach
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="bg-gradient-to-r from-red-500/10 to-orange-500/10 border border-red-500/20 rounded-lg p-4">
              <h4 className="text-red-300 font-bold mb-3">🚨 Immediate Actions Required</h4>
              <ul className="space-y-2 text-sm text-red-200">
                <li>• Reset passwords for all compromised accounts immediately</li>
                <li>• Enable multi-factor authentication on high-risk services</li>
                <li>• Revoke and regenerate session tokens/cookies</li>
                <li>• Scan and clean infected systems with anti-malware tools</li>
              </ul>
            </div>
            
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4">
              <h4 className="text-amber-300 font-bold mb-3">⚡ Short-term Measures</h4>
              <ul className="space-y-2 text-sm text-amber-200">
                <li>• Implement network segmentation to contain threats</li>
                <li>• Update browser security settings and clear stored data</li>
                <li>• Monitor accounts for unauthorized access attempts</li>
                <li>• Document incident for compliance and learning purposes</li>
              </ul>
            </div>
            
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
              <h4 className="text-green-300 font-bold mb-3">🔒 Long-term Prevention</h4>
              <ul className="space-y-2 text-sm text-green-200">
                <li>• Deploy endpoint detection and response (EDR) solutions</li>
                <li>• Implement user security awareness training</li>
                <li>• Regular security audits and vulnerability assessments</li>
                <li>• Establish incident response procedures</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}