import { createSlice } from '@reduxjs/toolkit';
import { apiService } from '../../utils/api';

const storedUser = localStorage.getItem('fs_user_info');
let initialUser = null;
if (storedUser) {
  try {
    initialUser = JSON.parse(storedUser);
  } catch (e) {
    console.error('Failed to parse cached user info:', e);
  }
}

const initialState = {
  user: initialUser,
  isAuthenticated: !!initialUser,
  isLoading: false,
  error: null
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    authStart: (state) => {
      state.isLoading = true;
      state.error = null;
    },
    authSuccess: (state, action) => {
      state.isLoading = false;
      state.isAuthenticated = true;
      state.user = action.payload;
      state.error = null;
      localStorage.setItem('fs_user_info', JSON.stringify(action.payload));
    },
    authFailure: (state, action) => {
      state.isLoading = false;
      state.error = action.payload;
    },
    logoutUser: (state) => {
      state.user = null;
      state.isAuthenticated = false;
      state.isLoading = false;
      state.error = null;
      localStorage.removeItem('fs_user_info');
    },
    clearError: (state) => {
      state.error = null;
    }
  }
});

export const { 
  authStart, 
  authSuccess, 
  authFailure, 
  logoutUser, 
  clearError 
} = authSlice.actions;

// Async Thunks
export const login = (email, password) => async (dispatch) => {
  dispatch(authStart());
  try {
    const res = await apiService.login(email, password);
    if (res?.success) {
      dispatch(authSuccess(res.data));
      return { success: true };
    } else {
      dispatch(authFailure(res?.error || 'Registration failed'));
      return { success: false, error: res?.error };
    }
  } catch (err) {
    const msg = err.error || err.message || 'Login credentials incorrect.';
    dispatch(authFailure(msg));
    return { success: false, error: msg };
  }
};

export const register = (name, email, password) => async (dispatch) => {
  dispatch(authStart());
  try {
    const res = await apiService.register(name, email, password);
    if (res?.success) {
      dispatch(authSuccess(res.data));
      return { success: true };
    } else {
      dispatch(authFailure(res?.error || 'Registration failed'));
      return { success: false, error: res?.error };
    }
  } catch (err) {
    const msg = err.error || err.message || 'Registration details failed validations.';
    dispatch(authFailure(msg));
    return { success: false, error: msg };
  }
};

export const loadProfile = () => async (dispatch, getState) => {
  const { auth } = getState();
  if (!auth.isAuthenticated) return;
  
  dispatch(authStart());
  try {
    const res = await apiService.getProfile();
    if (res?.success) {
      // Keep existing token while updating profile values
      const updatedUser = { ...auth.user, ...res.data };
      dispatch(authSuccess(updatedUser));
    }
  } catch (err) {
    console.error('Failed to load credentials profile:', err);
    // If authorization fails, clear credentials
    dispatch(logoutUser());
  }
};

export default authSlice.reducer;
