import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

export async function getHealth() {
  const { data } = await api.get('/health/')
  return data
}

export async function predictAirQuality(payload) {
  const { data } = await api.post('/predict/', payload)
  return data
}

export async function getMetrics() {
  const { data } = await api.get('/metrics/')
  return data
}

export async function explainChart(payload) {
  const { data } = await api.post('/ai/explain/', payload)
  return data
}
