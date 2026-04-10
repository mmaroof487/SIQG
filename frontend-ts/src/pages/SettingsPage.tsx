import { useState } from "react";
import { Settings2, Key, Bell, Shield, TerminalSquare } from "lucide-react";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("api-keys");
  
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-end gap-6 mb-2">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border border-primary-neon/30 flex items-center justify-center shadow-[0_0_20px_rgba(0,255,157,0.15)] backdrop-blur-xl">
          <Settings2 className="w-8 h-8 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
        </div>
        <div>
          <h1 className="text-4xl font-black text-on-surface mb-2 tracking-tight">Sentinel Settings</h1>
          <p className="text-on-surface-variant font-medium">Access matrix, deployment overrides, and API keys</p>
        </div>
      </div>

      <div className="flex gap-6 mt-8">
        {/* Settings Sidebar */}
        <div className="w-64 shrink-0 space-y-2">
          {[
            { id: 'api-keys', icon: Key, label: 'API Keys' },
            { id: 'notifications', icon: Bell, label: 'Notifications' },
            { id: 'security', icon: Shield, label: 'Security Polices' },
            { id: 'terminal', icon: TerminalSquare, label: 'Editor Preferences' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold uppercase tracking-wider text-sm transition-all ${
                activeTab === tab.id 
                ? 'bg-primary-neon/10 text-primary-neon border border-primary-neon/30 shadow-[inset_0_0_10px_rgba(0,255,157,0.05)]' 
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-high border border-transparent'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Settings Content */}
        <div className="flex-1 bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl shadow-lg ring-1 ring-white/5 overflow-hidden">
          {activeTab === 'api-keys' && (
            <div className="p-8">
              <h2 className="text-xl font-bold text-on-surface mb-2 flex items-center gap-2">
                <span className="w-1.5 h-6 bg-primary-neon rounded-full"></span>
                Programmatic Access
              </h2>
              <p className="text-on-surface-variant text-sm mb-8">Generate HMAC-signed tokens for bypassing the GUI layer. Treat these as highly classified.</p>
              
              <div className="bg-surface-high/30 border border-surface-high rounded-xl p-6 mb-8 flex items-center justify-between">
                <div>
                  <h3 className="text-on-surface font-bold text-lg">Production Token</h3>
                  <p className="text-on-surface-variant text-sm mt-1">Last used 2 hours ago from 10.0.0.5</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="font-mono text-sm bg-surface px-4 py-2 border border-surface-high rounded-lg text-primary-neon">
                    siqg_live_xxxxxxxxxxxxxxxxxxxxxx
                  </div>
                  <button className="px-4 py-2 bg-error/10 hover:bg-error/20 text-error font-bold uppercase tracking-wider text-xs rounded-lg transition-colors border border-error/30">Revoke</button>
                </div>
              </div>

              <button className="px-6 py-2.5 bg-primary-neon hover:bg-primary-neon/80 text-background font-bold tracking-wider uppercase text-sm rounded-xl transition-all shadow-[0_0_15px_rgba(0,255,157,0.3)]">
                Generate New Key
              </button>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="p-8">
              <h2 className="text-xl font-bold text-on-surface mb-2 flex items-center gap-2">
                <span className="w-1.5 h-6 bg-primary-container rounded-full"></span>
                Webhook Channels
              </h2>
              <p className="text-on-surface-variant text-sm mb-8">Configure endpoints to receive Argus Sentinel broadcast events including anomaly detections.</p>

              <div className="space-y-6">
                <div className="space-y-3">
                  <label className="text-sm font-bold uppercase tracking-wider text-on-surface-variant">Slack Webhook URL</label>
                  <input type="text" className="w-full bg-surface border border-surface-high rounded-xl px-4 py-3 text-on-surface outline-none focus:border-primary-neon/50 transition-colors" placeholder="https://hooks.slack.com/services/..." />
                </div>
                <div className="space-y-3">
                  <label className="text-sm font-bold uppercase tracking-wider text-on-surface-variant">PagerDuty Integration Key</label>
                  <input type="text" className="w-full bg-surface border border-surface-high rounded-xl px-4 py-3 text-on-surface outline-none focus:border-primary-neon/50 transition-colors" placeholder="e.g. 5d5a8s..." />
                </div>
                <div className="pt-4 border-t border-surface-high">
                  <button className="px-6 py-2.5 bg-surface-high hover:border-primary-neon/50 border border-surface-high text-on-surface font-bold tracking-wider uppercase text-sm rounded-xl transition-all">
                    Save Pipeline Config
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab !== 'api-keys' && activeTab !== 'notifications' && (
            <div className="p-20 text-center text-on-surface-variant font-mono uppercase tracking-widest flex flex-col items-center">
              <Settings2 className="w-12 h-12 mb-4 opacity-20" />
              Module Offline
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
