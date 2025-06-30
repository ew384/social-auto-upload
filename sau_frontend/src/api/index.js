// sau_frontend/src/api/index.js - 更新版本
// API 统一导出
export * from './user'
export * from './account'
export * from './material'
export * from './group'  // 新增分组API导出

// 可以在这里添加其他API模块的导出
// export * from './product'
// export * from './order'
// export * from './common'

// sau_frontend/src/stores/index.js - 更新版本
import { createPinia } from 'pinia'
import { useUserStore } from './user'
import { useAccountStore } from './account'
import { useAppStore } from './app'
import { useGroupStore } from './group'  // 新增分组store导出

const pinia = createPinia()

export default pinia
export {
    useUserStore,
    useAccountStore,
    useAppStore,
    useGroupStore  // 新增分组store导出
}