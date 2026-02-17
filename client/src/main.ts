import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import {
  ArrowDown,
  ArrowLeft,
  Calendar,
  Calendar as CalendarIcon,
  ChatDotRound,
  ChatLineRound,
  ChatLineSquare,
  Check,
  Clock,
  Coffee,
  Collection,
  Connection,
  Cpu,
  Delete,
  Document,
  Download,
  Edit,
  Expand,
  Fold,
  Key,
  Loading,
  Lock,
  Moon,
  Odometer,
  OfficeBuilding,
  Opportunity,
  Phone,
  Picture,
  Place,
  Plus,
  Postcard,
  Promotion,
  Reading,
  School,
  Search,
  Select,
  SetUp,
  Setting,
  Star,
  StarFilled,
  Sunny,
  SwitchButton,
  TrendCharts,
  Trophy,
  Upload,
  User,
  UserFilled,
  VideoCamera,
  VideoPause,
  Warning,
} from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './styles/reset.scss'
import './styles/accessibility.scss'

const app = createApp(App)
const pinia = createPinia()

const globalIcons = {
  ArrowDown,
  ArrowLeft,
  Calendar,
  CalendarIcon,
  ChatDotRound,
  ChatLineRound,
  ChatLineSquare,
  Check,
  Clock,
  Coffee,
  Collection,
  Connection,
  Cpu,
  Delete,
  Document,
  Download,
  Edit,
  Expand,
  Fold,
  Key,
  Loading,
  Lock,
  Moon,
  Odometer,
  OfficeBuilding,
  Opportunity,
  Phone,
  Picture,
  Place,
  Plus,
  Postcard,
  Promotion,
  Reading,
  School,
  Search,
  Select,
  SetUp,
  Setting,
  Star,
  StarFilled,
  Sunny,
  SwitchButton,
  TrendCharts,
  Trophy,
  Upload,
  User,
  UserFilled,
  VideoCamera,
  VideoPause,
  Warning,
}

for (const [key, component] of Object.entries(globalIcons)) {
  app.component(key, component)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
