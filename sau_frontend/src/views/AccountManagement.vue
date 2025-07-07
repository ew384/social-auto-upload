<template>
  <div class="account-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">账号管理</h1>
          <p class="page-subtitle">管理所有平台的账号信息</p>
        </div>
        <div class="header-actions">
          <el-button 
            v-if="activeTab === 'accounts'"
            type="primary" 
            @click="handleAddAccount" 
            class="add-btn"
          >
            <el-icon><Plus /></el-icon>
            添加账号
          </el-button>
          <el-button 
            v-if="activeTab === 'groups'"
            type="primary" 
            @click="handleAddGroup" 
            class="add-btn"
          >
            <el-icon><Plus /></el-icon>
            创建分组
          </el-button>
        </div>
      </div>
    </div>

    <!-- 标签页切换 -->
    <div class="tabs-container">
      <!-- 自定义标签页按钮 -->
      <div class="simple-tabs">
        <div class="tabs-header">
          <div 
            :class="['tab-item', { active: activeTab === 'accounts' }]"
            @click="activeTab = 'accounts'"
          >
            账号管理
          </div>
          <div 
            :class="['tab-item', { active: activeTab === 'groups' }]"
            @click="activeTab = 'groups'"
          >
            分组管理
          </div>
        </div>
      </div>

      <!-- 内容区域 -->
      <div class="tab-content">
        <!-- 账号管理内容 -->
        <div v-show="activeTab === 'accounts'" class="accounts-content">
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

                <!-- 分组筛选 -->
                <el-select v-model="filterGroup" placeholder="选择分组" clearable class="filter-select">
                  <el-option label="全部分组" value="" />
                  <el-option label="未分组" value="ungrouped" />
                  <el-option 
                    v-for="group in accountStore.groups"
                    :key="group.id"
                    :label="group.name"
                    :value="group.id"
                  />
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
              <el-button @click="fetchAccounts" :loading="appStore.isAccountRefreshing" class="refresh-btn">
                <el-icon :class="{ 'rotating': appStore.isAccountRefreshing }"><Refresh /></el-icon>
              </el-button>
              <el-dropdown>
                <el-button class="more-btn">
                  <el-icon><More /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item>批量操作</el-dropdown-item>
                    <el-dropdown-item>导出数据</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>

          <!-- 统计卡片 -->
          <div class="stats-section">
            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-icon total">
                  <el-icon><User /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-number">{{ totalCount }}</div>
                  <div class="stat-label">总账号数</div>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon normal">
                  <el-icon><CircleCheckFilled /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-number">{{ normalCount }}</div>
                  <div class="stat-label">正常账号</div>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon abnormal">
                  <el-icon><WarningFilled /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-number">{{ abnormalCount }}</div>
                  <div class="stat-label">异常账号</div>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon platforms">
                  <el-icon><Grid /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-number">{{ platformCount }}</div>
                  <div class="stat-label">覆盖平台</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 账号列表 -->
          <div class="accounts-section">
            <div v-if="filteredAccounts.length > 0" class="accounts-grid">
              <div 
                v-for="account in filteredAccounts" 
                :key="account.id"
                class="account-card"
              >
                <!-- 账号信息 -->
                <div class="account-info">
                  <div class="avatar-container">
                    <div class="account-avatar">
                      <el-avatar :size="56" :src="account.avatar || ''" />
                    </div>
                    <div class="platform-logo">
                      <img :src="getPlatformLogo(account.platform)" :alt="account.platform" />
                    </div>
                    <div :class="['status-dot', account.status === '正常' ? 'online' : 'offline']"></div>
                  </div>

                  <div class="account-details">
                    <h3 class="account-name">{{ account.name }}</h3>
                    <div class="account-meta">
                      <span class="platform-text">{{ account.platform }}</span>
                      <!-- 分组信息 -->
                      <el-tag 
                        v-if="account.group_name"
                        :color="account.group_color"
                        size="small"
                        effect="light"
                        class="group-tag"
                      >
                        {{ account.group_name }}
                      </el-tag>
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
                <div class="account-actions">
                  <el-button size="small" @click="handleEdit(account)" class="action-btn" title="编辑">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                  <el-button 
                    size="small" 
                    type="danger" 
                    @click="handleDelete(account)"
                    class="action-btn danger"
                    title="删除"
                  >
                    <el-icon><Delete /></el-icon>
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
                <h3 class="empty-title">暂无账号数据</h3>
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

        <!-- 分组管理内容 -->
        <div v-show="activeTab === 'groups'" class="groups-content">
          <!-- 分组统计 -->
          <div class="groups-stats">
            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-icon total">
                  <el-icon><Collection /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-number">{{ accountStore.groups.length }}</div>
                  <div class="stat-label">总分组数</div>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon normal">
                  <el-icon><User /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-number">{{ ungroupedAccounts.length }}</div>
                  <div class="stat-label">未分组账号</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 分组列表 -->
          <div class="groups-list">
            <!-- 未分组区域 -->
            <div class="group-card ungrouped">
              <div class="group-header">
                <div class="group-info">
                  <div class="group-icon">
                    <el-icon><User /></el-icon>
                  </div>
                  <div class="group-details">
                    <h3 class="group-name">未分组账号</h3>
                    <p class="group-description">{{ ungroupedAccounts.length }} 个账号</p>
                  </div>
                </div>
              </div>
              
              <div class="group-accounts" v-if="ungroupedAccounts.length > 0">
                <div 
                  v-for="account in ungroupedAccounts"
                  :key="account.id"
                  class="group-account-item"
                  draggable="true"
                  @dragstart="handleDragStart(account, $event)"
                  @dragend="handleDragEnd"
                >
                  <el-avatar :size="32" :src="account.avatar" />
                  <div class="account-info">
                    <span class="account-name">{{ account.name }}</span>
                    <span class="account-platform">{{ account.platform }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 分组区域 -->
            <div 
              v-for="group in accountStore.groups"
              :key="group.id"
              class="group-card"
              @dragover="handleDragOver"
              @dragleave="handleDragLeave"
              @drop="handleDrop(group.id, $event)"
            >
              <div class="group-header">
                <div class="group-info">
                  <div class="group-icon" :style="{ backgroundColor: group.color }">
                    <el-icon><component :is="getGroupIcon(group.icon)" /></el-icon>
                  </div>
                  <div class="group-details">
                    <h3 class="group-name">{{ group.name }}</h3>
                    <p class="group-description">{{ group.description || `${getAccountsByGroup(group.id).length} 个账号` }}</p>
                  </div>
                </div>
                
                <div class="group-actions">
                  <el-button size="small" text @click="handleEditGroup(group)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                  <el-button size="small" text type="danger" @click="handleDeleteGroup(group)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
              
              <div class="group-accounts" v-if="getAccountsByGroup(group.id).length > 0">
                <div 
                  v-for="account in getAccountsByGroup(group.id)"
                  :key="account.id"
                  class="group-account-item"
                  draggable="true"
                  @dragstart="handleDragStart(account, $event)"
                  @dragend="handleDragEnd"
                >
                  <el-avatar :size="32" :src="account.avatar" />
                  <div class="account-info">
                    <span class="account-name">{{ account.name }}</span>
                    <span class="account-platform">{{ account.platform }}</span>
                  </div>
                  <el-button 
                    size="small" 
                    text 
                    @click="moveAccountToGroup(account.id, null)"
                    title="移出分组"
                    class="remove-btn"
                  >
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
              </div>
              
              <div v-else class="group-empty">
                <span>拖拽账号到此分组</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

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
              />

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

    <!-- 分组管理对话框 -->
    <el-dialog
      v-model="groupDialogVisible"
      :title="groupDialogType === 'add' ? '创建分组' : '编辑分组'"
      width="480px"
      class="group-dialog"
    >
      <el-form :model="groupForm" label-width="80px" :rules="groupRules" ref="groupFormRef">
        <el-form-item label="分组名称" prop="name">
          <el-input v-model="groupForm.name" placeholder="请输入分组名称" />
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input 
            v-model="groupForm.description" 
            type="textarea" 
            :rows="2"
            placeholder="请输入分组描述（可选）" 
          />
        </el-form-item>
        
        <el-form-item label="颜色">
          <el-color-picker v-model="groupForm.color" />
        </el-form-item>
        
        <el-form-item label="图标">
          <el-select v-model="groupForm.icon" placeholder="选择图标">
            <el-option 
              v-for="icon in groupIcons"
              :key="icon"
              :label="icon"
              :value="icon"
            >
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-icon><component :is="getGroupIcon(icon)" /></el-icon>
                <span>{{ icon }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="groupDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitGroupForm">
            {{ groupDialogType === 'add' ? '创建' : '更新' }}
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
  CircleCheckFilled,
  WarningFilled,
  Grid,
  UserFilled,
  Iphone,
  Loading,
  CircleCloseFilled,
  VideoCamera,
  VideoPlay,
  Message,
  Document,
  Collection,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { accountApi } from "@/api/account";
import { useAccountStore } from "@/stores/account";
import { useAppStore } from "@/stores/app";

// 状态管理
const accountStore = useAccountStore();
const appStore = useAppStore();

// 筛选和搜索
const filterStatus = ref("");
const filterPlatform = ref("");
const searchKeyword = ref("");

// 平台配置
const platforms = [
  { name: "抖音", icon: "VideoCamera", class: "douyin" },
  { name: "快手", icon: "PlayTwo", class: "kuaishou" },
  { name: "视频号", icon: "MessageBox", class: "wechat" },
  { name: "小红书", icon: "Notebook", class: "xiaohongshu" },
];

// 对话框相关
const dialogVisible = ref(false);
const dialogType = ref("add");
const accountFormRef = ref(null);
const sseConnecting = ref(false);
const qrCodeData = ref("");
const loginStatus = ref("");

// 表单数据
const accountForm = reactive({
  id: null,
  name: "",
  platform: "",
  status: "正常",
});

// 表单验证规则
const rules = {
  platform: [{ required: true, message: "请选择平台", trigger: "change" }],
  name: [{ required: true, message: "请输入账号名称", trigger: "blur" }],
};

// 计算属性
const activeTab = ref("accounts");

// 新增：分组筛选
const filterGroup = ref("");

// 修改筛选逻辑
const filteredAccounts = computed(() => {
  let accounts = accountStore.accounts;

  if (filterStatus.value) {
    accounts = accounts.filter((acc) => acc.status === filterStatus.value);
  }

  if (filterPlatform.value) {
    accounts = accounts.filter((acc) => acc.platform === filterPlatform.value);
  }

  // 新增：分组筛选
  if (filterGroup.value) {
    if (filterGroup.value === "ungrouped") {
      accounts = accounts.filter((acc) => !acc.group_id);
    } else {
      accounts = accounts.filter((acc) => acc.group_id === filterGroup.value);
    }
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
const platformCount = computed(() => {
  const platforms = new Set(accountStore.accounts.map((acc) => acc.platform));
  return platforms.size;
});

const fetchAccounts = async (forceCheck = false) => {
  if (appStore.isAccountRefreshing) return;

  appStore.setAccountRefreshing(true);

  try {
    // 先尝试使用新API，如果失败则回退到旧API
    let res;
    try {
      res = await accountApi.getAccountsWithGroups(forceCheck);
    } catch (error) {
      console.warn("新API不可用，回退到旧API:", error);
      res = await accountApi.getValidAccounts(forceCheck);
    }

    if (res.code === 200 && res.data) {
      accountStore.setAccounts(res.data);

      // 同时获取分组信息
      try {
        const groupsRes = await accountApi.getGroups();
        if (groupsRes.code === 200 && groupsRes.data) {
          accountStore.setGroups(groupsRes.data);
        }
      } catch (error) {
        console.warn("获取分组信息失败:", error);
      }

      if (forceCheck) {
        ElMessage.success("账号数据刷新成功");
      } else {
        ElMessage.success("账号数据加载成功");
      }
      if (appStore.isFirstTimeAccountManagement) {
        appStore.setAccountManagementVisited();
      }
    } else {
      ElMessage.error("获取账号数据失败");
    }
  } catch (error) {
    console.error("获取账号数据失败:", error);
    ElMessage.error("获取账号数据失败");
  } finally {
    appStore.setAccountRefreshing(false);
  }
};
const getPlatformLogo = (platform) => {
  const logoMap = {
    抖音: "/src/assets/logos/douyin.png",
    快手: "/src/assets/logos/kuaishou.png",
    视频号: "/src/assets/logos/wechat_shipinghao.png",
    小红书: "/src/assets/logos/xiaohongshu.jpg",
  };
  return logoMap[platform] || "";
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
            fetchAccounts();
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
                ? 1
                : accountForm.platform === "抖音"
                ? 2
                : accountForm.platform === "视频号"
                ? 3
                : 4
            ),
            userName: accountForm.name,
          });
          if (res.code === 200) {
            accountStore.updateAccount(accountForm.id, accountForm);
            ElMessage.success("更新成功");
            dialogVisible.value = false;
            fetchAccounts();
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
// 新增：分组管理相关方法和数据
const groupDialogVisible = ref(false);
const groupDialogType = ref("add");
const groupFormRef = ref(null);
const draggedAccount = ref(null);

const groupForm = reactive({
  id: null,
  name: "",
  description: "",
  color: "#5B73DE",
  icon: "Users",
});

const groupRules = {
  name: [{ required: true, message: "请输入分组名称", trigger: "blur" }],
};

// 可选的图标列表
const groupIcons = [
  "Users",
  "User",
  "Briefcase",
  "Star",
  "Heart",
  "Flag",
  "Trophy",
  "Gift",
  "Crown",
  "Diamond",
  "Fire",
  "Lightning",
];

// 计算属性：未分组的账号
const ungroupedAccounts = computed(() => {
  return accountStore.accounts.filter((acc) => !acc.group_id);
});

// 根据分组ID获取账号
const getAccountsByGroup = (groupId) => {
  return accountStore.accounts.filter((acc) => acc.group_id === groupId);
};

// 获取分组图标组件
const getGroupIcon = (iconName) => {
  // Element Plus 图标映射
  const iconMap = {
    Users: "User",
    User: "User",
    Briefcase: "Briefcase",
    Star: "Star",
    Heart: "Heart",
    Flag: "Flag",
    Trophy: "Trophy",
    Gift: "Gift",
    Crown: "Crown",
    Diamond: "Diamond",
    Fire: "Fire",
    Lightning: "Lightning",
  };
  return iconMap[iconName] || "User";
};

// 拖拽开始
const handleDragStart = (account, event) => {
  draggedAccount.value = account;
  event.dataTransfer.effectAllowed = "move";

  // 添加拖拽样式
  event.target.style.opacity = "0.5";
};

const handleDragOver = (event) => {
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";

  // 添加悬停样式
  const groupCard = event.currentTarget;
  groupCard.classList.add("drag-over");
};

const handleDragLeave = (event) => {
  // 移除悬停样式
  const groupCard = event.currentTarget;
  groupCard.classList.remove("drag-over");
};

const handleDrop = async (groupId, event) => {
  event.preventDefault();

  // 移除悬停样式
  const groupCard = event.currentTarget;
  groupCard.classList.remove("drag-over");

  if (!draggedAccount.value) return;

  try {
    const res = await accountApi.updateAccountGroup({
      account_id: draggedAccount.value.id,
      group_id: groupId,
    });

    if (res.code === 200) {
      const group = accountStore.getGroupById(groupId);
      accountStore.updateAccountGroup(draggedAccount.value.id, groupId, group);
      ElMessage.success("账号分组更新成功");
    } else {
      ElMessage.error(res.msg || "分组更新失败");
    }
  } catch (error) {
    console.error("更新账号分组失败:", error);
    ElMessage.error("分组更新失败");
  } finally {
    draggedAccount.value = null;
  }
};

const handleDragEnd = (event) => {
  // 恢复透明度
  event.target.style.opacity = "1";
  draggedAccount.value = null;
};
// 移动账号到指定分组
const moveAccountToGroup = async (accountId, groupId) => {
  try {
    const res = await accountApi.updateAccountGroup({
      account_id: accountId,
      group_id: groupId,
    });

    if (res.code === 200) {
      const group = groupId ? accountStore.getGroupById(groupId) : null;
      accountStore.updateAccountGroup(accountId, groupId, group);
      ElMessage.success(groupId ? "账号已移入分组" : "账号已移出分组");
    } else {
      ElMessage.error(res.msg || "操作失败");
    }
  } catch (error) {
    console.error("移动账号失败:", error);
    ElMessage.error("操作失败");
  }
};

// 添加分组
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

// 编辑分组
const handleEditGroup = (group) => {
  groupDialogType.value = "edit";
  Object.assign(groupForm, { ...group });
  groupDialogVisible.value = true;
};

// 删除分组
const handleDeleteGroup = (group) => {
  ElMessageBox.confirm(
    `确定要删除分组 "${group.name}" 吗？分组内的账号将变为未分组状态。`,
    "删除确认",
    {
      confirmButtonText: "确定删除",
      cancelButtonText: "取消",
      type: "warning",
    }
  )
    .then(async () => {
      try {
        const res = await accountApi.deleteGroup(group.id);
        if (res.code === 200) {
          accountStore.deleteGroup(group.id);
          ElMessage.success("分组删除成功");
        } else {
          ElMessage.error(res.msg || "删除失败");
        }
      } catch (error) {
        console.error("删除分组失败:", error);
        ElMessage.error("删除失败");
      }
    })
    .catch(() => {});
};

// 提交分组表单
const submitGroupForm = () => {
  groupFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        let res;
        if (groupDialogType.value === "add") {
          res = await accountApi.createGroup(groupForm);
          if (res.code === 200) {
            ElMessage.success("分组创建成功");
            // 重新获取分组列表
            const groupsRes = await accountApi.getGroups();
            if (groupsRes.code === 200) {
              accountStore.setGroups(groupsRes.data);
            }
          }
        } else {
          res = await accountApi.updateGroup(groupForm);
          if (res.code === 200) {
            accountStore.updateGroup(groupForm.id, groupForm);
            ElMessage.success("分组更新成功");
          }
        }

        if (res.code === 200) {
          groupDialogVisible.value = false;
        } else {
          ElMessage.error(res.msg || "操作失败");
        }
      } catch (error) {
        console.error("分组操作失败:", error);
        ElMessage.error("操作失败");
      }
    }
  });
};
// 生命周期
onMounted(() => {
  if (appStore.isFirstTimeAccountManagement) {
    fetchAccounts(false); // 首次加载不强制验证
  }
});
const handleRefresh = () => {
  fetchAccounts(true); // 手动刷新时强制验证
};
onBeforeUnmount(() => {
  closeSSEConnection();
});
</script>

<style lang="scss" scoped>
// 变量定义
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
  max-width: 1200px;
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

// 统计卡片
.stats-section {
  margin-bottom: $space-lg;

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: $space-md;

    .stat-card {
      background: $bg-white;
      border-radius: $radius-lg;
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

        &.total {
          background: linear-gradient(135deg, $primary 0%, #8b9ee8 100%);
        }

        &.normal {
          background: linear-gradient(135deg, $success 0%, #34d399 100%);
        }

        &.abnormal {
          background: linear-gradient(135deg, $danger 0%, #f87171 100%);
        }

        &.platforms {
          background: linear-gradient(135deg, $info 0%, #9ca3af 100%);
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
    }
  }
}

// 账号列表
.accounts-section {
  .accounts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: $space-lg;
  }

  .account-card {
    background: $bg-white;
    border-radius: $radius-xl;
    padding: $space-lg;
    box-shadow: $shadow-sm;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;

    &:hover {
      transform: translateY(-2px);
      box-shadow: $shadow-lg;
    }

    .account-info {
      display: flex;
      align-items: center;
      gap: $space-md;
      margin-bottom: $space-lg;

      .avatar-container {
        position: relative;
        flex-shrink: 0;

        .account-avatar {
          position: relative;

          :deep(.el-avatar) {
            border: 3px solid #f1f5f9;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          }
        }

        .platform-logo {
          position: absolute;
          bottom: -4px;
          right: -4px;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: white;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
          border: 1px solid white;

          img {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            object-fit: cover;
          }
        }

        .status-dot {
          position: absolute;
          top: 2px;
          right: 8px;
          width: 12px;
          height: 12px;
          border-radius: 50%;
          border: 2px solid white;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);

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
        min-width: 0; // 防止文字溢出

        .account-name {
          font-size: 16px;
          font-weight: 600;
          color: $text-primary;
          margin: 0 0 $space-xs 0;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .account-meta {
          display: flex;
          align-items: center;
          gap: $space-sm;
          flex-wrap: wrap;

          .platform-text {
            font-size: 13px;
            color: $text-secondary;
            background: $bg-gray;
            padding: 2px 8px;
            border-radius: $radius-sm;
            font-weight: 500;
          }

          // 新增：分组标签样式
          .group-tag {
            font-size: 12px;
            border: none;

            :deep(.el-tag__content) {
              color: white;
              font-weight: 500;
            }
          }
        }
      }
    }

    .account-actions {
      position: absolute;
      top: $space-md;
      right: $space-md;
      display: flex;
      gap: $space-xs;
      opacity: 0;
      transform: translateY(-4px);
      transition: all 0.3s ease;

      .action-btn {
        width: 28px;
        height: 28px;
        min-height: 28px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        font-weight: 500;
        transition: all 0.3s ease;
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(4px);
        border: 1px solid rgba(0, 0, 0, 0.1);

        .el-icon {
          font-size: 14px;
        }

        &:hover {
          transform: scale(1.1);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }

        &.danger {
          &:hover {
            background-color: $danger;
            border-color: $danger;
            color: white;
          }
        }
      }
    }

    &:hover .account-actions {
      opacity: 1;
      transform: translateY(0);
    }
  }
}

// 空状态
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

// 对话框样式
.account-dialog {
  .dialog-content {
    padding: $space-md 0;

    .platform-select {
      .platform-option {
        display: flex;
        align-items: center;
        gap: $space-sm;

        .platform-icon {
          font-size: 16px;

          &.douyin {
            color: $platform-douyin;
          }
          &.kuaishou {
            color: $platform-kuaishou;
          }
          &.wechat {
            color: $platform-wechat;
          }
          &.xiaohongshu {
            color: $platform-xiaohongshu;
          }
        }
      }
    }

    .qrcode-container {
      margin-top: $space-lg;
      text-align: center;

      .qrcode-wrapper {
        .qrcode-header {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: $space-sm;
          margin-bottom: $space-md;
          font-weight: 600;
          color: $text-primary;
        }

        .qrcode-tip {
          color: $text-secondary;
          margin-bottom: $space-md;
        }

        .qrcode-frame {
          background: $bg-gray;
          border-radius: $radius-lg;
          padding: $space-lg;
          display: inline-block;

          .qrcode-image {
            width: 200px;
            height: 200px;
            border-radius: $radius-md;
          }
        }
      }

      .loading-wrapper,
      .success-wrapper,
      .error-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: $space-md;
        padding: $space-2xl;

        .loading-icon,
        .success-icon,
        .error-icon {
          font-size: 48px;
        }

        .loading-icon {
          color: $primary;
          animation: rotate 1s linear infinite;
        }

        .success-icon {
          color: $success;
        }

        .error-icon {
          color: $danger;
        }

        .loading-text,
        .success-text,
        .error-text {
          font-size: 16px;
          font-weight: 500;
        }
      }
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: $space-sm;
    padding-top: $space-md;
  }
}

// 动画
@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// 响应式
@media (max-width: 768px) {
  .page-header .header-content {
    flex-direction: column;
    align-items: stretch;
    gap: $space-md;
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

  .stats-grid {
    grid-template-columns: 1fr !important;
  }

  .accounts-grid {
    grid-template-columns: 1fr !important;
  }
}
// 分组管理专用样式
.groups-content {
  .groups-stats {
    margin-bottom: $space-lg;

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: $space-md;

      .stat-card {
        background: $bg-white;
        border-radius: $radius-lg;
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

          &.total {
            background: linear-gradient(135deg, $primary 0%, #8b9ee8 100%);
          }

          &.normal {
            background: linear-gradient(135deg, $success 0%, #34d399 100%);
          }

          &.abnormal {
            background: linear-gradient(135deg, $danger 0%, #f87171 100%);
          }

          &.platforms {
            background: linear-gradient(135deg, $info 0%, #9ca3af 100%);
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
      }
    }
  }

  .groups-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: $space-lg;

    .group-card {
      background: $bg-white;
      border-radius: $radius-xl;
      padding: $space-lg;
      box-shadow: $shadow-sm;
      transition: all 0.3s ease;
      border: 2px solid transparent;

      &:hover {
        transform: translateY(-2px);
        box-shadow: $shadow-md;
      }

      &.ungrouped {
        border: 2px dashed $border-light;
        background: $bg-gray;

        .group-icon {
          background: $text-muted !important;
        }
      }

      // 拖拽悬停效果
      &.drag-over {
        border-color: $primary;
        background-color: rgba(91, 115, 222, 0.05);
      }

      .group-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: $space-md;

        .group-info {
          display: flex;
          align-items: flex-start;
          gap: $space-md;
          flex: 1;

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

          .group-details {
            flex: 1;
            min-width: 0;

            .group-name {
              font-size: 18px;
              font-weight: 600;
              color: $text-primary;
              margin: 0 0 $space-xs 0;
              line-height: 1.2;
            }

            .group-description {
              font-size: 14px;
              color: $text-secondary;
              margin: 0;
              line-height: 1.4;
            }
          }
        }

        .group-actions {
          display: flex;
          gap: $space-xs;
          opacity: 0;
          transition: opacity 0.3s ease;

          .el-button {
            width: 32px;
            height: 32px;
            border-radius: 50%;
          }
        }
      }

      &:hover .group-actions {
        opacity: 1;
      }

      .group-accounts {
        .group-account-item {
          display: flex;
          align-items: center;
          gap: $space-sm;
          padding: $space-sm;
          border-radius: $radius-md;
          transition: all 0.3s ease;
          cursor: grab;
          margin-bottom: $space-xs;

          &:hover {
            background-color: $bg-light;
          }

          &:active {
            cursor: grabbing;
          }

          &:last-child {
            margin-bottom: 0;
          }

          .account-info {
            flex: 1;
            min-width: 0;

            .account-name {
              font-size: 14px;
              font-weight: 500;
              color: $text-primary;
              margin-bottom: 2px;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }

            .account-platform {
              font-size: 12px;
              color: $text-secondary;
            }
          }

          .remove-btn {
            opacity: 0;
            transition: opacity 0.3s ease;
            width: 24px;
            height: 24px;
            min-height: 24px;
            padding: 0;
            border-radius: 50%;

            .el-icon {
              font-size: 12px;
            }
          }

          &:hover .remove-btn {
            opacity: 1;
          }
        }
      }

      .group-empty {
        padding: $space-lg;
        text-align: center;
        color: $text-muted;
        font-size: 14px;
        border: 2px dashed $border-light;
        border-radius: $radius-md;
        background-color: $bg-light;
      }
    }
  }
}

// 标签页样式优化
// 更接近竞品的标签页样式
.tabs-container {
  .simple-tabs {
    margin-bottom: $space-lg;

    .tabs-header {
      display: flex;
      align-items: center;
      background: transparent;
      padding: 0;

      .tab-item {
        padding: 12px 20px;
        margin-right: 8px;
        font-size: 14px;
        font-weight: 500;
        color: #9ca3af;
        cursor: pointer;
        transition: all 0.3s ease;
        position: relative;
        background: transparent;
        border: none;
        border-radius: 6px 6px 0 0;

        &:hover {
          color: $text-primary;
          background-color: rgba(91, 115, 222, 0.05);
        }

        &.active {
          color: $primary;
          background-color: $bg-white;
          border-bottom: 2px solid $primary;
          box-shadow: 0 -1px 0 0 $border-light, 1px 0 0 0 $border-light,
            -1px 0 0 0 $border-light;
        }
      }
    }
  }

  .tab-content {
    background: $bg-white;
    border-radius: 0 8px 8px 8px;
    padding: $space-lg;
    box-shadow: $shadow-sm;
  }
}
</style>