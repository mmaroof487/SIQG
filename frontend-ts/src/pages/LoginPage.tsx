import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../utils/api';
import { Shield, KeyRound, User, Lock } from 'lucide-react';

export default function LoginPage() {
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (isRegistering) {
        const res = await api.register(username, email, password);
        localStorage.setItem('token', res.data.access_token);
      } else {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);
        
        const res = await fetch('http://localhost:8000/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData.toString()
        });
        
        if (!res.ok) {
            throw new Error('Invalid credentials');
        }
        const data = await res.json();
        localStorage.setItem('token', data.access_token);
      }
      // Trigger a page reload to reset states or just navigate
      window.location.href = '/dashboard';
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-md bg-surface/60 backdrop-blur-xl border border-surface-high p-8 rounded-2xl shadow-2xl ring-1 ring-white/5 relative overflow-hidden">
        
        {/* Glow effects */}
        <div className="absolute -top-32 -right-32 w-64 h-64 bg-primary-neon/20 rounded-full blur-[100px] pointer-events-none"></div>
        <div className="absolute -bottom-32 -left-32 w-64 h-64 bg-primary-container/20 rounded-full blur-[100px] pointer-events-none"></div>

        <div className="relative z-10 flex flex-col items-center mb-8">
            <div className="w-20 h-20 bg-surface-high/50 rounded-2xl border border-surface-high flex items-center justify-center mb-4 shadow-[0_0_25px_rgba(0,255,157,0.1)] p-2">
                <img src="/argus-logo.png" alt="Argus Gateway" className="w-full h-full object-contain" />
            </div>
            <h1 className="text-2xl font-black tracking-tight text-on-surface">ARGUS GATEWAY</h1>
            <p className="text-on-surface-variant font-medium text-sm mt-1 uppercase tracking-widest">
                {isRegistering ? 'Initialize Operative' : 'Secure Authenticate'}
            </p>
        </div>

        {error && (
            <div className="mb-6 p-3 bg-error/10 border border-error/30 rounded-lg text-error text-sm font-semibold flex items-center justify-center text-center">
                {error}
            </div>
        )}

        <form onSubmit={handleSubmit} className="relative z-10 space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider ml-1">Operative ID (Username)</label>
            <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant" />
                <input 
                    type="text" 
                    required
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    className="w-full bg-surface-high/50 border border-surface-high focus:border-primary-neon focus:ring-1 focus:ring-primary-neon rounded-xl py-3 pl-10 pr-4 text-sm text-on-surface transition-all outline-none"
                    placeholder="Enter identifying signature..."
                />
            </div>
          </div>

          {isRegistering && (
            <div className="space-y-1">
              <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider ml-1">Comms Uplink (Email)</label>
              <div className="relative">
                  <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant" />
                  <input 
                      type="email" 
                      required
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      className="w-full bg-surface-high/50 border border-surface-high focus:border-primary-neon focus:ring-1 focus:ring-primary-neon rounded-xl py-3 pl-10 pr-4 text-sm text-on-surface transition-all outline-none"
                      placeholder="Transmission target..."
                  />
              </div>
            </div>
          )}

          <div className="space-y-1">
            <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider ml-1">Encryption Key (Password)</label>
            <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant" />
                <input 
                    type="password" 
                    required
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    className="w-full bg-surface-high/50 border border-surface-high focus:border-primary-neon focus:ring-1 focus:ring-primary-neon rounded-xl py-3 pl-10 pr-4 text-sm tracking-widest text-on-surface transition-all outline-none placeholder:tracking-normal"
                    placeholder="••••••••••••"
                />
            </div>
          </div>

          <button 
            type="submit" 
            disabled={isLoading}
            className="w-full mt-6 py-3.5 bg-primary-neon/10 hover:bg-primary-neon/20 border border-primary-neon/30 text-primary-neon font-bold uppercase tracking-widest text-sm rounded-xl transition-all shadow-[0_0_20px_rgba(0,255,157,0.1)] flex justify-center items-center gap-2"
          >
            {isLoading ? (
                <div className="w-5 h-5 border-2 border-primary-neon border-t-transparent rounded-full animate-spin"></div>
            ) : (
                <>{isRegistering ? 'MINT CREDENTIALS' : 'INITIATE UPLINK'}</>
            )}
          </button>
        </form>

        <div className="relative z-10 mt-6 text-center">
            <button 
                type="button" 
                onClick={() => { setIsRegistering(!isRegistering); setError(''); }}
                className="text-primary-container text-xs font-bold uppercase tracking-wider hover:text-primary-neon transition-colors"
            >
                {isRegistering ? 'Return to Authentication Matrix' : 'Register New Operative Credentials'}
            </button>
        </div>
      </div>
    </div>
  );
}
