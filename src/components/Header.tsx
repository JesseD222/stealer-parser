"use client";

export function Header() {
  return (
    <header className="border-b border-purple-500/20 bg-black/40 backdrop-blur-md">
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">SP</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                Stealer Parser
              </h1>
              <p className="text-purple-300 text-sm">
                Advanced Infostealer Log Analysis
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-6">
            <nav className="hidden md:flex items-center space-x-6">
              <a 
                href="#analysis" 
                className="text-purple-300 hover:text-white transition-colors duration-200"
              >
                Analysis
              </a>
              <a 
                href="#reports" 
                className="text-purple-300 hover:text-white transition-colors duration-200"
              >
                Reports
              </a>
              <a 
                href="#docs" 
                className="text-purple-300 hover:text-white transition-colors duration-200"
              >
                Documentation
              </a>
            </nav>
            
            <div className="flex items-center space-x-2 text-purple-400">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-sm">Ready</span>
            </div>
          </div>
        </div>
        
        <div className="mt-4 p-4 bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-lg border border-purple-500/20">
          <div className="flex items-center space-x-3">
            <div className="w-6 h-6 bg-amber-500 rounded flex items-center justify-center">
              <span className="text-black text-xs font-bold">!</span>
            </div>
            <div>
              <p className="text-amber-200 text-sm font-medium">
                Security Notice
              </p>
              <p className="text-amber-100 text-xs mt-1">
                This tool is designed for legitimate security research and incident response. 
                Only process files you have legal authority to analyze.
              </p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}