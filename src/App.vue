<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAttendanceStore } from './stores/attendanceStore'

/**
 * 核心邏輯區塊
 * 對標 React Hooks 概念，處理資料流與外部 API
 */
const store = useAttendanceStore()

// 響應式狀態 (State)
const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const moodInput = ref('還不錯')
const isProcessing = ref(false)

// 1. 生命週期：初始化攝影機
onMounted(async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ 
      video: { width: 1280, height: 720 } 
    })
    if (videoRef.value) videoRef.value.srcObject = stream
  } catch (err) {
    ElMessage.error('無法取得攝影機權限，請確認瀏覽器設定')
  }
})

// 2. 拍照與上傳邏輯 (RPA 自動化核心)
const handleCapture = async () => {
  if (!videoRef.value || !canvasRef.value) return
  
  isProcessing.value = true
  const video = videoRef.value
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')

  // 繪製當前影像到隱藏的 Canvas
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  ctx?.drawImage(video, 0, 0, canvas.width, canvas.height)

  // 轉換為二進位 Blob 格式
  canvas.toBlob(async (blob) => {
    if (!blob) {
      isProcessing.value = false
      return
    }

    const formData = new FormData()
    formData.append('file', blob, 'student_card.png')
    formData.append('mood', moodInput.value)

    try {
      // 透過 Vite Proxy 發送到 FastAPI
      const response = await axios.post('/api/upload', formData)
      
      // 更新 Pinia 狀態管理
      store.addRecord(response.data)
      
      ElMessage.success({
        message: `打卡成功！歡迎回來，${response.data.name}`,
        duration: 5000
      })

      // 自動播放後端產生的 AI 語音回覆
      if (response.data.audio_endpoint) {
        const audio = new Audio(`http://127.0.0.1:8000${response.data.audio_endpoint}`)
        audio.play()
      }
    } catch (error) {
      ElMessage.error('辨識失敗，請確保學生證學號對準紅框區域')
    } finally {
      isProcessing.value = false
    }
  }, 'image/png')
}
</script>

<template>
  <div class="min-h-screen bg-slate-200 p-4 md:p-12 flex items-center justify-center font-sans">
    <canvas ref="canvasRef" class="hidden"></canvas>

    <div class="book-container relative w-full max-w-7xl flex flex-col md:flex-row shadow-2xl rounded-r-xl rounded-l-md overflow-hidden bg-white">
      
      <div class="page-left w-full md:w-1/2 p-8 border-r border-slate-200 relative">
        <div class="flex flex-col h-full">
          <div class="mb-6">
            <h1 class="text-2xl font-black text-slate-800 tracking-tighter">THE CHECK-IN DIARY</h1>
            <p class="text-xs text-slate-400 font-mono">2026 R&D SYSTEM LOG</p>
          </div>

          <div class="relative bg-black rounded-sm aspect-video shadow-inner overflow-hidden border-4 border-slate-100">
            <video ref="videoRef" autoplay class="w-full h-full object-cover"></video>
            <div class="roi-overlay">
              <div class="roi-label">POSITION ID HERE</div>
            </div>
          </div>

          <div class="mt-auto pt-8 space-y-4">
            <el-input 
              v-model="moodInput" 
              placeholder="Write your mood here..." 
              variant="unstyled"
              class="custom-diary-input"
            />
            <el-button 
              type="primary" 
              class="w-full h-14 text-lg font-bold rounded-none tracking-widest"
              :loading="isProcessing"
              @click="handleCapture"
            >
              EXECUTE OCR
            </el-button>
          </div>
        </div>
        
        <div class="absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-black/5 to-transparent pointer-events-none"></div>
      </div>

      <div class="page-right w-full md:w-1/2 p-8 bg-slate-50/50 relative">
        <div class="flex flex-col h-full">
          <div class="grid grid-cols-2 gap-4 mb-8">
            <div class="p-4 bg-white border border-slate-100 shadow-sm">
              <div class="text-[10px] text-slate-400 font-bold uppercase">Rate</div>
              <div class="text-2xl font-black text-blue-600">
                {{ Math.round((store.checkedInCount / store.totalExpected) * 100) }}%
              </div>
            </div>
            <div class="p-4 bg-white border border-slate-100 shadow-sm">
              <div class="text-[10px] text-slate-400 font-bold uppercase">Count</div>
              <div class="text-2xl font-black text-slate-800">
                {{ store.records.length }} <span class="text-xs text-slate-400">/ {{ store.totalExpected }}</span>
              </div>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto pr-2 custom-scrollbar">
            <h3 class="text-xs font-bold text-slate-400 mb-4 uppercase tracking-widest italic border-b pb-2">Recent Entries</h3>
            <el-empty v-if="store.records.length === 0" description="Awaiting data..." />
            
            <transition-group name="page-flip">
              <div 
                v-for="record in store.records" 
                :key="record.timestamp" 
                class="mb-6 pb-6 border-b border-slate-200 last:border-0"
              >
                <div class="flex justify-between items-center mb-2">
                  <span class="text-[10px] font-mono text-blue-500 bg-blue-50 px-2 py-0.5">{{ record.student_id }}</span>
                  <span class="text-[10px] text-slate-400 uppercase tracking-tighter">{{ record.timestamp }}</span>
                </div>
                <div class="text-lg font-serif italic text-slate-800 mb-2">{{ record.name }}</div>
                <div class="text-sm text-slate-500 leading-relaxed pl-4 border-l-2 border-slate-200">
                  "{{ record.ai_message }}"
                </div>
              </div>
            </transition-group>
          </div>
        </div>

        <div class="absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-black/5 to-transparent pointer-events-none"></div>
      </div>
    </div>
  </div>
</template>







<style scoped>
.book-container {
  min-height: 650px;
  /* 模擬書本厚度的側面陰影 */
  box-shadow: 
    30px 30px 60px -12px rgba(0, 0, 0, 0.25),
    -5px 0 15px -5px rgba(0, 0, 0, 0.1);
}

/* 模擬手寫筆記本的輸入框樣式 */
.custom-diary-input :deep(.el-input__wrapper) {
  box-shadow: none !important;
  border-bottom: 1px dashed #cbd5e1;
  border-radius: 0;
  padding: 0;
  background: transparent;
}

.custom-diary-input :deep(.el-input__inner) {
  font-family: 'Georgia', serif;
  font-style: italic;
  color: #1e293b;
  font-size: 1.1rem;
}

/* 翻頁進場效果 */
.page-flip-enter-active {
  transition: all 0.6s cubic-bezier(0.23, 1, 0.32, 1);
}
.page-flip-enter-from {
  opacity: 0;
  transform: rotateY(-20deg) translateX(50px);
  filter: blur(4px);
}

/* 原有的 ROI 邏輯保持不變，確保座標精準 */
.roi-overlay {
  position: absolute;
  left: 3.9%; top: 76.4%; width: 31.2%; height: 9.7%;
  border: 2px solid #3b82f6;
  z-index: 10;
  pointer-events: none;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.6);
}

.roi-label {
  position: absolute;
  top: -16px; left: 0;
  background: #3b82f6;
  color: white;
  font-size: 8px;
  padding: 0 4px;
}

.custom-scrollbar::-webkit-scrollbar { width: 3px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #e2e8f0; }
</style>