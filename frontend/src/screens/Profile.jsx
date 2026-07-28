import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logoutUser, loadProfile } from '../store/slices/authSlice';
import { User, Shield, Calendar, LogOut, CheckCircle2 } from 'lucide-react';

export const Profile = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useSelector((state) => state.auth);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    } else {
      dispatch(loadProfile());
    }
  }, [isAuthenticated, navigate, dispatch]);

  const handleLogout = () => {
    dispatch(logoutUser());
    navigate('/');
  };

  if (!user) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="glass-panel p-8 rounded-2xl border border-white/5 relative overflow-hidden">
        {/* Glow Element */}
        <div className="absolute -top-32 -left-32 w-64 h-64 bg-amber-500/5 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between border-b border-white/5 pb-8 mb-8 gap-4">
          <div className="flex items-center space-x-4">
            <div className="h-16 w-16 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
              <User className="h-8 w-8 text-amber-500" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">{user.name}</h1>
              <p className="text-slate-400 text-sm font-mono">{user.email}</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="flex items-center space-x-1.5 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 hover:border-rose-500/30 text-rose-400 px-4 py-2 rounded-lg text-xs font-semibold font-mono transition-all uppercase cursor-pointer"
          >
            <LogOut className="h-4 w-4" />
            <span>Terminate Session</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-white mb-4">Credentials & Security</h2>
              <div className="bg-[#11111a] border border-white/5 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500 uppercase font-mono font-semibold tracking-wider">Access Clearance</span>
                  <span className="flex items-center space-x-1 px-2.5 py-1.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-xs text-amber-400 font-mono font-semibold uppercase">
                    <Shield className="h-3 w-3" />
                    <span>{user.role}</span>
                  </span>
                </div>

                <div className="flex items-center justify-between border-t border-white/5 pt-4">
                  <span className="text-xs text-slate-500 uppercase font-mono font-semibold tracking-wider">MERN Registered</span>
                  <span className="flex items-center space-x-1 text-xs text-slate-300 font-mono">
                    <Calendar className="h-3.5 w-3.5 text-slate-500" />
                    <span>System Active Node 2026</span>
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-white mb-4">Operator Clearance Tasks</h2>
            <div className="bg-[#11111a] border border-white/5 rounded-xl p-5 space-y-4">
              <p className="text-xs text-slate-400 leading-relaxed">
                As an authentic member of FalconSpido, you have active capability to participate in submissions. 
                {user.role === 'admin' ? (
                  <span className="text-amber-400"> You have full Administrator access, giving you permission to crawl URLs, review AI descriptions, and submit URL Indexing API pings to Google Search Console (GSC).</span>
                ) : (
                  <span> Feel free to submit custom pine scripts, Expert Advisors, and trading utilities. Our moderator team will quickly crawl your page with Gemini grounding and authorize listings.</span>
                )}
              </p>

              <div className="flex items-center space-x-2 text-xs text-emerald-400 bg-emerald-500/5 border border-emerald-500/10 p-3 rounded-lg">
                <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
                <span>Your connection node is secure & fully encrypted.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
