import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './styles/tokens.css'
import './styles/primitives.css'
import './styles/shell.css'
import './styles/processing.css'
import './styles/extraction.css'
import './styles/review.css'
import './styles/audit.css'
import './styles/help.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
