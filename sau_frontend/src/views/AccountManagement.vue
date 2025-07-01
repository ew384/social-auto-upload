<template>
  <div class="account-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">账号管理</h1>
          <p class="page-subtitle">管理所有平台的账号信息，支持分组管理</p>
        </div>
        <div class="header-actions">
          <el-button @click="handleAddGroup" class="add-group-btn">
            <el-icon><FolderAdd /></el-icon>
            新建分组
          </el-button>
          <el-button type="primary" @click="handleAddAccount" class="add-btn">
            <el-icon><Plus /></el-icon>
            添加账号
          </el-button>
        </div>
      </div>
    </div>

    <!-- 分组管理标签页 -->
    <div class="group-tabs-section">
      <div class="tabs-header">
        <div class="tabs-nav">
          <div 
            v-for="tab in tabs" 
            :key="tab.key"
            :class="['tab-item', { active: activeTab === tab.key }]"
            @click="setActiveTab(tab.key)"
          >
            <el-icon><component :is="tab.icon" /></el-icon>
            <span>{{ tab.label }}</span>
            <el-badge v-if="tab.count > 0" :value="tab.count" />
          </div>
        </div>
        
        <div class="tabs-actions">
          <el-button @click="fetchData" :loading="appStore.isAccountRefreshing" class="refresh-btn">
            <el-icon :class="{ 'rotating': appStore.isAccountRefreshing }"><Refresh /></el-icon>
          </el-button>
          <el-dropdown v-if="activeTab !== 'overview'">
            <el-button class="more-btn">
              <el-icon><More /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleBatchOperation">批量操作</el-dropdown-item>
                <el-dropdown-item @click="handleExportData">导出数据</el-dropdown-item>
                <el-dropdown-item divided @click="handleGroupSettings">分组设置</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>

    <!-- 标签页内容 -->
    <div class="tab-content">
      <!-- 概览标签页 -->
      <div v-show="activeTab === 'overview'" class="overview-tab">
        <!-- 统计卡片 -->
        <div class="stats-section">
          <div class="stats-grid">
            <div class="stat-card total">
              <div class="stat-icon">
                <el-icon><User /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-number">{{ totalCount }}</div>
                <div class="stat-label">总账号数</div>
              </div>
            </div>

            <div class="stat-card normal">
              <div class="stat-icon">
                <el-icon><CircleCheckFilled /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-number">{{ normalCount }}</div>
                <div class="stat-label">正常账号</div>
              </div>
            </div>

            <div class="stat-card abnormal">
              <div class="stat-icon">
                <el-icon><WarningFilled /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-number">{{ abnormalCount }}</div>
                <div class="stat-label">异常账号</div>
              </div>
            </div>

            <div class="stat-card groups">
              <div class="stat-icon">
                <el-icon><Grid /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-number">{{ groupStore.groups.length }}</div>
                <div class="stat-label">分组数量</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 分组概览 -->
        <div class="groups-overview">
          <h3 class="section-title">分组概览</h3>
          <div class="groups-grid">
            <div 
              v-for="group in groupStore.groups" 
              :key="group.id"
              class="group-overview-card"
              @click="viewGroupDetail(group)"
            >
              <div class="group-header">
                <div class="group-icon" :style="{ backgroundColor: group.color }">
                  <el-icon><component :is="group.icon" /></el-icon>
                </div>
                <div class="group-info">
                  <h4 class="group-name">{{ group.name }}</h4>
                  <p class="group-desc">{{ group.description || '暂无描述' }}</p>
                </div>
              </div>
              
              <div class="group-stats">
                <div class="stat-item">
                  <span class="label">账号数</span>
                  <span class="value">{{ group.account_count || 0 }}</span>
                </div>
                <div class="stat-item">
                  <span class="label">正常率</span>
                  <span class="value">{{ getGroupHealthRate(group.id) }}%</span>
                </div>
              </div>

              <div class="group-actions">
                <el-button size="small" @click.stop="editGroup(group)">
                  <el-icon><Edit /></el-icon>
                  编辑
                </el-button>
              </div>
            </div>

            <!-- 新建分组卡片 -->
            <div class="group-overview-card add-group-card" @click="handleAddGroup">
              <div class="add-group-content">
                <el-icon class="add-icon"><Plus /></el-icon>
                <span>新建分组</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 分组详情标签页 -->
      <div v-show="activeTab !== 'overview'" class="group-detail-tab">
        <!-- 筛选工具栏 -->
        <div class="filter-toolbar">
          <div class="filter-left">
            <div class="filter-group">
              <el-select v-model="filterStatus" placeholder="账号状态" clearable class="filter-select">
                <el-option label="全部状态" value="" />
                <el-option label="正常" value="正常" />
                <el-option label="异常" value="异常" />
              </el-select>

              <el-select v-model="filterPlatform" placeholder="选择平台" clearable class="filter-select">
                <el-option label="全部平台" value="" />
                <el-option label="抖音" value="抖音" />
                <el-option label="快手" value="快手" />
                <el-option label="视频号" value="视频号" />
                <el-option label="小红书" value="小红书" />
              </el-select>
            </div>

            <div class="search-box">
              <el-input
                v-model="searchKeyword"
                placeholder="搜索账号名称..."
                clearable
                @input="handleSearch"
                class="search-input"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </div>
          </div>

          <div class="filter-right">
            <el-checkbox v-model="batchMode" v-if="activeTab !== 'overview'">批量操作</el-checkbox>
            <el-button v-if="batchMode && selectedAccounts.length > 0" @click="handleBatchMove">
              <el-icon><FolderOpened /></el-icon>
              移动分组 ({{ selectedAccounts.length }})
            </el-button>
          </div>
        </div>

        <!-- 账号列表 -->
        <div class="accounts-section">
          <div v-if="filteredAccounts.length > 0" class="accounts-grid">
            <div 
              v-for="account in filteredAccounts" 
              :key="account.id"
              :class="['account-card', { 
                'selected': selectedAccounts.includes(account.id),
                'batch-mode': batchMode 
              }]"
              @click="batchMode ? toggleAccountSelection(account) : null"
            >
              <!-- 批量选择框 -->
              <div v-if="batchMode" class="batch-checkbox">
                <el-checkbox 
                  :model-value="selectedAccounts.includes(account.id)"
                  @change="toggleAccountSelection(account)"
                />
              </div>

              <!-- 分组标识 -->
              <div :class="['group-badge', getPlatformClass(account.platform)]" :style="{ backgroundColor: account.groupColor }">
                <span class="group-name">{{ account.groupName }}</span>
              </div>

              <!-- 平台标识 -->
              <div :class="['platform-badge', getPlatformClass(account.platform)]">
                <component :is="getPlatformIcon(account.platform)" class="platform-icon" />
                <span class="platform-name">{{ account.platform }}</span>
              </div>

              <!-- 账号信息 -->
              <div class="account-info">
                <div class="account-avatar">
                  <el-avatar :size="48" :src="account.avatar" />
                  <div :class="['status-dot', account.status === '正常' ? 'online' : 'offline']"></div>
                </div>

                <div class="account-details">
                  <h3 class="account-name">{{ account.name }}</h3>
                  <div class="account-meta">
                    <el-tag 
                      :type="account.status === '正常' ? 'success' : 'danger'" 
                      size="small"
                      effect="light"
                    >
                      {{ account.status }}
                    </el-tag>
                  </div>
                </div>
              </div>

              <!-- 操作按钮 -->
              <div v-if="!batchMode" class="account-actions">
                <el-dropdown>
                  <el-button size="small" class="action-btn">
                    <el-icon><FolderOpened /></el-icon>
                    移动分组
                    <el-icon><ArrowDown /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item 
                        v-for="group in groupStore.groups" 
                        :key="group.id"
                        @click="moveAccountToGroup(account, group)"
                        :disabled="account.groupId === group.id"
                      >
                        <div class="group-option">
                          <div class="group-color" :style="{ backgroundColor: group.color }"></div>
                          <span>{{ group.name }}</span>
                          <el-icon v-if="account.groupId === group.id"><Check /></el-icon>
                        </div>
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>

                <el-button size="small" @click="handleEdit(account)" class="action-btn">
                  <el-icon><Edit /></el-icon>
                  编辑
                </el-button>
                
                <el-button 
                  size="small" 
                  type="danger" 
                  @click="handleDelete(account)"
                  class="action-btn danger"
                >
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-else class="empty-state">
            <div class="empty-content">
              <div class="empty-icon">
                <el-icon><UserFilled /></el-icon>
              </div>
              <h3 class="empty-title">
                {{ activeTab === 'overview' ? '暂无账号数据' : `${getCurrentGroupName()}暂无账号` }}
              </h3>
              <p class="empty-description">
                {{ searchKeyword || filterStatus || filterPlatform ? '没有找到符合条件的账号' : '还没有添加任何账号，点击上方按钮开始添加' }}
              </p>
              <el-button v-if="!searchKeyword && !filterStatus && !filterPlatform" type="primary" @click="handleAddAccount">
                <el-icon><Plus /></el-icon>
                添加第一个账号
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分组管理对话框 -->
    <el-dialog
      v-model="groupDialogVisible"
      :title="groupDialogType === 'add' ? '新建分组' : '编辑分组'"
      width="500px"
      class="group-dialog"
      :close-on-click-modal="false"
    >
      <div class="dialog-content">
        <el-form :model="groupForm" label-width="80px" :rules="groupRules" ref="groupFormRef">
          <el-form-item label="分组名称" prop="name">
            <el-input v-model="groupForm.name" placeholder="请输入分组名称" />
          </el-form-item>

          <el-form-item label="分组描述">
            <el-input 
              v-model="groupForm.description" 
              type="textarea" 
              :rows="3"
              placeholder="请输入分组描述（可选）" 
            />
          </el-form-item>

          <el-form-item label="分组颜色">
            <div class="color-picker-section">
              <el-color-picker v-model="groupForm.color" />
              <div class="preset-colors">
                <div 
                  v-for="color in presetColors" 
                  :key="color"
                  :class="['color-preset', { active: groupForm.color === color }]"
                  :style="{ backgroundColor: color }"
                  @click="groupForm.color = color"
                ></div>
              </div>
            </div>
          </el-form-item>

          <el-form-item label="分组图标">
            <el-select v-model="groupForm.icon" placeholder="选择图标">
              <el-option 
                v-for="icon in iconOptions" 
                :key="icon.value"
                :label="icon.label"
                :value="icon.value"
              >
                <div class="icon-option">
                  <el-icon><component :is="icon.value" /></el-icon>
                  <span>{{ icon.label }}</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="groupDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitGroupForm">
            {{ groupDialogType === 'add' ? '创建' : '更新' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 批量移动分组对话框 -->
    <el-dialog
      v-model="batchMoveDialogVisible"
      title="批量移动分组"
      width="400px"
      class="batch-move-dialog"
    >
      <div class="batch-move-content">
        <p>将选中的 {{ selectedAccounts.length }} 个账号移动到：</p>
        <el-select v-model="targetGroupId" placeholder="选择目标分组" style="width: 100%">
          <el-option 
            v-for="group in groupStore.groups" 
            :key="group.id"
            :label="group.name"
            :value="group.id"
          >
            <div class="group-option">
              <div class="group-color" :style="{ backgroundColor: group.color }"></div>
              <span>{{ group.name }}</span>
            </div>
          </el-option>
        </el-select>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="batchMoveDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmBatchMove" :disabled="!targetGroupId">
            确认移动
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 添加/编辑账号对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '添加账号' : '编辑账号'"
      width="480px"
      class="account-dialog"
      :close-on-click-modal="false"
    >
      <div class="dialog-content">
        <el-form :model="accountForm" label-width="80px" :rules="rules" ref="accountFormRef">
          <el-form-item label="平台" prop="platform">
            <el-select 
              v-model="accountForm.platform" 
              placeholder="请选择平台" 
              style="width: 100%"
              :disabled="dialogType === 'edit' || sseConnecting"
              class="platform-select"
            >
              <el-option 
                v-for="platform in platforms"
                :key="platform.name"
                :label="platform.name"
                :value="platform.name"
              >
                <div class="platform-option">
                  <component :is="platform.icon" :class="['platform-icon', platform.class]" />
                  <span>{{ platform.name }}</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>

          <el-form-item label="名称" prop="name">
            <el-input 
              v-model="accountForm.name" 
              placeholder="请输入账号名称" 
              :disabled="sseConnecting"
            />
          </el-form-item>

          <!-- 二维码显示区域 -->
          <div v-if="sseConnecting" class="qrcode-container">
            <div v-if="qrCodeData && !loginStatus" class="qrcode-wrapper">
              <div class="qrcode-header">
                <el-icon><Iphone /></el-icon>
                <span>扫码登录</span>
              </div>
              <p class="qrcode-tip">请使用{{ accountForm.platform }}APP扫描二维码登录</p>
              <div class="qrcode-frame">
                <img :src="qrCodeData" alt="登录二维码" class="qrcode-image" />
              </div>
            </div>
            
            <div v-else-if="!qrCodeData && !loginStatus" class="loading-wrapper">
              <el-icon class="loading-icon"><Loading /></el-icon>
              <span class="loading-text">正在生成二维码...</span>
            </div>
            
            <div v-else-if="loginStatus === '200'" class="success-wrapper">
              <el-icon class="success-icon"><CircleCheckFilled /></el-icon>
              <span class="success-text">登录成功</span>
            </div>
            
            <div v-else-if="loginStatus === '500'" class="error-wrapper">
              <el-icon class="error-icon"><CircleCloseFilled /></el-icon>
              <span class="error-text">登录失败，请重试</span>
            </div>
          </div>
        </el-form>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false" :disabled="sseConnecting">
            取消
          </el-button>
          <el-button 
            type="primary" 
            @click="submitAccountForm" 
            :loading="sseConnecting"
            :disabled="sseConnecting"
          >
            {{ sseConnecting ? '连接中...' : '确认' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from "vue";
import {
  Plus,
  Search,
  Refresh,
  More,
  User,
  Edit,
  Delete,
  FolderAdd,
  CircleCheckFilled,
  WarningFilled,
  Grid,
  UserFilled,
  FolderOpened,
  ArrowDown,
  Check,
  Iphone,
  Loading,
  CircleCloseFilled,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { accountApi } from "@/api/account";
import { groupApi } from "@/api/group";
import { useAccountStore } from "@/stores/account";
import { useGroupStore } from "@/stores/group";
import { useAppStore } from "@/stores/app";

// 状态管理
const accountStore = useAccountStore();
const groupStore = useGroupStore();
const appStore = useAppStore();

// 响应式数据
const activeTab = ref("overview");
const filterStatus = ref("");
const filterPlatform = ref("");
const searchKeyword = ref("");
const batchMode = ref(false);
const selectedAccounts = ref([]);

// 对话框状态
const groupDialogVisible = ref(false);
const groupDialogType = ref("add");
const batchMoveDialogVisible = ref(false);
const targetGroupId = ref("");

// 账号对话框相关
const dialogVisible = ref(false);
const dialogType = ref("add");
const accountFormRef = ref(null);
const sseConnecting = ref(false);
const qrCodeData = ref("");
const loginStatus = ref("");

// 表单数据
const groupFormRef = ref(null);
const groupForm = reactive({
  id: null,
  name: "",
  description: "",
  color: "#5B73DE",
  icon: "Users",
});

// 账号表单数据
const accountForm = reactive({
  id: null,
  name: "",
  platform: "",
  status: "正常",
});

// 平台配置
const platforms = [
  { name: "抖音", icon: "VideoCamera", class: "douyin" },
  { name: "快手", icon: "PlayTwo", class: "kuaishou" },
  { name: "视频号", icon: "MessageBox", class: "wechat" },
  { name: "小红书", icon: "Notebook", class: "xiaohongshu" },
];

// 预设颜色
const presetColors = [
  "#5B73DE",
  "#10B981",
  "#F59E0B",
  "#EF4444",
  "#8B5CF6",
  "#06B6D4",
  "#84CC16",
  "#F97316",
  "#EC4899",
  "#6B7280",
];

// 图标选项
const iconOptions = [
  { label: "用户组", value: "Users" },
  { label: "文件夹", value: "Folder" },
  { label: "工作", value: "Briefcase" },
  { label: "个人", value: "User" },
  { label: "团队", value: "UserFilled" },
  { label: "设置", value: "Setting" },
  { label: "标签", value: "Collection" },
];

// 表单验证规则
const groupRules = {
  name: [
    { required: true, message: "请输入分组名称", trigger: "blur" },
    { min: 1, max: 20, message: "长度在 1 到 20 个字符", trigger: "blur" },
  ],
};

// 账号表单验证规则
const rules = {
  platform: [{ required: true, message: "请选择平台", trigger: "change" }],
  name: [{ required: true, message: "请输入账号名称", trigger: "blur" }],
};

// 计算属性
const tabs = computed(() => {
  const baseTabs = [
    {
      key: "overview",
      label: "概览",
      icon: "DataAnalysis",
      count: 0,
    },
  ];

  groupStore.groups.forEach((group) => {
    const groupAccounts = accountStore.getAccountsByGroup(group.id);
    baseTabs.push({
      key: `group-${group.id}`,
      label: group.name,
      icon: group.icon,
      count: groupAccounts.length,
      groupId: group.id,
      color: group.color,
    });
  });

  return baseTabs;
});

const currentGroupId = computed(() => {
  if (activeTab.value === "overview") return null;
  const groupKey = activeTab.value.replace("group-", "");
  return parseInt(groupKey);
});

const filteredAccounts = computed(() => {
  let accounts = [];

  if (activeTab.value === "overview") {
    accounts = accountStore.accounts;
  } else {
    accounts = accountStore.getAccountsByGroup(currentGroupId.value);
  }

  if (filterStatus.value) {
    accounts = accounts.filter((acc) => acc.status === filterStatus.value);
  }

  if (filterPlatform.value) {
    accounts = accounts.filter((acc) => acc.platform === filterPlatform.value);
  }

  if (searchKeyword.value) {
    accounts = accounts.filter((acc) =>
      acc.name.toLowerCase().includes(searchKeyword.value.toLowerCase())
    );
  }

  return accounts;
});

const totalCount = computed(() => accountStore.accounts.length);
const normalCount = computed(
  () => accountStore.accounts.filter((acc) => acc.status === "正常").length
);
const abnormalCount = computed(
  () => accountStore.accounts.filter((acc) => acc.status === "异常").length
);

// 方法
const fetchData = async () => {
  if (appStore.isAccountRefreshing) return;

  appStore.setAccountRefreshing(true);

  try {
    // 获取分组数据
    const groupRes = await groupApi.getAllGroups();
    if (groupRes.code === 200) {
      groupStore.setGroups(groupRes.data);
    }

    // 获取账号数据
    const accountRes = await accountApi.getAccountsWithGroups();
    if (accountRes.code === 200) {
      accountStore.setAccounts(accountRes.data);
      ElMessage.success("数据刷新成功");
    }
  } catch (error) {
    console.error("获取数据失败:", error);
    ElMessage.error("获取数据失败");
  } finally {
    appStore.setAccountRefreshing(false);
  }
};

const setActiveTab = (tabKey) => {
  activeTab.value = tabKey;
  batchMode.value = false;
  selectedAccounts.value = [];
};

const getCurrentGroupName = () => {
  const currentGroup = groupStore.getGroupById(currentGroupId.value);
  return currentGroup ? currentGroup.name : "分组";
};

const getGroupHealthRate = (groupId) => {
  const groupAccounts = accountStore.getAccountsByGroup(groupId);
  if (groupAccounts.length === 0) return 100;

  const normalCount = groupAccounts.filter(
    (acc) => acc.status === "正常"
  ).length;
  return Math.round((normalCount / groupAccounts.length) * 100);
};

const handleAddGroup = () => {
  groupDialogType.value = "add";
  Object.assign(groupForm, {
    id: null,
    name: "",
    description: "",
    color: "#5B73DE",
    icon: "Users",
  });
  groupDialogVisible.value = true;
};

const editGroup = (group) => {
  groupDialogType.value = "edit";
  Object.assign(groupForm, { ...group });
  groupDialogVisible.value = true;
};

const submitGroupForm = () => {
  groupFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (groupDialogType.value === "add") {
          const res = await groupApi.createGroup(groupForm);
          if (res.code === 200) {
            ElMessage.success("分组创建成功");
            await fetchData();
            groupDialogVisible.value = false;
          }
        } else {
          const res = await groupApi.updateGroup(groupForm.id, groupForm);
          if (res.code === 200) {
            ElMessage.success("分组更新成功");
            await fetchData();
            groupDialogVisible.value = false;
          }
        }
      } catch (error) {
        console.error("分组操作失败:", error);
        ElMessage.error("操作失败");
      }
    }
  });
};

const viewGroupDetail = (group) => {
  setActiveTab(`group-${group.id}`);
};

const toggleAccountSelection = (account) => {
  const index = selectedAccounts.value.indexOf(account.id);
  if (index > -1) {
    selectedAccounts.value.splice(index, 1);
  } else {
    selectedAccounts.value.push(account.id);
  }
};

const handleBatchMove = () => {
  targetGroupId.value = "";
  batchMoveDialogVisible.value = true;
};

const confirmBatchMove = async () => {
  try {
    const res = await accountApi.batchMoveToGroup(
      selectedAccounts.value,
      targetGroupId.value
    );
    if (res.code === 200) {
      ElMessage.success(`成功移动${selectedAccounts.value.length}个账号`);
      await fetchData();
      batchMoveDialogVisible.value = false;
      selectedAccounts.value = [];
      batchMode.value = false;
    }
  } catch (error) {
    console.error("批量移动失败:", error);
    ElMessage.error("移动失败");
  }
};

const moveAccountToGroup = async (account, group) => {
  try {
    const res = await accountApi.moveToGroup(account.id, group.id);
    if (res.code === 200) {
      accountStore.moveAccountToGroup(
        account.id,
        group.id,
        group.name,
        group.color
      );
      ElMessage.success(`账号已移动到"${group.name}"`);
    }
  } catch (error) {
    console.error("移动账号失败:", error);
    ElMessage.error("移动失败");
  }
};

const handleSearch = () => {
  // 搜索逻辑已通过计算属性实现
};

const handleAddAccount = () => {
  dialogType.value = "add";
  Object.assign(accountForm, {
    id: null,
    name: "",
    platform: "",
    status: "正常",
  });
  sseConnecting.value = false;
  qrCodeData.value = "";
  loginStatus.value = "";
  dialogVisible.value = true;
};

const handleEdit = (account) => {
  dialogType.value = "edit";
  Object.assign(accountForm, { ...account });
  dialogVisible.value = true;
};

const handleDelete = (account) => {
  ElMessageBox.confirm(`确定要删除账号 ${account.name} 吗？`, "删除确认", {
    confirmButtonText: "确定删除",
    cancelButtonText: "取消",
    type: "warning",
  })
    .then(async () => {
      try {
        const response = await accountApi.deleteAccount(account.id);

        if (response.code === 200) {
          accountStore.deleteAccount(account.id);
          ElMessage.success("删除成功");
        } else {
          ElMessage.error(response.msg || "删除失败");
        }
      } catch (error) {
        console.error("删除账号失败:", error);
        ElMessage.error("删除账号失败");
      }
    })
    .catch(() => {});
};

// SSE连接相关
let eventSource = null;

const closeSSEConnection = () => {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
};

const connectSSE = (platform, name) => {
  closeSSEConnection();

  sseConnecting.value = true;
  qrCodeData.value = "";
  loginStatus.value = "";

  const platformTypeMap = {
    小红书: "1",
    视频号: "2",
    抖音: "3",
    快手: "4",
  };

  const type = platformTypeMap[platform] || "1";
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:5409";
  const url = `${baseUrl}/login?type=${type}&id=${encodeURIComponent(name)}`;

  eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    const data = event.data;
    console.log("SSE消息:", data);

    if (!qrCodeData.value && data.length > 100) {
      try {
        if (data.startsWith("data:image")) {
          qrCodeData.value = data;
        } else {
          qrCodeData.value = `data:image/png;base64,${data}`;
        }
      } catch (error) {
        console.error("处理二维码数据出错:", error);
      }
    } else if (data === "200" || data === "500") {
      loginStatus.value = data;

      if (data === "200") {
        setTimeout(() => {
          closeSSEConnection();
          setTimeout(() => {
            dialogVisible.value = false;
            sseConnecting.value = false;
            ElMessage.success("账号添加成功");
            fetchData();
          }, 1000);
        }, 1000);
      } else {
        closeSSEConnection();
        setTimeout(() => {
          sseConnecting.value = false;
          qrCodeData.value = "";
          loginStatus.value = "";
        }, 2000);
      }
    }
  };

  eventSource.onerror = (error) => {
    console.error("SSE连接错误:", error);
    ElMessage.error("连接服务器失败，请稍后再试");
    closeSSEConnection();
    sseConnecting.value = false;
  };
};

const submitAccountForm = () => {
  accountFormRef.value.validate(async (valid) => {
    if (valid) {
      if (dialogType.value === "add") {
        connectSSE(accountForm.platform, accountForm.name);
      } else {
        try {
          const res = await accountApi.updateAccount({
            id: accountForm.id,
            type: Number(
              accountForm.platform === "快手"
                ? 4
                : accountForm.platform === "抖音"
                ? 3
                : accountForm.platform === "视频号"
                ? 2
                : 1
            ),
            userName: accountForm.name,
          });
          if (res.code === 200) {
            accountStore.updateAccount(accountForm.id, accountForm);
            ElMessage.success("更新成功");
            dialogVisible.value = false;
            fetchData();
          } else {
            ElMessage.error(res.msg || "更新账号失败");
          }
        } catch (error) {
          console.error("更新账号失败:", error);
          ElMessage.error("更新账号失败");
        }
      }
    }
  });
};

const handleBatchOperation = () => {
  batchMode.value = !batchMode.value;
  if (!batchMode.value) {
    selectedAccounts.value = [];
  }
};

const handleExportData = () => {
  ElMessage.info("导出功能开发中...");
};

const handleGroupSettings = () => {
  ElMessage.info("分组设置功能开发中...");
};

const getPlatformClass = (platform) => {
  const classMap = {
    抖音: "douyin",
    快手: "kuaishou",
    视频号: "wechat",
    小红书: "xiaohongshu",
  };
  return classMap[platform] || "default";
};

const getPlatformIcon = (platform) => {
  const iconMap = {
    抖音: "VideoCamera",
    快手: "PlayTwo",
    视频号: "MessageBox",
    小红书: "Notebook",
  };
  return iconMap[platform] || "Platform";
};

// 生命周期
onMounted(() => {
  fetchData();
});

onBeforeUnmount(() => {
  closeSSEConnection();
});
</script>

<style lang="scss" scoped>
// 继承原有样式变量
$primary: #5b73de;
$success: #10b981;
$warning: #f59e0b;
$danger: #ef4444;
$info: #6b7280;

$platform-douyin: #fe2c55;
$platform-kuaishou: #ff6600;
$platform-xiaohongshu: #ff2442;
$platform-wechat: #07c160;

$bg-light: #f8fafc;
$bg-white: #ffffff;
$bg-gray: #f1f5f9;

$text-primary: #1e293b;
$text-secondary: #64748b;
$text-muted: #94a3b8;

$border-light: #e2e8f0;
$shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
$shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
  0 2px 4px -1px rgba(0, 0, 0, 0.06);
$shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1),
  0 4px 6px -2px rgba(0, 0, 0, 0.05);

$radius-sm: 4px;
$radius-md: 8px;
$radius-lg: 12px;
$radius-xl: 16px;

$space-xs: 4px;
$space-sm: 8px;
$space-md: 16px;
$space-lg: 24px;
$space-xl: 32px;
$space-2xl: 48px;

.account-management {
  max-width: 1400px;
  margin: 0 auto;
}

// 页面头部
.page-header {
  margin-bottom: $space-lg;

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;

    .header-left {
      .page-title {
        font-size: 28px;
        font-weight: 700;
        color: $text-primary;
        margin: 0 0 $space-xs 0;
      }

      .page-subtitle {
        font-size: 16px;
        color: $text-secondary;
        margin: 0;
      }
    }

    .header-actions {
      display: flex;
      gap: $space-sm;

      .add-group-btn,
      .add-btn {
        padding: 12px 24px;
        font-weight: 600;
        border-radius: $radius-lg;
        box-shadow: $shadow-md;
        transition: all 0.3s ease;

        &:hover {
          transform: translateY(-2px);
          box-shadow: $shadow-lg;
        }
      }
    }
  }
}

// 分组标签页
.group-tabs-section {
  margin-bottom: $space-lg;

  .tabs-header {
    background: $bg-white;
    border-radius: $radius-xl;
    padding: $space-md;
    box-shadow: $shadow-sm;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .tabs-nav {
      display: flex;
      gap: $space-xs;
      flex: 1;

      .tab-item {
        display: flex;
        align-items: center;
        gap: $space-sm;
        padding: 12px 20px;
        border-radius: $radius-lg;
        cursor: pointer;
        transition: all 0.3s ease;
        color: $text-secondary;
        font-weight: 500;
        position: relative;

        &:hover {
          background-color: $bg-gray;
          color: $text-primary;
        }

        &.active {
          background-color: $primary;
          color: white;
          box-shadow: $shadow-md;
        }

        .el-badge {
          :deep(.el-badge__content) {
            background-color: rgba(255, 255, 255, 0.9);
            color: $primary;
            border: none;
          }
        }

        &.active .el-badge {
          :deep(.el-badge__content) {
            background-color: rgba(255, 255, 255, 1);
            color: $primary;
          }
        }
      }
    }

    .tabs-actions {
      display: flex;
      gap: $space-sm;

      .refresh-btn,
      .more-btn {
        width: 40px;
        height: 40px;
        border-radius: $radius-md;
        display: flex;
        align-items: center;
        justify-content: center;

        .rotating {
          animation: rotate 1s linear infinite;
        }
      }
    }
  }
}

// 标签页内容
.tab-content {
  min-height: 600px;
}

// 概览标签页
.overview-tab {
  .stats-section {
    margin-bottom: $space-2xl;

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: $space-lg;

      .stat-card {
        background: $bg-white;
        border-radius: $radius-xl;
        padding: $space-lg;
        display: flex;
        align-items: center;
        gap: $space-md;
        box-shadow: $shadow-sm;
        transition: all 0.3s ease;

        &:hover {
          transform: translateY(-2px);
          box-shadow: $shadow-md;
        }

        .stat-icon {
          width: 48px;
          height: 48px;
          border-radius: $radius-lg;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;

          .el-icon {
            font-size: 24px;
            color: white;
          }
        }

        .stat-content {
          .stat-number {
            font-size: 24px;
            font-weight: 700;
            color: $text-primary;
            line-height: 1.2;
          }

          .stat-label {
            font-size: 14px;
            color: $text-secondary;
            margin-top: $space-xs;
          }
        }

        &.total .stat-icon {
          background: linear-gradient(135deg, $primary 0%, #8b9ee8 100%);
        }

        &.normal .stat-icon {
          background: linear-gradient(135deg, $success 0%, #34d399 100%);
        }

        &.abnormal .stat-icon {
          background: linear-gradient(135deg, $danger 0%, #f87171 100%);
        }

        &.groups .stat-icon {
          background: linear-gradient(135deg, $info 0%, #9ca3af 100%);
        }
      }
    }
  }

  .groups-overview {
    .section-title {
      font-size: 20px;
      font-weight: 600;
      color: $text-primary;
      margin: 0 0 $space-lg 0;
    }

    .groups-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: $space-lg;

      .group-overview-card {
        background: $bg-white;
        border-radius: $radius-xl;
        padding: $space-lg;
        box-shadow: $shadow-sm;
        transition: all 0.3s ease;
        cursor: pointer;

        &:hover {
          transform: translateY(-4px);
          box-shadow: $shadow-lg;
        }

        &.add-group-card {
          border: 2px dashed $border-light;
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 180px;

          .add-group-content {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: $space-md;
            color: $text-muted;
            font-weight: 500;

            .add-icon {
              font-size: 32px;
            }
          }

          &:hover {
            border-color: $primary;
            color: $primary;

            .add-group-content {
              color: $primary;
            }
          }
        }

        .group-header {
          display: flex;
          align-items: center;
          gap: $space-md;
          margin-bottom: $space-lg;

          .group-icon {
            width: 48px;
            height: 48px;
            border-radius: $radius-lg;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;

            .el-icon {
              font-size: 24px;
              color: white;
            }
          }

          .group-info {
            flex: 1;

            .group-name {
              font-size: 18px;
              font-weight: 600;
              color: $text-primary;
              margin: 0 0 $space-xs 0;
            }

            .group-desc {
              font-size: 14px;
              color: $text-secondary;
              margin: 0;
              line-height: 1.4;
            }
          }
        }

        .group-stats {
          display: flex;
          justify-content: space-between;
          margin-bottom: $space-lg;

          .stat-item {
            text-align: center;

            .label {
              display: block;
              font-size: 12px;
              color: $text-secondary;
              margin-bottom: $space-xs;
            }

            .value {
              display: block;
              font-size: 18px;
              font-weight: 700;
              color: $text-primary;
            }
          }
        }

        .group-actions {
          text-align: right;
        }
      }
    }
  }
}

// 筛选工具栏
.filter-toolbar {
  background: $bg-white;
  border-radius: $radius-lg;
  padding: $space-lg;
  margin-bottom: $space-lg;
  box-shadow: $shadow-sm;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: $space-md;

  .filter-left {
    display: flex;
    align-items: center;
    gap: $space-md;
    flex: 1;

    .filter-group {
      display: flex;
      gap: $space-sm;

      .filter-select {
        width: 140px;
      }
    }

    .search-box {
      .search-input {
        width: 280px;
      }
    }
  }

  .filter-right {
    display: flex;
    align-items: center;
    gap: $space-md;
  }
}

// 账号列表
.accounts-section {
  .accounts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: $space-lg;

    .account-card {
      background: $bg-white;
      border-radius: $radius-xl;
      padding: $space-lg;
      box-shadow: $shadow-sm;
      transition: all 0.3s ease;
      position: relative;
      overflow: hidden;
      border: 2px solid transparent;

      &:hover {
        transform: translateY(-4px);
        box-shadow: $shadow-lg;
      }

      &.batch-mode {
        cursor: pointer;

        &:hover {
          border-color: $primary;
        }

        &.selected {
          border-color: $primary;
          background-color: rgba(91, 115, 222, 0.05);
        }
      }

      .batch-checkbox {
        position: absolute;
        top: $space-md;
        right: $space-md;
        z-index: 10;
      }

      .group-badge {
        position: absolute;
        top: 0;
        left: 0;
        padding: $space-xs $space-md;
        border-radius: 0 0 $radius-lg 0;
        color: white;
        font-size: 12px;
        font-weight: 600;
        opacity: 0.9;

        .group-name {
          color: white;
        }
      }

      .platform-badge {
        position: absolute;
        top: 0;
        right: 0;
        padding: $space-xs $space-sm;
        border-radius: 0 $radius-xl 0 $radius-lg;
        display: flex;
        align-items: center;
        gap: $space-xs;
        font-size: 12px;
        font-weight: 600;
        color: white;

        .platform-icon {
          font-size: 14px;
        }

        &.douyin {
          background: linear-gradient(
            135deg,
            $platform-douyin 0%,
            #ff6b8a 100%
          );
        }

        &.kuaishou {
          background: linear-gradient(
            135deg,
            $platform-kuaishou 0%,
            #ff8533 100%
          );
        }

        &.wechat {
          background: linear-gradient(
            135deg,
            $platform-wechat 0%,
            #3dd68c 100%
          );
        }

        &.xiaohongshu {
          background: linear-gradient(
            135deg,
            $platform-xiaohongshu 0%,
            #ff5b75 100%
          );
        }
      }

      .account-info {
        display: flex;
        align-items: center;
        gap: $space-md;
        margin: $space-xl 0 $space-lg 0;

        .account-avatar {
          position: relative;

          .status-dot {
            position: absolute;
            bottom: 2px;
            right: 2px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: 2px solid white;

            &.online {
              background-color: $success;
            }

            &.offline {
              background-color: $danger;
            }
          }
        }

        .account-details {
          flex: 1;

          .account-name {
            font-size: 16px;
            font-weight: 600;
            color: $text-primary;
            margin: 0 0 $space-xs 0;
          }

          .account-meta {
            display: flex;
            align-items: center;
            gap: $space-xs;
          }
        }
      }

      .account-actions {
        display: flex;
        gap: $space-sm;
        flex-wrap: wrap;

        .action-btn {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: $space-xs;
          border-radius: $radius-md;
          font-weight: 500;
          min-width: 80px;

          &.danger {
            &:hover {
              background-color: $danger;
              border-color: $danger;
              color: white;
            }
          }
        }
      }
    }
  }

  .empty-state {
    background: $bg-white;
    border-radius: $radius-xl;
    padding: $space-2xl;
    text-align: center;
    box-shadow: $shadow-sm;

    .empty-content {
      max-width: 400px;
      margin: 0 auto;

      .empty-icon {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: linear-gradient(135deg, $bg-gray 0%, #e2e8f0 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto $space-lg;

        .el-icon {
          font-size: 32px;
          color: $text-muted;
        }
      }

      .empty-title {
        font-size: 20px;
        font-weight: 600;
        color: $text-primary;
        margin: 0 0 $space-sm 0;
      }

      .empty-description {
        font-size: 14px;
        color: $text-secondary;
        line-height: 1.5;
        margin: 0 0 $space-lg 0;
      }
    }
  }
}

// 对话框样式
.group-dialog {
  .dialog-content {
    padding: $space-md 0;

    .color-picker-section {
      display: flex;
      align-items: center;
      gap: $space-md;

      .preset-colors {
        display: flex;
        gap: $space-xs;

        .color-preset {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          cursor: pointer;
          border: 2px solid transparent;
          transition: all 0.3s ease;

          &:hover {
            transform: scale(1.1);
          }

          &.active {
            border-color: $text-primary;
            transform: scale(1.1);
          }
        }
      }
    }

    .icon-option {
      display: flex;
      align-items: center;
      gap: $space-sm;
    }
  }
}

.batch-move-dialog {
  .batch-move-content {
    padding: $space-md 0;

    p {
      margin-bottom: $space-md;
      color: $text-secondary;
    }

    .group-option {
      display: flex;
      align-items: center;
      gap: $space-sm;

      .group-color {
        width: 12px;
        height: 12px;
        border-radius: 50%;
      }
    }
  }
}

// 下拉菜单中的分组选项
:deep(.el-dropdown-menu) {
  .group-option {
    display: flex;
    align-items: center;
    gap: $space-sm;
    width: 100%;

    .group-color {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    span {
      flex: 1;
    }

    .el-icon {
      color: $success;
    }
  }
}

// 动画效果
@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// 响应式设计
@media (max-width: 1200px) {
  .accounts-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)) !important;
  }

  .groups-grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)) !important;
  }
}

@media (max-width: 768px) {
  .account-management {
    padding: 0 $space-md;
  }

  .page-header .header-content {
    flex-direction: column;
    align-items: stretch;
    gap: $space-md;
  }

  .tabs-header {
    flex-direction: column;
    gap: $space-md;

    .tabs-nav {
      overflow-x: auto;
      flex-wrap: nowrap;
    }
  }

  .filter-toolbar {
    flex-direction: column;
    align-items: stretch;

    .filter-left {
      flex-direction: column;
      align-items: stretch;

      .filter-group {
        flex-direction: column;

        .filter-select {
          width: 100%;
        }
      }

      .search-box .search-input {
        width: 100%;
      }
    }

    .filter-right {
      justify-content: center;
    }
  }

  .accounts-grid {
    grid-template-columns: 1fr !important;
  }

  .groups-grid {
    grid-template-columns: 1fr !important;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }

  .account-card .account-actions {
    flex-direction: column;

    .action-btn {
      width: 100%;
    }
  }
}
</style>