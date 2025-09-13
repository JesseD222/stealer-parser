# Stealer Data Record Parser - Web Interface

A modern web interface for the stealer data record parser, built with Next.js and FastAPI.

## Features

- **Modern Web Interface**: Intuitive drag-and-drop file upload with real-time processing feedback
- **Comprehensive Analysis**: Detailed visualization of credentials, system info, and cookies
- **Risk Assessment**: Automatic categorization and risk analysis of compromised data
- **Multiple Export Formats**: Export results as JSON, CSV, or HTML reports
- **Real-time Processing**: Live progress updates and status monitoring
- **Security-First**: Secure file handling with sandboxed processing environment

## Architecture

- **Frontend**: Next.js 14 with TypeScript, Tailwind CSS, and shadcn/ui components
- **Backend**: FastAPI wrapper around the existing Python stealer_parser
- **Processing**: Existing Python parsing engine with PLY lexer/parser
- **Real-time Updates**: RESTful API with polling for progress tracking

## Quick Start

### Prerequisites

- Node.js 18+ and pnpm
- Python 3.10+ 
- Required system packages: `unrar`, `p7zip`

### Development Setup

1. **Install Frontend Dependencies**
   ```bash
   pnpm install
   ```

2. **Install API Dependencies**
   ```bash
   pip install -r api/requirements.txt
   # OR using poetry from the original project
   poetry install
   ```

3. **Start the API Server**
   ```bash
   # Option 1: Direct Python
   python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   
   # Option 2: Using pnpm script
   pnpm run api-server
   ```

4. **Start the Frontend**
   ```bash
   pnpm run dev
   ```

5. **Access the Application**
   - Web Interface: http://localhost:3000
   - API Documentation: http://localhost:8000/api/docs

### Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# For production with Nginx
docker-compose --profile production up --build
```

## Usage

### Web Interface

1. **Upload File**: Drag and drop or select a stealer archive (.zip, .rar, .7z)
2. **Optional Password**: Enter password if archive is encrypted
3. **Monitor Progress**: Real-time processing updates with detailed steps
4. **Analyze Results**: Interactive dashboard with multiple data views
5. **Export Data**: Download results in various formats

### API Endpoints

- `POST /api/upload` - Upload file for processing
- `GET /api/status/{job_id}` - Check processing status
- `GET /api/result/{job_id}` - Retrieve processing results
- `DELETE /api/jobs/{job_id}` - Clean up completed jobs

## Data Analysis Features

### Overview Dashboard
- Executive summary with security impact assessment
- Geographic distribution of compromised systems
- Threat attribution and stealer identification
- Risk categorization and recommendations

### Credentials Analysis
- Searchable table of all extracted credentials
- Risk level assessment (High/Medium/Low)
- Software and browser breakdown
- Password visibility controls

### System Information
- Detailed machine information and identifiers
- Geographic location and network data
- Compromise timeline and impact assessment
- Per-system data summaries

### Cookie Analysis
- Browser session data extraction
- Security flag analysis (Secure/HTTPOnly)
- Expiration status and domain categorization
- Browser-specific cookie breakdown

### Security Recommendations
- Immediate response actions
- Short-term security measures  
- Long-term prevention strategies
- Compliance and documentation guidance

## Security Considerations

- **File Validation**: Strict file type and size validation
- **Sandboxed Processing**: Isolated processing environment
- **Secure Headers**: Security headers for XSS and clickjacking protection
- **No Persistent Storage**: Temporary processing with automatic cleanup
- **Input Sanitization**: All inputs validated and sanitized

## Configuration

### Environment Variables

```bash
# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000

# API
API_HOST=0.0.0.0
API_PORT=8000
MAX_FILE_SIZE=104857600  # 100MB
```

### File Size Limits

- Maximum archive size: 100MB
- Supported formats: .zip, .rar, .7z
- Password protection supported

## Development

### Frontend Stack
- Next.js 14 with App Router
- TypeScript for type safety
- Tailwind CSS for styling
- shadcn/ui components
- Radix UI primitives

### Backend Stack
- FastAPI for REST API
- Background tasks for file processing
- Existing stealer_parser integration
- CORS enabled for development

### Code Organization

```
src/
├── app/                 # Next.js app router pages
├── components/          # Reusable React components
│   ├── ui/             # shadcn/ui components
│   └── ...             # Custom components
├── lib/                # Utilities and API client
└── ...

api/
├── main.py             # FastAPI application
├── requirements.txt    # Python dependencies
└── ...

stealer_parser/         # Original Python parser (unchanged)
```

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Ensure API server is running on port 8000
   - Check CORS configuration for your domain

2. **File Upload Fails**
   - Verify file size (max 100MB)
   - Check file format (.zip, .rar, .7z only)
   - Ensure sufficient disk space

3. **Processing Hangs**
   - Check API server logs
   - Verify archive is not corrupted
   - Try with a smaller test file

### Development Debugging

```bash
# API Server logs
python -m uvicorn api.main:app --reload --log-level debug

# Frontend development
pnpm run dev

# Check API health
curl http://localhost:8000/api/health
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project maintains the same license as the original stealer-parser project (Apache License 2.0).

## Acknowledgements

- Original stealer-parser by the security research community
- Built with Next.js, FastAPI, and modern web technologies
- UI components from shadcn/ui and Radix UI