// sau_frontend/src/stores/group.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useGroupStore = defineStore('group', () => {
    // 存储所有分组信息
    const groups = ref([])

    // 当前选中的分组ID
    const selectedGroupId = ref(null)

    // 平台颜色映射
    const platformColors = {
        1: '#FF2442', // 小红书
        2: '#07C160', // 视频号
        3: '#FE2C55', // 抖音
        4: '#FF6600'  // 快手
    }

    // 设置分组列表
    const setGroups = (groupsData) => {
        groups.value = groupsData || []
    }

    // 添加分组
    const addGroup = (group) => {
        if (group && group.id) {
            groups.value.push(group)
        }
    }

    // 更新分组
    const updateGroup = (id, updatedGroup) => {
        const index = groups.value.findIndex(group => group.id === id)
        if (index !== -1) {
            groups.value[index] = { ...groups.value[index], ...updatedGroup }
        }
    }

    // 删除分组
    const deleteGroup = (id) => {
        groups.value = groups.value.filter(group => group.id !== id)
    }

    // 根据ID获取分组
    const getGroupById = (id) => {
        return groups.value.find(group => group.id === id) || null
    }

    // 获取分组名称
    const getGroupName = (id) => {
        if (!id) return '未分组'
        const group = getGroupById(id)
        return group ? group.name : '未知分组'
    }

    // 获取分组颜色
    const getGroupColor = (id) => {
        if (!id) return '#94A3B8'
        const group = getGroupById(id)
        return group ? group.color : '#5B73DE'
    }

    // 获取分组图标
    const getGroupIcon = (id) => {
        if (!id) return 'Folder'
        const group = getGroupById(id)
        return group ? group.icon : 'Users'
    }

    // 设置选中的分组
    const setSelectedGroup = (groupId) => {
        selectedGroupId.value = groupId
    }

    // 清空选中的分组
    const clearSelectedGroup = () => {
        selectedGroupId.value = null
    }

    // 获取当前选中的分组
    const currentGroup = computed(() => {
        return selectedGroupId.value ? getGroupById(selectedGroupId.value) : null
    })

    // 分组统计信息
    const groupStats = computed(() => {
        return groups.value.map(group => ({
            id: group.id,
            name: group.name,
            description: group.description,
            color: group.color,
            icon: group.icon,
            accountCount: group.account_count || 0,
            sortOrder: group.sort_order || 0,
            createdAt: group.created_at,
            updatedAt: group.updated_at
        }))
    })

    // 获取默认分组
    const defaultGroup = computed(() => {
        return groups.value.find(group => group.name === '默认分组') || null
    })

    // 获取默认分组ID
    const defaultGroupId = computed(() => {
        const group = defaultGroup.value
        return group ? group.id : null
    })

    // 按排序顺序获取分组
    const sortedGroups = computed(() => {
        return [...groups.value].sort((a, b) => {
            const orderA = a.sort_order || 0
            const orderB = b.sort_order || 0
            if (orderA !== orderB) {
                return orderA - orderB
            }
            return a.name.localeCompare(b.name)
        })
    })

    // 检查分组是否存在
    const hasGroup = (id) => {
        return groups.value.some(group => group.id === id)
    }

    // 检查分组名称是否已存在
    const isGroupNameExists = (name, excludeId = null) => {
        return groups.value.some(group =>
            group.name === name && group.id !== excludeId
        )
    }

    // 获取分组总数
    const groupCount = computed(() => {
        return groups.value.length
    })

    // 获取有账号的分组数量
    const activeGroupCount = computed(() => {
        return groups.value.filter(group => (group.account_count || 0) > 0).length
    })

    // 重置所有状态
    const resetStore = () => {
        groups.value = []
        selectedGroupId.value = null
    }

    return {
        // 状态
        groups,
        selectedGroupId,
        platformColors,

        // 计算属性
        currentGroup,
        groupStats,
        defaultGroup,
        defaultGroupId,
        sortedGroups,
        groupCount,
        activeGroupCount,

        // 方法
        setGroups,
        addGroup,
        updateGroup,
        deleteGroup,
        getGroupById,
        getGroupName,
        getGroupColor,
        getGroupIcon,
        setSelectedGroup,
        clearSelectedGroup,
        hasGroup,
        isGroupNameExists,
        resetStore
    }
})