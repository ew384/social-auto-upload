import { http } from '@/utils/request'

// 账号管理相关API
export const accountApi = {
  // 获取有效账号列表
  getValidAccounts(forceCheck = false) {
    const params = forceCheck ? '?force=true' : '';
    return http.get(`/getValidAccounts${params}`)
  },

  // 添加账号
  addAccount(data) {
    return http.post('/account', data)
  },

  // 更新账号
  updateAccount(data) {
    return http.post('/updateUserinfo', data)
  },

  // 删除账号
  deleteAccount(id) {
    return http.get(`/deleteAccount?id=${id}`)
  }
}