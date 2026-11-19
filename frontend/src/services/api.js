import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
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
