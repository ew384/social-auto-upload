import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAccountStore = defineStore('account', () => {
  // 存储所有账号信息
  const accounts = ref([])

  // 平台类型映射
  const platformTypes = {
    1: '小红书',
    2: '视频号',
    3: '抖音',
    4: '快手'
  }

  // 设置账号列表（支持分组信息）
  const setAccounts = (accountsData) => {
    accounts.value = accountsData.map(item => {
      // 支持两种数据格式：原有的数组格式和新的对象格式
      if (Array.isArray(item)) {
        return {
          id: item[0],
          type: item[1],
          filePath: item[2],
          name: item[3],
          status: item[4] === 1 ? '正常' : '异常',
          platform: platformTypes[item[1]] || '未知',
          avatar: '/vite.svg',
          groupId: item[5] || null,
          groupName: item[6] || '未分组',
          groupColor: item[7] || '#5B73DE'
        }
      } else {
        return {
          id: item.id,
          type: item.type,
          filePath: item.filePath,
          name: item.userName,
          status: item.status === 1 ? '正常' : '异常',
          platform: platformTypes[item.type] || '未知',
          avatar: '/vite.svg',
          groupId: item.group_id,
          groupName: item.group_name || '未分组',
          groupColor: item.group_color || '#5B73DE'
        }
      }
    })
  }

  // 添加账号
  const addAccount = (account) => {
    accounts.value.push(account)
  }

  // 更新账号
  const updateAccount = (id, updatedAccount) => {
    const index = accounts.value.findIndex(acc => acc.id === id)
    if (index !== -1) {
      accounts.value[index] = { ...accounts.value[index], ...updatedAccount }
    }
  }

  // 删除账号
  const deleteAccount = (id) => {
    accounts.value = accounts.value.filter(acc => acc.id !== id)
  }

  // 根据分组获取账号
  const getAccountsByGroup = (groupId) => {
    return accounts.value.filter(acc => acc.groupId === groupId)
  }

  // 根据平台获取账号
  const getAccountsByPlatform = (platform) => {
    return accounts.value.filter(acc => acc.platform === platform)
  }

  // 移动账号到分组
  const moveAccountToGroup = (accountId, groupId, groupName, groupColor) => {
    const account = accounts.value.find(acc => acc.id === accountId)
    if (account) {
      account.groupId = groupId
      account.groupName = groupName
      account.groupColor = groupColor
    }
  }

  // 按分组分类的账号
  const accountsByGroup = computed(() => {
    const grouped = {}
    accounts.value.forEach(account => {
      const groupKey = account.groupId || 'ungrouped'
      if (!grouped[groupKey]) {
        grouped[groupKey] = {
          groupId: account.groupId,
          groupName: account.groupName,
          groupColor: account.groupColor,
          accounts: []
        }
      }
      grouped[groupKey].accounts.push(account)
    })
    return grouped
  })

  // 分组统计
  const groupStats = computed(() => {
    const stats = {}
    accounts.value.forEach(account => {
      const groupId = account.groupId || 'ungrouped'
      if (!stats[groupId]) {
        stats[groupId] = {
          total: 0,
          normal: 0,
          abnormal: 0,
          platforms: new Set()
        }
      }
      stats[groupId].total++
      if (account.status === '正常') {
        stats[groupId].normal++
      } else {
        stats[groupId].abnormal++
      }
      stats[groupId].platforms.add(account.platform)
    })

    // 转换 Set 为数组
    Object.values(stats).forEach(stat => {
      stat.platforms = Array.from(stat.platforms)
      stat.platformCount = stat.platforms.length
    })

    return stats
  })

  return {
    // 状态
    accounts,
    platformTypes,

    // 计算属性
    accountsByGroup,
    groupStats,

    // 方法
    setAccounts,
    addAccount,
    updateAccount,
    deleteAccount,
    getAccountsByGroup,
    getAccountsByPlatform,
    moveAccountToGroup
  }
})