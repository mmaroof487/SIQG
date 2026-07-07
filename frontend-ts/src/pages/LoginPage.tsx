import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../utils/api';
import { useAuth } from '../contexts/AuthContext';
import { KeyRound, User, Lock, ShieldCheck } from 'lucide-react';

// Parse backend validation errors — handles both plain strings and
// Pydantic v2 array format: [{"loc":["body","password"],"msg":"..."}]
function parseErrorDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e: any) => {
        const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : '';
        const msg = e.msg ?? e.message ?? JSON.stringify(e);
        return field ? `${field}: ${msg}` : msg;
      })
      .join(' · ');
  }
  return JSON.stringify(detail);
}

// Simple password strength score 0–4
function passwordStrength(pw: string): number {
  let score = 0;
  if (pw.length >= 8)  score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return Math.min(score, 4);
}

const STRENGTH_LABEL = ['', 'Weak', 'Fair', 'Good', 'Strong'];
const STRENGTH_COLOR = ['', 'bg-red-500', 'bg-yellow-400', 'bg-blue-400', 'bg-primary-neon'];

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const strength = isRegistering ? passwordStrength(password) : 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Client-side guards (mirrors backend rules — not a substitute)
    if (isRegistering) {
      if (username.trim().length < 3 || username.trim().length > 32) {
        setError('Username must be 3–32 characters.');
        return;
      }
      if (!/^[a-zA-Z0-9_-]+$/.test(username.trim())) {
        setError('Username may only contain letters, numbers, underscores or hyphens.');
        return;
      }
      if (password.length < 8) {
        setError('Password must be at least 8 characters.');
        return;
      }
      if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
        setError('Password must contain at least one letter and one number.');
        return;
      }
    }

    setIsLoading(true);
    try {
      if (isRegistering) {
        const res = await api.register(username, email, password);
        login(true, res.data.role);
      } else {
        const res = await api.login(username, password);
        login(true, res.data.role);
      }
      // Use React Router navigate instead of hard page reload
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(
        detail
          ? parseErrorDetail(detail)
          : err.message || 'Authentication failed. Check your credentials.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-md bg-surface/60 backdrop-blur-xl border border-surface-high p-8 rounded-2xl shadow-2xl ring-1 ring-white/5 relative overflow-hidden">

        {/* Glow effects */}
        <div className="absolute -top-32 -right-32 w-64 h-64 bg-primary-neon/20 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute -bottom-32 -left-32 w-64 h-64 bg-primary-container/20 rounded-full blur-[100px] pointer-events-none" />

        <div className="relative z-10 flex flex-col items-center mb-8">
          <div className="w-20 h-20 bg-surface-high/50 rounded-2xl border border-surface-high flex items-center justify-center mb-4 shadow-[0_0_25px_rgba(0,255,157,0.1)] p-2">
            <img src="/logo.png" alt="Argus Gateway" className="w-full h-full object-contain" />
          </div>
          <h1 className="text-2xl font-black tracking-tight text-on-surface">ARGUS GATEWAY</h1>
          <p className="text-on-surface-variant font-medium text-sm mt-1 uppercase tracking-widest">
            {isRegistering ? 'Initialize Operative' : 'Secure Authenticate'}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-error/10 border border-error/30 rounded-lg text-error text-sm font-semibold text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="relative z-10 space-y-4">

          {/* Username */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider ml-1">
              Operative ID (Username)
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant" />
              <input
                id="auth-username"
                type="text"
                required
                autoComplete="username"
                maxLength={32}
                value={username}
                onChange={e => setUsername(e.target.value)}
                className="w-full bg-surface-high/50 border border-surface-high focus:border-primary-neon focus:ring-1 focus:ring-primary-neon rounded-xl py-3 pl-10 pr-4 text-sm text-on-surface transition-all outline-none"
                placeholder="Enter identifying signature…"
              />
            </div>
          </div>

          {/* Email (register only) */}
          {isRegistering && (
            <div className="space-y-1">
              <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider ml-1">
                Comms Uplink (Email)
              </label>
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant" />
                <input
                  id="auth-email"
                  type="email"
                  required
                  autoComplete="email"
                  maxLength={254}
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full bg-surface-high/50 border border-surface-high focus:border-primary-neon focus:ring-1 focus:ring-primary-neon rounded-xl py-3 pl-10 pr-4 text-sm text-on-surface transition-all outline-none"
                  placeholder="Transmission target…"
                />
              </div>
            </div>
          )}

          {/* Password */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider ml-1">
              Encryption Key (Password)
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant" />
              <input
                id="auth-password"
                type="password"
                required
                autoComplete={isRegistering ? 'new-password' : 'current-password'}
                maxLength={128}
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full bg-surface-high/50 border border-surface-high focus:border-primary-neon focus:ring-1 focus:ring-primary-neon rounded-xl py-3 pl-10 pr-4 text-sm tracking-widest text-on-surface transition-all outline-none placeholder:tracking-normal"
                placeholder="••••••••••••"
              />
            </div>

            {/* Password strength bar — only on register */}
            {isRegistering && password.length > 0 && (
              <div className="mt-2 space-y-1">
                <div className="flex gap-1">
                  {[1, 2, 3, 4].map(i => (
                    <div
                      key={i}
                      className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                        i <= strength ? STRENGTH_COLOR[strength] : 'bg-surface-high'
                      }`}
                    />
                  ))}
                </div>
                <div className="flex items-center gap-1 ml-0.5">
                  <ShieldCheck className={`w-3 h-3 ${strength >= 3 ? 'text-primary-neon' : 'text-on-surface-variant'}`} />
                  <span className="text-xs text-on-surface-variant">
                    {STRENGTH_LABEL[strength] || 'Too short'}
                    {strength < 3 && ' — add uppercase, numbers or symbols'}
                  </span>
                </div>
              </div>
            )}
          </div>

          <button
            id="auth-submit"
            type="submit"
            disabled={isLoading}
            className="w-full mt-6 py-3.5 bg-primary-neon/10 hover:bg-primary-neon/20 border border-primary-neon/30 text-primary-neon font-bold uppercase tracking-widest text-sm rounded-xl transition-all shadow-[0_0_20px_rgba(0,255,157,0.1)] flex justify-center items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-primary-neon border-t-transparent rounded-full animate-spin" />
            ) : (
              <>{isRegistering ? 'MINT CREDENTIALS' : 'INITIATE UPLINK'}</>
            )}
          </button>
        </form>

        <div className="relative z-10 mt-6 text-center">
          <button
            type="button"
            onClick={() => { setIsRegistering(!isRegistering); setError(''); setPassword(''); }}
            className="text-primary-container text-xs font-bold uppercase tracking-wider hover:text-primary-neon transition-colors"
          >
            {isRegistering ? 'Return to Authentication Matrix' : 'Register New Operative Credentials'}
          </button>
        </div>
      </div>
    </div>
  );
}
