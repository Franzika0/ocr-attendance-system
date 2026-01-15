import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 定義打卡紀錄的型別，這展現了 TypeScript 的嚴謹性
interface AttendanceRecord {
  student_id: string
  name: string
  mood_input: string
  ai_message: string
  timestamp: string
}

export const useAttendanceStore = defineStore('attendance', () => {
  // 1. State: 存放所有紀錄
  const records = ref<AttendanceRecord[]>([])

  // 2. State: 預期總人數 (可以用於儀表板)
  const totalExpected = ref(50)

  // 3. Getters: 計算已報到人數 (對標 React useMemo)
  const checkedInCount = computed(() => records.value.length)

  // 4. Actions: 新增紀錄 (對標 Redux Action)
  function addRecord(data: AttendanceRecord) {
    // 將最新紀錄塞到陣列最前面
    records.value.unshift(data)
  }

  return { records, totalExpected, checkedInCount, addRecord }
})