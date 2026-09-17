const KEY = 'studyos_token';
export const getToken = () => { try { return localStorage.getItem(KEY); } catch { return null; } };
export const setToken = (token: string) => { try { localStorage.setItem(KEY, token); } catch { /* private mode */ } };
export const clearToken = () => { try { localStorage.removeItem(KEY); } catch { /* ignore */ } };
