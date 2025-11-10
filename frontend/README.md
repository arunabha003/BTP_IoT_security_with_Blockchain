# IoT Identity Gateway - Frontend

Modern React-based web interface for the IoT Identity Gateway with RSA Accumulator and Blockchain integration.

## Features

- **Dashboard**: Real-time system monitoring with statistics
- **Device Enrollment**: Generate keypairs and enroll new IoT devices
- **Authentication**: Verify device credentials and witnesses
- **Device Revocation**: Remove devices using trapdoor operations
- **Device Registry**: View and manage all enrolled devices
- **System Status**: Monitor gateway and blockchain health

## Technology Stack

- **React 18**: Modern UI library
- **Vite**: Fast build tool and dev server
- **Tailwind CSS**: Utility-first styling
- **Axios**: HTTP client for API calls
- **React Router**: Client-side routing
- **Lucide React**: Beautiful icons
- **React Hot Toast**: Toast notifications

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Running IoT Gateway backend (http://127.0.0.1:8000)
- Running Anvil blockchain (http://127.0.0.1:8545)

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at http://localhost:3000

### Build for Production

```bash
# Create optimized production build
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── gateway.js          # API client for backend
│   ├── pages/
│   │   ├── Dashboard.jsx       # Main dashboard
│   │   ├── EnrollDevice.jsx    # Device enrollment flow
│   │   ├── AuthenticateDevice.jsx  # Device authentication
│   │   ├── RevokeDevice.jsx    # Device revocation
│   │   ├── DeviceList.jsx      # Device registry
│   │   └── SystemStatus.jsx    # System monitoring
│   ├── App.jsx                 # Main app component with routing
│   ├── main.jsx                # Application entry point
│   └── index.css               # Global styles (Tailwind)
├── index.html                  # HTML template
├── package.json                # Dependencies and scripts
├── vite.config.js              # Vite configuration
├── tailwind.config.js          # Tailwind CSS configuration
└── postcss.config.js           # PostCSS configuration
```

## API Integration

The frontend connects to the backend gateway at `http://127.0.0.1:8000` through a proxy configured in `vite.config.js`. All API calls use the `/api` prefix which is automatically rewritten.

### Available Endpoints

- `GET /status` - System status and statistics
- `GET /root` - Current accumulator root
- `POST /keygen` - Generate device keypair
- `POST /enroll` - Enroll new device
- `POST /auth` - Authenticate device
- `POST /revoke` - Revoke device
- `GET /witness/{deviceIdHex}` - Get device witness

## Key Features

### 1. Device Enrollment

Three-step wizard:
1. Generate cryptographic keypair (Ed25519 or RSA)
2. Review keys and enroll device
3. View enrollment results with device credentials

### 2. Device Authentication

Form-based authentication with:
- Device ID validation
- Witness verification
- Signature checking
- Automatic witness updates

### 3. Device Revocation

Secure revocation process with:
- Confirmation dialog
- Trapdoor-based removal
- Blockchain state update
- Witness refresh for remaining devices

### 4. Real-time Monitoring

- Auto-refreshing dashboard (every 5 seconds)
- System health indicators
- Accumulator statistics
- Blockchain connection status

## Customization

### Styling

The app uses Tailwind CSS with custom theme colors defined in `tailwind.config.js`. To customize:

```javascript
// tailwind.config.js
theme: {
  extend: {
    colors: {
      primary: {
        500: '#3b82f6',  // Customize primary color
        // ... other shades
      }
    }
  }
}
```

### API Endpoint

To change the backend URL, update `vite.config.js`:

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://YOUR_BACKEND_URL',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

## Development

### Running in Development Mode

```bash
npm run dev
```

Features:
- Hot Module Replacement (HMR)
- Fast refresh
- Detailed error messages
- Source maps

### Code Quality

```bash
# Run linter
npm run lint
```

## Deployment

### Build for Production

```bash
npm run build
```

Output will be in the `dist/` directory, ready to be served by any static file server.

### Serving Production Build

```bash
# Preview production build locally
npm run preview

# Or use any static server
npx serve dist
```

### Deploy to Cloud

The built files in `dist/` can be deployed to:
- Vercel
- Netlify
- AWS S3 + CloudFront
- GitHub Pages
- Any static hosting service

## Troubleshooting

### Cannot connect to backend

- Ensure the gateway is running on http://127.0.0.1:8000
- Check browser console for CORS errors
- Verify proxy configuration in `vite.config.js`

### Styling not working

- Make sure Tailwind CSS is properly installed
- Run `npm install` to ensure all dependencies are installed
- Check that PostCSS configuration is correct

### API calls failing

- Verify backend is running and accessible
- Check network tab in browser DevTools
- Ensure API endpoints match backend routes

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Modern mobile browsers

## License

Same as main project

## Support

For issues or questions, please refer to the main project documentation.
