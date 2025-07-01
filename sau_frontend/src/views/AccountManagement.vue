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
          <el-button type="primary" @click="handleAddAccount" class="add-btn">
            <el-icon><Plus /></el-icon>
            添加账号
          </el-button>
        </div>
      </div>
    </div>

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
          <div class="account-actions">
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
const filteredAccounts = computed(() => {
  let accounts = accountStore.accounts;

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
const platformCount = computed(() => {
  const platforms = new Set(accountStore.accounts.map((acc) => acc.platform));
  return platforms.size;
});

// 方法
const fetchAccounts = async () => {
  if (appStore.isAccountRefreshing) return;

  appStore.setAccountRefreshing(true);

  try {
    const res = await accountApi.getValidAccounts();
    if (res.code === 200 && res.data) {
      accountStore.setAccounts(res.data);
      ElMessage.success("账号数据刷新成功");
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

// 生命周期
onMounted(() => {
  if (appStore.isFirstTimeAccountManagement) {
    fetchAccounts();
  }
});

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
      transform: translateY(-4px);
      box-shadow: $shadow-lg;
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
        background: linear-gradient(135deg, $platform-douyin 0%, #ff6b8a 100%);
      }

      &.kuaishou {
        background: linear-gradient(
          135deg,
          $platform-kuaishou 0%,
          #ff8533 100%
        );
      }

      &.wechat {
        background: linear-gradient(135deg, $platform-wechat 0%, #3dd68c 100%);
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
      margin-bottom: $space-lg;

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

      .action-btn {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: $space-xs;
        border-radius: $radius-md;
        font-weight: 500;

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
</style>