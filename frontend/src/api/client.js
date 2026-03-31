import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

export const api = axios.create({ baseURL: BASE_URL })

export async function signup(username, password, role) {
  const { data } = await api.post('/auth/signup', { username, password, role })
  return data
}

export async function login(username, password) {
  const { data } = await api.post('/auth/login', { username, password })
  return data
}

export async function queryRag(question, model) {
  const { data } = await api.post('/query', { question, model })
  return data
}

export function createChatSocket(onMessage, onError) {
  const ws = new WebSocket(`${WS_URL}/ws/chat`)
  ws.onmessage = (event) => onMessage(JSON.parse(event.data))
  ws.onerror = (err) => onError && onError(err)
  return ws
}
