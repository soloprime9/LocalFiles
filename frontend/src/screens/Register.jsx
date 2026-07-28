import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate, Link } from 'react-router-dom';
import { register, clearError } from '../store/slices/authSlice';
import { ShieldAlert, Mail, Lock, User, ArrowRight, AlertTriangle } from 'lucide-react';

export const Register = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [validationErr, setValidationErr] = useState('');

  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { isLoading, error, isAuthenticated } = useSelector((state) => state.auth);

  useEffect(() => {
    dispatch(clearError());
    setValidationErr('');
  }, [dispatch]);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationErr('');

    if (!name || !email || !password) {
      setValidationErr('Please fill in check parameters.');
      return;
    }

    if (password.length < 6) {
      setValidationErr('Password must be at least 6 characters.');
      return;
    }

    const payload = await dispatch(register(name, email, password));
    if (payload?.success) {
      navigate('/');
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 glass-panel p-8 rounded-2xl border border-white/5 relative overflow-hidden">
        {/* Glow Element */}
        <div className="absolute -bottom-32 -left-32 w-64 h-64 bg-amber-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div>
          <div className="mx-auto h-12 w-12 rounded-xl bg-amber-500/10 flex items-center justify-center border border-amber-500/30">
            <ShieldAlert className="h-6 w-6 text-amber-500" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-white tracking-tight">
            Register Account
          </h2>
          <p className="mt-2 text-center text-sm text-slate-400">
            Set up an account on FalconSpido's directory node.
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          { (error || validationErr) && (
            <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 p-3.5 rounded-lg text-xs flex items-start space-x-2">
              <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
              <span>{error || validationErr}</span>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1.5 font-mono">
                Operator Username
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="QuantMaster"
                  className="w-full bg-[#11111a] border border-white/5 rounded-lg py-2.5 pl-10 pr-4 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 transition-all font-sans"
                />
                <User className="absolute left-3 top-3 h-4 w-4 text-slate-600" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1.5 font-mono">
                Official Email
              </label>
              <div className="relative">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="operator@domain.com"
                  className="w-full bg-[#11111a] border border-white/5 rounded-lg py-2.5 pl-10 pr-4 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 transition-all font-sans"
                />
                <Mail className="absolute left-3 top-3 h-4 w-4 text-slate-600" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1.5 font-mono">
                Access Token Password
              </label>
              <div className="relative">
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-[#11111a] border border-white/5 rounded-lg py-2.5 pl-10 pr-4 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 transition-all font-sans"
                />
                <Lock className="absolute left-3 top-3 h-4 w-4 text-slate-600" />
              </div>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2.5 px-4 border border-transparent text-sm font-semibold rounded-lg text-black bg-amber-500 hover:bg-amber-400 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 transition-all cursor-pointer shadow-lg shadow-amber-500/10 disabled:opacity-55"
            >
              {isLoading ? (
                <div className="h-5 w-5 border-2 border-black border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <span className="flex items-center space-x-1">
                  <span>Register Credentials</span>
                  <ArrowRight className="h-4 w-4" />
                </span>
              )}
            </button>
          </div>
        </form>

        <div className="text-center mt-4">
          <p className="text-xs text-slate-500 font-mono">
            Already registered?{' '}
            <Link to="/login" className="text-amber-500 hover:text-amber-400 hover:underline">
              Sign In ->
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;
