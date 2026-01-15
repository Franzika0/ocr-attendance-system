import { createApp } from 'vue'
import { createPinia } from 'pinia' // 引入 Pinia
import App from './App.vue'
import './style.css'

// 1. 建立 Vue 實例
const app = createApp(App)

// 2. 建立 Pinia 實例
const pinia = createPinia()

// 3. 掛載插件
app.use(pinia)

// 4. 掛載應用程式
app.mount('#app')