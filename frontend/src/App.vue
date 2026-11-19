<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Bar, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  BarElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from 'chart.js'
import { getHealth, predictAirQuality } from './services/api'

ChartJS.register(BarElement, ArcElement, CategoryScale, LinearScale, Tooltip, Legend)

const activePage = ref('home')
const form = reactive({
  sensor_s1: '',
  sensor_s2: '',
  sensor_s3: '',
  sensor_s4: '',
  sensor_s5: '',
  temperature: '',
  relative_humidity: '',
  absolute_humidity: '',
})

const loading = ref(false)
const health = ref({ status: 'checking', model_ready: false, message: 'Memeriksa backend...' })
const result = ref(null)
const errorMessage = ref('')
const metrics = ref(null)
const metricsLoading = ref(true)
const metricsError = ref('')
const aiInsights = reactive({
  prediction_distribution: { loading: false, text: '', error: '' },
  r2_comparison: { loading: false, text: '', error: '' },
  data_split: { loading: false, text: '', error: '' },
  feature_usage: { loading: false, text: '', error: '' },
})

const pages = [
  { key: 'home', label: 'Beranda' },
  { key: 'prediction', label: 'Ruang Prediksi' },
  { key: 'performance', label: 'Evaluasi Model' },
  { key: 'guide', label: 'Panduan' },
]

const sensorFields = [
  {
    key: 'sensor_s1',
    title: 'PT08.S1 — CO (Karbon monoksida / Carbon Monoxide)',
    description: 'Respons sensor dengan target nominal karbon monoksida.',
    unit: 'a.u.',
    example: 'Contoh: 1360',
  },
  {
    key: 'sensor_s2',
    title: 'PT08.S2 — NMHC (Hidrokarbon non-metana / Non-Methane Hydrocarbons)',
    description: 'Respons sensor dengan target nominal hidrokarbon non-metana.',
    unit: 'a.u.',
    example: 'Contoh: 1046',
  },
  {
    key: 'sensor_s3',
    title: 'PT08.S3 — NOx (Oksida nitrogen / Nitrogen Oxides)',
    description: 'Respons sensor dengan target nominal oksida nitrogen.',
    unit: 'a.u.',
    example: 'Contoh: 1056',
  },
  {
    key: 'sensor_s4',
    title: 'PT08.S4 — NO₂ (Nitrogen dioksida / Nitrogen Dioxide)',
    description: 'Respons sensor dengan target nominal nitrogen dioksida.',
    unit: 'a.u.',
    example: 'Contoh: 1692',
  },
  {
    key: 'sensor_s5',
    title: 'PT08.S5 — O₃ (Ozon / Ozone)',
    description: 'Respons sensor dengan target nominal ozon.',
    unit: 'a.u.',
    example: 'Contoh: 1268',
  },
]

const environmentFields = [
  { key: 'temperature', title: 'Suhu udara (T)', description: 'Temperatur saat pengukuran.', unit: '°C', example: 'Contoh: 13.6', min: -30, max: 60, step: 0.1 },
  { key: 'relative_humidity', title: 'Kelembapan relatif (RH)', description: 'Persentase kelembapan relatif udara.', unit: '%', example: 'Contoh: 48.9', min: 0, max: 100, step: 0.1 },
  { key: 'absolute_humidity', title: 'Kelembapan absolut (AH)', description: 'Nilai kelembapan absolut pada skala dataset UCI.', unit: 'skala UCI', example: 'Contoh: 0.7578', min: 0, step: 0.0001 },
]

const targetPresentation = {
  'CO(GT)': 'Karbon monoksida (CO)',
  'C6H6(GT)': 'Benzena (C₆H₆)',
  'NOx(GT)': 'Oksida nitrogen (NOx)',
  'NO2(GT)': 'Nitrogen dioksida (NO₂)',
}

const glossary = [
  {
    term: 'CO', full: 'Karbon monoksida · Carbon Monoxide',
    explanation: 'Gas yang tidak berwarna dan tidak berbau. CO dapat terbentuk dari pembakaran bahan bakar yang tidak sempurna, misalnya pada kendaraan bermotor.',
    role: 'Salah satu konsentrasi polutan yang diprediksi AirSense.',
  },
  {
    term: 'NMHC', full: 'Hidrokarbon non-metana · Non-Methane Hydrocarbons',
    explanation: 'Kelompok senyawa hidrokarbon di udara selain metana. Istilah ini merujuk pada kelompok senyawa, bukan satu gas tunggal.',
    role: 'Nama target nominal sensor PT08.S2; bukan target keluaran model AirSense saat ini.',
  },
  {
    term: 'C₆H₆ / Benzena', full: 'Benzena · Benzene',
    explanation: 'Senyawa hidrokarbon aromatik yang dapat ditemukan pada emisi kendaraan dan penguapan bahan bakar. Paparan benzena perlu diperhatikan karena memiliki risiko kesehatan.',
    role: 'Konsentrasi benzena diprediksi menggunakan satu fitur: PT08.S2(NMHC).',
  },
  {
    term: 'NOx', full: 'Oksida nitrogen · Nitrogen Oxides',
    explanation: 'Istilah kolektif untuk beberapa senyawa oksida nitrogen, terutama NO dan NO₂, yang dapat terbentuk dari proses pembakaran.',
    role: 'Salah satu konsentrasi polutan yang diprediksi AirSense.',
  },
  {
    term: 'NO₂', full: 'Nitrogen dioksida · Nitrogen Dioxide',
    explanation: 'Salah satu jenis oksida nitrogen. Gas ini dapat dihasilkan dari pembakaran, termasuk emisi kendaraan dan kegiatan industri.',
    role: 'Salah satu konsentrasi polutan yang diprediksi AirSense.',
  },
  {
    term: 'O₃', full: 'Ozon · Ozone',
    explanation: 'Gas yang tersusun dari tiga atom oksigen. Ozon dekat permukaan tanah dapat terbentuk melalui reaksi kimia antara polutan lain dengan bantuan sinar matahari.',
    role: 'Target nominal sensor PT08.S5; konsentrasi O₃ bukan keluaran model versi awal AirSense.',
  },
  {
    term: 'PT08', full: 'Respons sensor kimia',
    explanation: 'Lima kolom PT08.S1 sampai PT08.S5 berisi respons sensor kimia pada dataset. Angkanya bukan konsentrasi gas secara langsung.',
    role: 'Lima respons sensor menjadi masukan utama model AirSense.',
  },
  {
    term: 'T, RH, AH', full: 'Variabel kondisi lingkungan',
    explanation: 'T adalah temperatur, RH adalah kelembapan relatif, dan AH adalah kelembapan absolut. Ketiganya membantu menggambarkan kondisi udara saat pengukuran.',
    role: 'Tiga fitur lingkungan yang digunakan bersama respons sensor pada model CO, NOx, dan NO₂.',
  },
]

const categoryClass = computed(() => {
  const value = result.value?.overall_category
  if (value === 'Baik') return 'good'
  if (value === 'Sedang') return 'moderate'
  if (value === 'Buruk') return 'bad'
  return ''
})

const predictionCategoryCounts = computed(() => {
  const predictions = result.value?.predictions ?? []
  return ['Baik', 'Sedang', 'Buruk'].map((category) => ({
    category,
    count: predictions.filter((item) => item.category === category).length,
  }))
})

const predictionCategoryChartData = computed(() => ({
  labels: predictionCategoryCounts.value.map((item) => item.category),
  datasets: [{
    data: predictionCategoryCounts.value.map((item) => item.count),
    backgroundColor: ['#2dbb88', '#e6ad45', '#e16c70'],
    borderColor: '#101d30',
    borderWidth: 4,
    hoverOffset: 7,
  }],
}))

const predictionCategoryChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '68%',
  plugins: {
    legend: {
      position: 'bottom',
      labels: { color: '#b9c7d9', padding: 18, usePointStyle: true, boxWidth: 8 },
    },
    tooltip: {
      callbacks: {
        label: (context) => `${context.label}: ${Number(context.raw)} polutan`,
      },
    },
  },
}

const modelRows = computed(() => {
  const targets = metrics.value?.targets ?? {}
  const featureMap = metrics.value?.model_feature_columns ?? {}
  return Object.entries(targetPresentation).map(([key, label]) => {
    const item = targets[key]
    return {
      key,
      label,
      mae: item?.mae,
      rmse: item?.rmse,
      r2: item?.r2,
      featureCount: item?.feature_columns?.length ?? featureMap[key]?.length ?? null,
      featureColumns: item?.feature_columns ?? featureMap[key] ?? [],
      trainRows: item?.train_rows,
      testRows: item?.test_rows,
    }
  }).filter((item) => item.mae !== undefined)
})

const performanceChartData = computed(() => ({
  labels: modelRows.value.map((item) => item.label),
  datasets: [{
    label: 'R²',
    data: modelRows.value.map((item) => item.r2),
    backgroundColor: ['#62cfae', '#85dfc2', '#4d9c91', '#4f8290'],
    borderRadius: 5,
    borderSkipped: false,
    barThickness: 25,
  }],
}))

const performanceChartOptions = {
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: (context) => `R²: ${Number(context.raw).toFixed(4)}` } },
  },
  scales: {
    x: {
      min: 0,
      max: 1,
      ticks: { color: '#8ea3b8', callback: (value) => Number(value).toFixed(1) },
      grid: { color: 'rgba(150,175,198,.12)' },
      border: { display: false },
    },
    y: {
      ticks: { color: '#c0ccda' },
      grid: { display: false },
      border: { display: false },
    },
  },
}

const dataSplitChartData = computed(() => ({
  labels: modelRows.value.map((item) => item.label),
  datasets: [
    {
      label: 'Data latih',
      data: modelRows.value.map((item) => Number(item.trainRows || 0)),
      backgroundColor: '#62cfae',
      borderRadius: 4,
      borderSkipped: false,
    },
    {
      label: 'Data uji',
      data: modelRows.value.map((item) => Number(item.testRows || 0)),
      backgroundColor: '#4f8290',
      borderRadius: 4,
      borderSkipped: false,
    },
  ],
}))

const dataSplitChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom',
      labels: { color: '#b9c7d9', padding: 18, usePointStyle: true, boxWidth: 8 },
    },
    tooltip: {
      callbacks: {
        label: (context) => `${context.dataset.label}: ${Number(context.raw).toLocaleString('id-ID')} baris`,
      },
    },
  },
  scales: {
    x: {
      ticks: { color: '#c0ccda' },
      grid: { display: false },
      border: { display: false },
    },
    y: {
      beginAtZero: true,
      ticks: { color: '#8ea3b8', callback: (value) => Number(value).toLocaleString('id-ID') },
      grid: { color: 'rgba(150,175,198,.12)' },
      border: { display: false },
    },
  },
}

const featureCountChartData = computed(() => ({
  labels: modelRows.value.map((item) => item.label),
  datasets: [{
    label: 'Jumlah fitur',
    data: modelRows.value.map((item) => Number(item.featureCount || 0)),
    backgroundColor: ['#62cfae', '#85dfc2', '#4d9c91', '#4f8290'],
    borderRadius: 5,
    borderSkipped: false,
    barThickness: 24,
  }],
}))

const featureCountChartOptions = {
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (context) => `${Number(context.raw)} fitur digunakan`,
      },
    },
  },
  scales: {
    x: {
      min: 0,
      max: 8,
      ticks: { color: '#8ea3b8', stepSize: 1 },
      grid: { color: 'rgba(150,175,198,.12)' },
      border: { display: false },
    },
    y: {
      ticks: { color: '#c0ccda' },
      grid: { display: false },
      border: { display: false },
    },
  },
}

const trainedAtLabel = computed(() => {
  const value = metrics.value?.trained_at
  if (!value) return 'Tidak tersedia'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('id-ID')
})

function navigateTo(page) {
  activePage.value = page
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function checkBackend() {
  try {
    health.value = await getHealth()
  } catch {
    health.value = {
      status: 'offline',
      model_ready: false,
      message: 'Backend belum terhubung. Pastikan Django berjalan pada port 8000.',
    }
  }
}

async function loadMetrics() {
  metricsLoading.value = true
  metricsError.value = ''
  try {
    const response = await fetch('/api/metrics/', {
      headers: { Accept: 'application/json' },
    })
    if (!response.ok) throw new Error(`Gagal mengambil metrik (HTTP ${response.status}).`)
    metrics.value = await response.json()
  } catch (error) {
    metricsError.value = error.message || 'Metrik model belum dapat dimuat.'
  } finally {
    metricsLoading.value = false
  }
}

async function explainChart(chartKey, predictionContext = null) {
  const insight = aiInsights[chartKey]
  if (!insight || insight.loading || insight.text) return

  insight.loading = true
  insight.error = ''
  insight.text = ''

  const payload = { chart_key: chartKey }
  if (chartKey === 'prediction_distribution' && predictionContext) {
    payload.overall_category = predictionContext.overall_category
    payload.predictions = predictionContext.predictions
  }

  try {
    const response = await fetch('/api/ai/explain/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(data?.detail || `Gagal meminta penjelasan AI (HTTP ${response.status}).`)
    }
    insight.text = data.explanation || 'Penjelasan AI belum tersedia.'
  } catch (error) {
    insight.error = error.message || 'Penjelasan AI tidak dapat dimuat. Coba lagi.'
  } finally {
    insight.loading = false
  }
}

function explainPredictionDistribution() {
  if (!result.value) return
  const predictionContext = {
    overall_category: result.value.overall_category,
    predictions: result.value.predictions.map((item) => ({
      key: item.key,
      label: item.label,
      value: Number(item.value),
      unit: item.unit,
      category: item.category,
    })),
  }
  explainChart('prediction_distribution', predictionContext)
}

async function submitPrediction() {
  errorMessage.value = ''
  result.value = null
  aiInsights.prediction_distribution.text = ''
  aiInsights.prediction_distribution.error = ''

  const missing = Object.entries(form).filter(([, value]) => value === '' || value === null)
  if (missing.length) {
    errorMessage.value = 'Lengkapi seluruh 8 input sebelum menjalankan prediksi.'
    return
  }

  const payload = Object.fromEntries(
    Object.entries(form).map(([key, value]) => [key, Number(value)]),
  )
  if (Object.values(payload).some((value) => !Number.isFinite(value))) {
    errorMessage.value = 'Pastikan semua input berupa angka yang valid.'
    return
  }

  loading.value = true
  try {
    result.value = await predictAirQuality(payload)
  } catch (error) {
    const data = error?.response?.data
    errorMessage.value = data?.detail || 'Prediksi gagal. Periksa backend dan format input.'
  } finally {
    loading.value = false
  }
}

function resetForm() {
  Object.keys(form).forEach((key) => { form[key] = '' })
  result.value = null
  errorMessage.value = ''
}

onMounted(() => {
  checkBackend()
  loadMetrics()
})
</script>

<template>
  <div class="app-shell">
    <div class="site-sticky-header">
      <div class="site-header-inner">
      <header class="topbar">
        <a class="brand" href="#top" aria-label="AirSense beranda" @click.prevent="navigateTo('home')">
          <span class="brand-mark"><span></span><span></span><span></span></span>
          <span>airsense<span class="brand-dot">.</span></span>
        </a>
        <div class="topbar-right">
          <span class="project-label">SISTEM PREDIKSI KUALITAS UDARA</span>
        </div>
      </header>

      <nav class="page-nav" aria-label="Navigasi utama">
        <button
          v-for="page in pages"
          :key="page.key"
          type="button"
          class="page-nav-button"
          :class="{ active: activePage === page.key }"
          :aria-current="activePage === page.key ? 'page' : undefined"
          @click="navigateTo(page.key)"
        >
          {{ page.label }}
        </button>
      </nav>
      </div>
    </div>

    <main id="top">
      <!-- PAGE 1: HOME -->
      <template v-if="activePage === 'home'">
        <section class="home-hero">
          <div class="home-hero-copy">
            <div class="home-hero-pretitle">
              <span class="home-hero-mark" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M3 8h11a3 3 0 1 0-2.8-4" />
                  <path d="M2 12h16a2.5 2.5 0 1 1-2.4 3.2" />
                  <path d="M4 16h6a2 2 0 1 1-1.8 2.8" />
                </svg>
              </span>
              <div class="eyebrow">PREDIKSI KUALITAS UDARA</div>
            </div>
            <h1>Understand the air.<br /><em>Predict what matters.</em></h1>
            <p class="home-lead">AirSense membantu memperkirakan konsentrasi polutan udara berdasarkan respons sensor kimia dan kondisi lingkungan menggunakan Machine Learning.</p>
            <p class="home-support">Masukkan data sensor, jalankan model prediksi, lalu pahami hasil estimasi melalui nilai numerik dan kategori kondisi udara.</p>
            <div class="home-hero-actions">
              <button class="home-primary-button" type="button" @click="navigateTo('prediction')">
                Mulai Prediksi <span>↗</span>
              </button>
              <button class="home-secondary-button" type="button" @click="navigateTo('guide')">
                Pelajari cara kerja
              </button>
            </div>
            <div class="home-hero-tags">
              <span>Pembacaan sensor</span>
              <span>Regresi ML</span>
              <span>Kondisi udara</span>
            </div>
          </div>
          <div class="hero-visual home-hero-visual" aria-hidden="true">
            <div class="orb orb-one"></div><div class="orb orb-two"></div><div class="orb orb-three"></div>
            <div class="orbit orbit-a"></div><div class="orbit orbit-b"></div>
            <div class="visual-core">
              <span class="core-ring"></span>
              <span class="core-leaf" aria-hidden="true">
                <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M7 17h22c5 0 8-3 8-7 0-3-2-5-5-5" />
                  <path d="M5 25h29c4 0 7 2 7 6s-3 6-6 6" />
                  <path d="M10 33h11" />
                </svg>
              </span>
            </div>
            <span class="visual-caption">SINYAL<br />ATMOSFER / 001</span>
          </div>
        </section>

        <section class="home-introduction">
          <div class="home-section-heading">
            <div class="eyebrow">TENTANG AIRSENSE</div>
            <h2>Apa itu <em>AirSense?</em></h2>
          </div>
          <div class="home-intro-copy">
            <p>AirSense adalah prototipe aplikasi prediksi kualitas udara berbasis Machine Learning. Sistem memanfaatkan lima respons sensor kimia serta tiga variabel lingkungan untuk memperkirakan konsentrasi empat polutan: CO, benzena, NOx, dan NO₂.</p>
            <p>AirSense bukan alat pengukur udara secara langsung dan tidak menyediakan pemantauan waktu nyata. Hasilnya merupakan estimasi model yang dilatih menggunakan dataset historis UCI Air Quality.</p>
          </div>
        </section>

        <section class="home-highlights">
          <article class="home-highlight-card">
            <span class="home-card-index">MASUKAN</span>
            <div class="home-card-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h3l2.2-6 4.2 12 2.2-6H21" /></svg>
            </div>
            <h3>Data sensor sebagai masukan</h3>
            <p>Gunakan lima respons sensor kimia dan tiga variabel lingkungan sesuai format dataset.</p>
          </article>
          <article class="home-highlight-card">
            <span class="home-card-index">PREDIKSI</span>
            <div class="home-card-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3a3 3 0 0 0-3 3v.5A3.5 3.5 0 0 0 4 13a3 3 0 0 0 2 5.5A3 3 0 0 0 9 21"/><path d="M15 3a3 3 0 0 1 3 3v.5A3.5 3.5 0 0 1 20 13a3 3 0 0 1-2 5.5A3 3 0 0 1 15 21"/><path d="M9 7h3m-3 5h6m-6 5h3M12 4v16"/></svg>
            </div>
            <h3>Empat model regresi</h3>
            <p>Model Random Forest memperkirakan konsentrasi CO, benzena, NOx, dan NO₂.</p>
          </article>
          <article class="home-highlight-card">
            <span class="home-card-index">INTERPRETASI</span>
            <div class="home-card-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19V5m0 14h17"/><path d="M8 15v-4m5 4V7m5 8V9"/><path d="m7 8 4-3 4 2 4-4"/></svg>
            </div>
            <h3>Hasil lebih mudah dipahami</h3>
            <p>Lihat estimasi numerik beserta kategori relatif Baik, Sedang, atau Buruk.</p>
          </article>
        </section>

        <section class="home-workflow-section">
          <div class="home-section-heading">
            <div class="eyebrow">CARA KERJA SISTEM</div>
            <h2>Dari pembacaan sensor<br /><em>menjadi estimasi.</em></h2>
          </div>
          <div class="home-workflow-grid">
            <div>
              <div class="workflow-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M4 17h16M8 7v6m8-6v10"/><circle cx="8" cy="15" r="2"/><circle cx="16" cy="11" r="2"/></svg></div>
              <span>MASUKAN</span><strong>Masukkan data</strong><p>Isi delapan nilai dari respons sensor dan kondisi lingkungan.</p>
            </div>
            <div>
              <div class="workflow-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 20 6v5c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6l8-3Z"/><path d="m8.5 12 2.3 2.3 4.8-5"/></svg></div>
              <span>PROSES</span><strong>Proses Machine Learning</strong><p>Django memvalidasi input dan meneruskan fitur yang sesuai ke setiap model regresi.</p>
            </div>
            <div>
              <div class="workflow-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19V5m0 14h16"/><path d="M8 15v-4m4 4V8m4 7V6"/></svg></div>
              <span>HASIL</span><strong>Pahami hasil</strong><p>AirSense menampilkan estimasi konsentrasi dan kategori relatif setiap polutan.</p>
            </div>
          </div>
        </section>

        <section class="home-dataset-note">
          <div>
            <div class="eyebrow">DATA & TRANSPARANSI</div>
            <h2>Berbasis dataset terbuka.</h2>
            <p>Model dikembangkan menggunakan UCI Air Quality, dataset historis pengukuran kualitas udara di Italia pada 2004–2005. Kategori internal AirSense bukan ISPU resmi.</p>
          </div>
          <button class="home-secondary-button" type="button" @click="navigateTo('performance')">Lihat evaluasi model <span>↗</span></button>
        </section>

        <section class="home-final-cta">
          <div>
            <span class="result-kicker">SIAP MEMULAI?</span>
            <h2>Mulai kenali hasil prediksi kualitas udara.</h2>
            <p>Masukkan data sensor dan lihat estimasi yang dihasilkan model AirSense.</p>
          </div>
          <button class="home-primary-button" type="button" @click="navigateTo('prediction')">Mulai Prediksi <span>↗</span></button>
        </section>
      </template>

      <!-- PAGE 2: RUANG PREDIKSI -->
      <template v-else-if="activePage === 'prediction'">
        <div class="page-intro prediction-page-intro">
          <div class="eyebrow"> RUANG PREDIKSI</div>
          <h1>Prediksi konsentrasi<br /><em>polutan udara.</em></h1>
          <p>Masukkan delapan nilai respons sensor dan kondisi lingkungan untuk memperoleh estimasi konsentrasi empat polutan dari model AirSense.</p>
        </div>

        <div class="notice">
          <span class="notice-icon">i</span>
          <span><strong>Prototipe edukasi.</strong> Kategori Baik/Sedang/Buruk merupakan kategori relatif berdasarkan distribusi target pada data latih, bukan ISPU resmi. Dataset UCI berasal dari pengukuran historis di Italia (2004–2005).</span>
        </div>

        <section class="workspace">
          <div class="section-heading">
            <div>
              <div class="eyebrow">RUANG PREDIKSI</div>
              <h2>Masukan pembacaan sensor</h2>
              <p>Isi delapan nilai sesuai skala dataset. Seluruh kolom wajib diisi.</p>
            </div>
          </div>

          <div v-if="!health.model_ready" class="backend-warning">
            <strong>Model belum siap.</strong> {{ health.message }}
            <span>Pelatihan model: <code>python ml/train_model.py</code> dari folder <code>backend</code>.</span>
          </div>

          <form class="input-panel" @submit.prevent="submitPrediction">
            <div class="panel-title">
              <div class="panel-index">A</div>
              <div><h3>Respons sensor kimia</h3><p>Lima sensor kimia dengan sasaran gas nominal yang berbeda.</p></div>
            </div>
            <div class="form-grid sensor-grid">
              <label v-for="field in sensorFields" :key="field.key" class="field">
                <span class="field-title">{{ field.title }}</span>
                <span class="field-description">{{ field.description }}</span>
                <span class="input-wrap">
                  <input v-model="form[field.key]" type="number" min="0" step="any" :placeholder="field.example" required />
                  <small>{{ field.unit }}</small>
                </span>
              </label>
            </div>
            <p class="field-footnote">a.u. = satuan arbitrer (arbitrary units). Nilai PT08 merupakan respons sensor pada dataset, bukan konsentrasi polutan secara langsung.</p>

            <div class="panel-divider"></div>
            <div class="panel-title">
              <div class="panel-index">B</div>
              <div><h3>Kondisi lingkungan</h3><p>Parameter suhu dan kelembapan saat pengambilan data.</p></div>
            </div>
            <div class="form-grid environment-grid">
              <label v-for="field in environmentFields" :key="field.key" class="field">
                <span class="field-title">{{ field.title }}</span>
                <span class="field-description">{{ field.description }}</span>
                <span class="input-wrap">
                  <input v-model="form[field.key]" type="number" :min="field.min" :max="field.max" :step="field.step" :placeholder="field.example" required />
                  <small>{{ field.unit }}</small>
                </span>
              </label>
            </div>
            <p class="field-footnote">Catatan AH: dokumentasi atribut UCI tidak mencantumkan satuan fisik. Masukkan nilai dalam skala asli dataset dan jangan mengonversinya ke satuan lain.</p>

            <div v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</div>
            <div class="form-actions">
              <button class="reset-button" type="button" @click="resetForm">Kosongkan formulir</button>
              <button class="predict-button" type="submit" :disabled="loading || !health.model_ready">
                <span>{{ loading ? 'Menghitung prediksi...' : 'Jalankan prediksi' }}</span><span class="button-arrow">↗</span>
              </button>
            </div>
          </form>
        </section>

        <section v-if="result" class="results-section">
          <div class="section-heading result-heading">
            <div><div class="eyebrow">HASIL PREDIKSI</div><h2>Hasil prediksi</h2><p>Estimasi konsentrasi berdasarkan input yang kamu berikan.</p></div>
          </div>

          <div class="result-overview" :class="categoryClass">
            <div>
              <span class="result-kicker">KONDISI RELATIF KESELURUHAN</span>
              <h3>{{ result.overall_category }}</h3>
              <p>Kategori keseluruhan mengikuti kategori terburuk dari empat polutan yang diprediksi.</p>
            </div>
            <div class="status-symbol">{{ result.overall_category === 'Baik' ? '✓' : result.overall_category === 'Sedang' ? '≈' : '!' }}</div>
          </div>

          <div class="result-layout prediction-result-layout">
            <div class="pollutant-list prediction-results-grid">
              <article v-for="item in result.predictions" :key="item.key" class="pollutant-card">
                <div class="pollutant-top"><span>{{ item.label }}</span><span class="mini-status" :class="item.category.toLowerCase()">{{ item.category }}</span></div>
                <div class="pollutant-value">{{ Number(item.value).toLocaleString('id-ID', { maximumFractionDigits: 3 }) }} <small>{{ item.unit }}</small></div>
                <p v-if="item.features_used" class="feature-used">Model menggunakan {{ item.features_used.length }} fitur masukan.</p>
              </article>
            </div>

            <div class="chart-panel prediction-category-panel">
              <div class="chart-heading">
                <div><span class="result-kicker">RINGKASAN KATEGORI</span><h3>Distribusi kategori polutan</h3></div>
                <span class="chart-count">{{ result.predictions.length }} polutan</span>
              </div>
              <div class="prediction-doughnut-wrap" role="img" aria-label="Diagram distribusi empat polutan berdasarkan kategori Baik, Sedang, dan Buruk">
                <Doughnut :data="predictionCategoryChartData" :options="predictionCategoryChartOptions" />
              </div>
              <p class="chart-footnote">Diagram menunjukkan jumlah polutan pada setiap kategori, bukan persentase kualitas udara atau indeks gabungan.</p>
              <button class="ai-explain-button" type="button" :disabled="aiInsights.prediction_distribution.loading || !!aiInsights.prediction_distribution.text" @click="explainPredictionDistribution">
                <span aria-hidden="true">✦</span>
                {{ aiInsights.prediction_distribution.loading ? 'AI sedang menganalisis…' : aiInsights.prediction_distribution.text ? 'Penjelasan tersedia' : 'Jelaskan grafik dengan AI' }}
              </button>
              <div v-if="aiInsights.prediction_distribution.text || aiInsights.prediction_distribution.error" class="ai-insight-panel" aria-live="polite">
                <div class="ai-insight-heading"><span aria-hidden="true">✦</span><strong>Penjelasan AI</strong><span>Groq</span></div>
                <p v-if="aiInsights.prediction_distribution.text">{{ aiInsights.prediction_distribution.text }}</p>
                <p v-if="aiInsights.prediction_distribution.error" class="ai-insight-error">{{ aiInsights.prediction_distribution.error }}</p>
              </div>
            </div>
          </div>
          <p class="result-disclaimer">{{ result.classification_note }} Nilai yang ditampilkan merupakan estimasi model, bukan hasil pembacaan alat secara langsung.</p>
        </section>
      </template>

      <!-- PAGE 3: EVALUASI MODEL -->
      <section v-else-if="activePage === 'performance'" class="content-page model-section">
        <div class="page-intro">
          <div class="eyebrow"> EVALUASI MODEL</div>
          <h1>Kenali performa<br /><em>model AirSense.</em></h1>
          <p>Halaman ini merangkum evaluasi empat model regresi menggunakan pembagian data kronologis 80:20 pada dataset UCI Air Quality.</p>
        </div>

        <div v-if="metricsLoading" class="metrics-message">Sedang memuat metrik evaluasi dari Django...</div>
        <div v-else-if="metricsError" class="metrics-message metrics-error">
          {{ metricsError }}
          <button class="inline-action" type="button" @click="loadMetrics">Coba lagi</button>
        </div>
        <template v-else-if="modelRows.length">
          <div class="model-metrics-layout">
            <div class="chart-panel performance-panel">
              <div class="chart-heading">
                <div><span class="result-kicker">SKOR R²</span><h3>Perbandingan R² empat model</h3></div>
                <span class="chart-count">Skala 0–1</span>
              </div>
              <div class="performance-chart-wrap"><Bar :data="performanceChartData" :options="performanceChartOptions" /></div>
              <p class="chart-footnote">R² menunjukkan proporsi variasi target yang dijelaskan model pada data uji. Nilai lebih tinggi menunjukkan kecocokan yang lebih baik pada pembagian data ini.</p>
              <button class="ai-explain-button" type="button" :disabled="aiInsights.r2_comparison.loading || !!aiInsights.r2_comparison.text" @click="explainChart('r2_comparison')">
                <span aria-hidden="true">✦</span>
                {{ aiInsights.r2_comparison.loading ? 'AI sedang menganalisis…' : aiInsights.r2_comparison.text ? 'Penjelasan tersedia' : 'Jelaskan grafik dengan AI' }}
              </button>
              <div v-if="aiInsights.r2_comparison.text || aiInsights.r2_comparison.error" class="ai-insight-panel" aria-live="polite">
                <div class="ai-insight-heading"><span aria-hidden="true">✦</span><strong>Penjelasan AI</strong><span>Groq</span></div>
                <p v-if="aiInsights.r2_comparison.text">{{ aiInsights.r2_comparison.text }}</p>
                <p v-if="aiInsights.r2_comparison.error" class="ai-insight-error">{{ aiInsights.r2_comparison.error }}</p>
              </div>
            </div>

            <div class="metric-table-panel">
              <div class="chart-heading">
                <div><span class="result-kicker">RINCIAN EVALUASI</span><h3>Ringkasan metrik</h3></div>
              </div>
              <div class="table-scroll">
                <table class="metrics-table">
                  <thead><tr><th>Target</th><th>Fitur</th><th>MAE</th><th>RMSE</th><th>R²</th></tr></thead>
                  <tbody>
                    <tr v-for="item in modelRows" :key="item.key">
                      <td>{{ item.label }}</td>
                      <td>{{ item.featureCount ?? '—' }}</td>
                      <td>{{ Number(item.mae).toFixed(3) }}</td>
                      <td>{{ Number(item.rmse).toFixed(3) }}</td>
                      <td>{{ Number(item.r2).toFixed(4) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p class="metric-note">MAE dan RMSE mengikuti satuan masing-masing target. Karena satuannya berbeda, nilai error antar-polutan tidak dibandingkan secara langsung.</p>
            </div>
          </div>

          <div class="model-extra-charts">
            <div class="chart-panel extra-performance-panel">
              <div class="chart-heading">
                <div><span class="result-kicker">PEMBAGIAN DATA</span><h3>Jumlah data latih dan uji</h3></div>
              </div>
              <div class="secondary-chart-wrap"><Bar :data="dataSplitChartData" :options="dataSplitChartOptions" /></div>
              <p class="chart-footnote">Jumlah baris valid untuk setiap target. Perbedaan jumlah terjadi karena tiap polutan memiliki missing value yang berbeda.</p>
              <button class="ai-explain-button" type="button" :disabled="aiInsights.data_split.loading || !!aiInsights.data_split.text" @click="explainChart('data_split')">
                <span aria-hidden="true">✦</span>
                {{ aiInsights.data_split.loading ? 'AI sedang menganalisis…' : aiInsights.data_split.text ? 'Penjelasan tersedia' : 'Jelaskan grafik dengan AI' }}
              </button>
              <div v-if="aiInsights.data_split.text || aiInsights.data_split.error" class="ai-insight-panel" aria-live="polite">
                <div class="ai-insight-heading"><span aria-hidden="true">✦</span><strong>Penjelasan AI</strong><span>Groq</span></div>
                <p v-if="aiInsights.data_split.text">{{ aiInsights.data_split.text }}</p>
                <p v-if="aiInsights.data_split.error" class="ai-insight-error">{{ aiInsights.data_split.error }}</p>
              </div>
            </div>

            <div class="chart-panel extra-performance-panel">
              <div class="chart-heading">
                <div><span class="result-kicker">PENGGUNAAN FITUR</span><h3>Jumlah fitur yang digunakan setiap model</h3></div>
                <span class="chart-count">Maksimal 8 fitur</span>
              </div>
              <div class="secondary-chart-wrap"><Bar :data="featureCountChartData" :options="featureCountChartOptions" /></div>
              <p class="chart-footnote">Benzena menggunakan satu fitur PT08.S2(NMHC), sedangkan model CO, NOx, dan NO₂ menggunakan delapan fitur.</p>
              <button class="ai-explain-button" type="button" :disabled="aiInsights.feature_usage.loading || !!aiInsights.feature_usage.text" @click="explainChart('feature_usage')">
                <span aria-hidden="true">✦</span>
                {{ aiInsights.feature_usage.loading ? 'AI sedang menganalisis…' : aiInsights.feature_usage.text ? 'Penjelasan tersedia' : 'Jelaskan grafik dengan AI' }}
              </button>
              <div v-if="aiInsights.feature_usage.text || aiInsights.feature_usage.error" class="ai-insight-panel" aria-live="polite">
                <div class="ai-insight-heading"><span aria-hidden="true">✦</span><strong>Penjelasan AI</strong><span>Groq</span></div>
                <p v-if="aiInsights.feature_usage.text">{{ aiInsights.feature_usage.text }}</p>
                <p v-if="aiInsights.feature_usage.error" class="ai-insight-error">{{ aiInsights.feature_usage.error }}</p>
              </div>
            </div>
          </div>

          <section class="model-detail-section">
            <div class="section-heading compact-heading">
              <div><div class="eyebrow">KONFIGURASI MODEL</div><h2>Konfigurasi setiap model</h2><p>Fitur yang benar-benar digunakan ketika masing-masing model dilatih.</p></div>
            </div>
            <div class="model-detail-grid">
              <article v-for="item in modelRows" :key="item.key" class="model-detail-card">
                <div class="model-detail-top"><h3>{{ item.label }}</h3><span>{{ item.featureCount }} fitur</span></div>
                <div class="feature-chip-list">
                  <span v-for="feature in item.featureColumns" :key="feature">{{ feature }}</span>
                </div>
                <div class="model-row-counts">
                  <span>Data latih <strong>{{ Number(item.trainRows || 0).toLocaleString('id-ID') }}</strong></span>
                  <span>Data uji <strong>{{ Number(item.testRows || 0).toLocaleString('id-ID') }}</strong></span>
                </div>
              </article>
            </div>
          </section>

          <section class="dataset-info-section">
            <div class="section-heading compact-heading">
              <div><div class="eyebrow">INFORMASI DATASET</div><h2>Informasi dataset</h2></div>
            </div>
            <div class="dataset-meta">
              <div><span>DATASET</span><strong>{{ metrics.dataset || 'UCI Air Quality' }}</strong></div>
              <div><span>BARIS SETELAH PEMBERSIHAN</span><strong>{{ Number(metrics.dataset_rows_after_blank_rows_removed).toLocaleString('id-ID') }}</strong></div>
              <div><span>JUMLAH VARIABEL INPUT</span><strong>{{ metrics.input_features?.length ?? 8 }} variabel</strong></div>
              <div><span>PELATIHAN TERAKHIR</span><strong>{{ trainedAtLabel }}</strong></div>
            </div>
            <p class="result-disclaimer">Metrik berasal dari pemisahan data kronologis 80:20. Setelah evaluasi, model untuk penggunaan aplikasi dilatih ulang menggunakan seluruh baris target yang valid. Kinerja pada data baru dapat berbeda. Dataset merupakan data historis dari Italia (2004–2005).</p>
          </section>
        </template>
        <div v-else class="metrics-message">Metrik model belum tersedia.</div>
      </section>

      <!-- PAGE 4: GUIDE -->
      <section v-else-if="activePage === 'guide'" class="content-page guide-section">
        <div class="page-intro">
          <div class="eyebrow"> PANDUAN AIRSENSE</div>
          <h1>Memahami cara<br /><em>AirSense bekerja.</em></h1>
          <p>Panduan singkat tentang alur prediksi, istilah sensor, nama senyawa, dan arti hasil yang ditampilkan aplikasi.</p>
        </div>

        <section class="guide-block">
          <div class="section-heading compact-heading">
            <div><div class="eyebrow">ALUR KERJA SISTEM</div><h2>Bagaimana sistem bekerja?</h2><p>Alur dimulai dari data sensor sampai menjadi estimasi konsentrasi polutan.</p></div>
          </div>
          <div class="workflow-grid">
            <article class="workflow-card"><span>MASUKAN</span><div class="workflow-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M4 17h16M8 7v6m8-6v10"/><circle cx="8" cy="15" r="2"/><circle cx="16" cy="11" r="2"/></svg></div><h3>Masukan sensor</h3><p>Pengguna memasukkan lima respons sensor kimia dan tiga parameter lingkungan.</p></article>
            <article class="workflow-card"><span>VALIDASI</span><div class="workflow-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 20 6v5c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6l8-3Z"/><path d="m8.5 12 2.3 2.3 4.8-5"/></svg></div><h3>Validasi Django</h3><p>Backend memeriksa format input dan menyiapkan fitur yang dibutuhkan masing-masing model.</p></article>
            <article class="workflow-card"><span>PREDIKSI</span><div class="workflow-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3a3 3 0 0 0-3 3v.5A3.5 3.5 0 0 0 4 13a3 3 0 0 0 2 5.5A3 3 0 0 0 9 21"/><path d="M15 3a3 3 0 0 1 3 3v.5A3.5 3.5 0 0 1 20 13a3 3 0 0 1-2 5.5A3 3 0 0 1 15 21"/><path d="M9 7h3m-3 5h6m-6 5h3M12 4v16"/></svg></div><h3>Prediksi ML</h3><p>Empat model Random Forest memperkirakan konsentrasi CO, benzena, NOx, dan NO₂.</p></article>
            <article class="workflow-card"><span>HASIL</span><div class="workflow-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19V5m0 14h16"/><path d="M8 15v-4m4 4V8m4 7V6"/></svg></div><h3>Hasil prediksi</h3><p>Aplikasi menampilkan nilai numerik, kategori relatif, dan satuan targetnya.</p></article>
          </div>
        </section>

        <section class="guide-block">
          <div class="section-heading compact-heading">
            <div><div class="eyebrow">ISTILAH SENSOR</div><h2>Mengenal sensor PT08</h2><p>Angka PT08 merupakan respons sensor, bukan konsentrasi polutan langsung.</p></div>
          </div>
          <div class="glossary-grid sensor-glossary">
            <article class="glossary-card"><div class="glossary-code">PT08.S1</div><h3>CO · Karbon monoksida (Carbon Monoxide)</h3><p>Respons sensor dengan target nominal karbon monoksida.</p></article>
            <article class="glossary-card"><div class="glossary-code">PT08.S2</div><h3>NMHC · Hidrokarbon non-metana (Non-Methane Hydrocarbons)</h3><p>Respons sensor dengan target nominal kelompok hidrokarbon selain metana.</p></article>
            <article class="glossary-card"><div class="glossary-code">PT08.S3</div><h3>NOx · Oksida nitrogen (Nitrogen Oxides)</h3><p>Respons sensor dengan target nominal kelompok oksida nitrogen.</p></article>
            <article class="glossary-card"><div class="glossary-code">PT08.S4</div><h3>NO₂ · Nitrogen dioksida (Nitrogen Dioxide)</h3><p>Respons sensor dengan target nominal nitrogen dioksida.</p></article>
            <article class="glossary-card"><div class="glossary-code">PT08.S5</div><h3>O₃ · Ozon (Ozone)</h3><p>Respons sensor dengan target nominal ozon.</p></article>
          </div>
          <p class="field-footnote">a.u. (arbitrary units) digunakan sebagai label skala respons. Nilai sensor tidak boleh dibaca sebagai mg/m³ atau ppb.</p>
        </section>

        <section class="guide-block">
          <div class="section-heading compact-heading">
            <div><div class="eyebrow">GLOSARIUM KIMIA</div><h2>Istilah polutan dan lingkungan</h2><p>Penjelasan istilah teknis yang muncul pada input maupun hasil prediksi.</p></div>
          </div>
          <div class="glossary-grid">
            <article v-for="item in glossary" :key="item.term" class="glossary-card">
              <div class="glossary-code">{{ item.term }}</div>
              <h3>{{ item.full }}</h3>
              <p>{{ item.explanation }}</p>
              <div class="glossary-role"><strong>Dalam AirSense</strong>{{ item.role }}</div>
            </article>
          </div>
        </section>

        <section class="guide-block category-guide">
          <div class="section-heading compact-heading">
            <div><div class="eyebrow">PENJELASAN KATEGORI</div><h2>Bagaimana membaca kategori?</h2><p>Kategori yang ditampilkan merupakan interpretasi internal prototipe.</p></div>
          </div>
          <div class="category-guide-grid">
            <article class="category-guide-card good"><span></span><div><h3>Baik</h3><p>Nilai prediksi berada pada kelompok kuantil bawah dari distribusi target data latih.</p></div></article>
            <article class="category-guide-card moderate"><span></span><div><h3>Sedang</h3><p>Nilai prediksi berada di antara batas kuantil bawah dan kuantil atas.</p></div></article>
            <article class="category-guide-card bad"><span></span><div><h3>Buruk</h3><p>Nilai prediksi berada pada kelompok kuantil atas dari distribusi target data latih.</p></div></article>
          </div>
          <div class="notice guide-notice"><span class="notice-icon">i</span><span><strong>Batasan penting.</strong> Kategori Baik/Sedang/Buruk saat ini ditentukan dari kuantil data latih per polutan. Kategori ini bukan ISPU, bukan standar ambang kesehatan resmi, dan tidak dapat digunakan sebagai diagnosis risiko kesehatan. Dataset UCI merupakan data historis dari satu lokasi di Italia pada 2004–2005.</span></div>
        </section>

        <section class="guide-block source-block">
          <div class="section-heading compact-heading">
            <div><div class="eyebrow">SUMBER DATA</div><h2>Sumber data dan teknologi</h2></div>
          </div>
          <div class="source-grid">
            <div><span>DATASET</span><strong>UCI Machine Learning Repository — Air Quality</strong><p>Data pengukuran kualitas udara historis dari Italia, Maret 2004 sampai April 2005.</p><a href="https://archive.ics.uci.edu/dataset/360/air+quality" target="_blank" rel="noreferrer">Lihat sumber dataset ↗</a></div>
            <div><span>TEKNOLOGI</span><strong>Django · Vue 3 · Scikit-learn</strong><p>Django menyediakan REST API, Vue menampilkan antarmuka, dan Scikit-learn menjalankan model regresi.</p></div>
          </div>
        </section>
      </section>
      <section v-else class="content-page">
        <div class="metrics-message">Halaman tidak ditemukan. <button class="inline-action" type="button" @click="navigateTo('home')">Kembali ke Beranda</button></div>
      </section>
    </main>

    <footer><button class="footer-home-link" type="button" @click="navigateTo('home')"><span class="brand footer-brand">airsense<span class="brand-dot">.</span></span></button><span>Prototipe edukasi · Django + Vue + Scikit-learn</span></footer>
  </div>
</template>