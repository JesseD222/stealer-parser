import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stealer Data Record Parser",
  description: "Advanced web interface for parsing infostealer malware logs and analyzing compromised systems",
  keywords: "stealer, malware, parser, security, logs, analysis",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 min-h-screen font-sans">
        <div className="min-h-screen bg-black/20 backdrop-blur-sm">
          {children}
        </div>
      </body>
    </html>
  );
}