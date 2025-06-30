// sau_frontend/src/api/group.js
import { http } from '@/utils/request'

// 分组管理相关API
export const groupApi = {
    // 获取所有分组
    getAllGroups() {
        return http.get('/groups')
    },

    // 创建分组
    createGroup(data) {
        return http.post('/groups', data)
    },

    // 更新分组
    updateGroup(id, data) {
        return http.put(`/groups/${id}`, data)
    },

    // 删除分组
    deleteGroup(id) {
        return http.delete(`/groups/${id}`)
    },

    // 获取分组下的账号
    getGroupAccounts(groupId) {
        return http.get(`/groups/${groupId}/accounts`)
    },

    // 移动账号到分组
    moveAccountToGroup(accountId, groupId) {
        return http.put('/accounts/group', {
            account_id: accountId,
            group_id: groupId
        })
    },

    // 批量移动账号到分组
    batchMoveAccountsToGroup(accountIds, groupId) {
        return http.put('/accounts/batch-group', {
            account_ids: accountIds,
            group_id: groupId
        })
    },

    // 获取带分组信息的账号列表
    getAccountsWithGroups() {
        return http.get('/getValidAccountsWithGroups')
    }
}

// 更新 sau_frontend/src/api/account.js
import { http } from '@/utils/request'

// 账号管理相关API
export const accountApi = {
    // 获取有效账号列表
    getValidAccounts() {
        return http.get('/getValidAccounts')
    },

    // 获取带分组信息的账号列表
    getAccountsWithGroups() {
        return http.get('/getValidAccountsWithGroups')
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
    },

    // 移动账号到分组
    moveToGroup(accountId, groupId) {
        return http.put('/accounts/group', {
            account_id: accountId,
            group_id: groupId
        })
    },

    // 批量移动账号到分组
    batchMoveToGroup(accountIds, groupId) {
        return http.put('/accounts/batch-group', {
            account_ids: accountIds,
            group_id: groupId
        })
    }
}