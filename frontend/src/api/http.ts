import axios from 'axios'
import qs from 'qs'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: Number(import.meta.env.VITE_API_TIMEOUT_MS),
  paramsSerializer: (params) => qs.stringify(params, { arrayFormat: 'repeat' }),
})
http.interceptors.request.use(config=>{const token=localStorage.getItem('token');if(token) config.headers.Authorization=`Bearer ${token}`;return config})
http.interceptors.response.use(r=>r,e=>{if(e.response?.status===401&&location.pathname!='/login'&&!e.config?.skipAuthRedirect){localStorage.removeItem('token');location.href='/login'}return Promise.reject(e)})
