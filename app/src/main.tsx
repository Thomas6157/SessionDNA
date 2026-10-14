import React from 'react';
import ReactDOM from 'react-dom/client';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {StateProvider} from './lib/state';
import App from './App';
import './style.css';
const client=new QueryClient({defaultOptions:{queries:{retry:1,staleTime:60000,refetchOnWindowFocus:false}}});
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={client}><StateProvider><App/></StateProvider></QueryClientProvider></React.StrictMode>);
if('serviceWorker' in navigator)window.addEventListener('load',()=>{navigator.serviceWorker.register('/sw.js').catch(()=>{/* L'application reste utilisable si le mode hors connexion est indisponible. */});});
