import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App';
import {BrandingProvider} from './features/branding/BrandingContext';
import './style.css';
createRoot(document.getElementById('root')!).render(<React.StrictMode><BrandingProvider><App/></BrandingProvider></React.StrictMode>);
