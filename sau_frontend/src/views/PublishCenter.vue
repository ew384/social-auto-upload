<template>
  <div class="publish-center">
    <!-- 页面头部保持不变 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">发布中心</h1>
          <p class="page-subtitle">一键发布内容到多个平台，支持按分组选择账号</p>
        </div>
        <div class="header-actions">
          <el-button @click="addNewPublishTask" class="add-task-btn">
            <el-icon><Plus /></el-icon>
            新建发布任务
          </el-button>
        </div>
      </div>
    </div>

    <!-- 发布任务列表 -->
    <div class="publish-tasks">
      <div 
        v-for="task in publishTasks" 
        :key="task.id"
        class="publish-task-card"
      >
        <!-- 任务头部和进度步骤保持不变 -->
        <div class="task-header">
          <div class="task-info">
            <h3 class="task-title">{{ task.title || `发布任务 ${task.id}` }}</h3>
            <div class="task-status">
              <el-tag 
                :type="getTaskStatusType(task.status)" 
                size="small"
                effect="light"
              >
                {{ getTaskStatusText(task.status) }}
              </el-tag>
            </div>
          </div>
          <div class="task-actions">
            <el-button 
              v-if="task.status === 'draft'"
              type="primary" 
              size="small"
              @click="publishTask(task)"
              :loading="task.publishing"
            >
              <el-icon><Upload /></el-icon>
              {{ task.publishing ? '发布中' : '立即发布' }}
            </el-button>
            <el-button 
              size="small" 
              @click="duplicateTask(task)"
            >
              <el-icon><CopyDocument /></el-icon>
              复制
            </el-button>
            <el-button 
              size="small" 
              type="danger"
              @click="deleteTask(task)"
            >
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </div>
        </div>

        <!-- 进度指示器保持不变 -->
        <div class="progress-steps">
          <div 
            v-for="(step, index) in steps" 
            :key="step.key"
            :class="['step-item', {
              'active': task.currentStep === step.key,
              'completed': getStepIndex(task.currentStep) > index,
              'error': task.status === 'error' && task.currentStep === step.key
            }]"
            @click="setCurrentStep(task, step.key)"
          >
            <div class="step-circle">
              <el-icon v-if="getStepIndex(task.currentStep) > index"><Check /></el-icon>
              <el-icon v-else-if="task.status === 'error' && task.currentStep === step.key"><Close /></el-icon>
              <span v-else>{{ index + 1 }}</span>
            </div>
            <div class="step-label">{{ step.label }}</div>
          </div>
        </div>

        <!-- 步骤内容 -->
        <div class="step-content">
          <!-- 步骤1: 选择视频 - 保持不变 -->
          <div v-show="task.currentStep === 'video'" class="step-panel">
            <!-- 视频选择内容保持原有逻辑 -->
          </div>

          <!-- 步骤2: 选择账号 - 增强版本 -->
          <div v-show="task.currentStep === 'accounts'" class="step-panel">
            <div class="step-header">
              <h4>选择发布账号</h4>
              <p>选择要发布内容的账号，支持按分组快速选择</p>
            </div>

            <div class="accounts-section">
              <!-- 分组快速选择 -->
              <div class="group-selector">
                <h5 class="selector-title">
                  <el-icon><FolderOpened /></el-icon>
                  按分组选择
                </h5>
                <div class="group-buttons">
                  <el-button
                    v-for="group in groupStore.groups"
                    :key="group.id"
                    size="small"
                    :type="isGroupSelected(task, group.id) ? 'primary' : 'default'"
                    @click="toggleGroupSelection(task, group)"
                    class="group-btn"
                  >
                    <div class="group-indicator" :style="{ backgroundColor: group.color }"></div>
                    <span>{{ group.name }}</span>
                    <el-badge 
                      :value="getGroupAccountCount(group.id)" 
                      :hidden="getGroupAccountCount(group.id) === 0"
                    />
                  </el-button>
                  
                  <el-button 
                    size="small" 
                    @click="toggleAllAccounts(task)"
                    :type="task.selectedAccounts.length === availableAccounts.length ? 'success' : 'default'"
                  >
                    <el-icon><Grid /></el-icon>
                    全选/全不选 ({{ availableAccounts.length }})
                  </el-button>
                </div>
              </div>

              <!-- 分组展示区域 -->
              <div class="grouped-accounts">
                <div 
                  v-for="group in groupsWithAccounts" 
                  :key="group.id"
                  class="group-section"
                  v-show="group.accounts.length > 0"
                >
                  <!-- 分组头部 -->
                  <div class="group-header">
                    <div class="group-info">
                      <div class="group-icon" :style="{ backgroundColor: group.color }">
                        <el-icon><component :is="group.icon" /></el-icon>
                      </div>
                      <div class="group-details">
                        <h6 class="group-name">{{ group.name }}</h6>
                        <span class="group-count">{{ group.accounts.length }} 个账号</span>
                      </div>
                    </div>
                    
                    <div class="group-actions">
                      <el-button 
                        size="small" 
                        @click="toggleGroupSelection(task, group)"
                        :type="isGroupSelected(task, group.id) ? 'primary' : 'default'"
                      >
                        {{ isGroupSelected(task, group.id) ? '取消选择' : '选择全部' }}
                      </el-button>
                    </div>
                  </div>

                  <!-- 分组内账号 -->
                  <div class="group-accounts">
                    <div 
                      v-for="account in group.accounts" 
                      :key="account.id"
                      :class="['account-item', { 
                        'selected': task.selectedAccounts.includes(account.id),
                        'disabled': account.status !== '正常'
                      }]"
                      @click="toggleAccountSelection(task, account)"
                    >
                      <div class="account-avatar">
                        <el-avatar :size="36" :src="account.avatar" />
                        <div :class="['status-dot', account.status === '正常' ? 'online' : 'offline']"></div>
                        <div v-if="task.selectedAccounts.includes(account.id)" class="selected-mark">
                          <el-icon><Check /></el-icon>
                        </div>
                      </div>
                      
                      <div class="account-info">
                        <div class="account-name">{{ account.name }}</div>
                        <div class="account-platform">
                          <component :is="getPlatformIcon(account.platform)" class="platform-icon" />
                          <span>{{ account.platform }}</span>
                        </div>
                      </div>

                      <div class="account-status">
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
                </div>
              </div>

              <!-- 选中账号统计 -->
              <div v-if="task.selectedAccounts.length > 0" class="selected-summary">
                <div class="summary-content">
                  <div class="summary-info">
                    <el-icon><User /></el-icon>
                    <span>已选择 {{ task.selectedAccounts.length }} 个账号</span>
                  </div>
                  
                  <div class="selected-platforms">
                    <el-tag
                      v-for="platform in getSelectedPlatforms(task)"
                      :key="platform"
                      size="small"
                      :type="getPlatformTagType(platform)"
                      effect="light"
                    >
                      {{ platform }}
                    </el-tag>
                  </div>
                </div>
                
                <el-button size="small" @click="clearAccountSelection(task)">
                  清空选择
                </el-button>
              </div>
            </div>
          </div>

          <!-- 步骤3和步骤4保持不变 -->
          <!-- ... 其他步骤内容 ... -->
        </div>

        <!-- 步骤导航保持不变 -->
        <div class="step-navigation">
          <div class="nav-left">
            <el-button 
              v-if="task.currentStep !== 'video'"
              @click="previousStep(task)"
              :disabled="task.publishing"
            >
              <el-icon><ArrowLeft /></el-icon>
              上一步
            </el-button>
          </div>
          <div class="nav-right">
            <el-button 
              v-if="task.currentStep !== 'confirm'"
              type="primary"
              @click="nextStep(task)"
              :disabled="!canProceedToNextStep(task)"
            >
              下一步
              <el-icon><ArrowRight /></el-icon>
            </el-button>
            <el-button 
              v-else
              type="primary"
              @click="publishTask(task)"
              :loading="task.publishing"
              :disabled="!canPublish(task)"
            >
              <el-icon><Upload /></el-icon>
              {{ task.publishing ? '发布中' : '确认发布' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import {
  Plus,
  Upload,
  CopyDocument,
  Delete,
  VideoCamera,
  Folder,
  VideoPlay,
  View,
  Check,
  Close,
  User,
  ArrowLeft,
  ArrowRight,
  FolderOpened,
  Grid,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useAccountStore } from "@/stores/account";
import { useGroupStore } from "@/stores/group";
import { useAppStore } from "@/stores/app";
import { accountApi } from "@/api/account";
import { groupApi } from "@/api/group";

// 状态管理
const accountStore = useAccountStore();
const groupStore = useGroupStore();
const appStore = useAppStore();

// 步骤配置
const steps = [
  { key: "video", label: "选择视频" },
  { key: "accounts", label: "选择账号" },
  { key: "content", label: "编辑内容" },
  { key: "confirm", label: "确认发布" },
];

// 发布任务列表
const publishTasks = ref([]);
let taskIdCounter = 1;

// 计算属性
const availableAccounts = computed(() => accountStore.accounts);

// 按分组组织的账号
const groupsWithAccounts = computed(() => {
  return groupStore.groups.map((group) => ({
    ...group,
    accounts: accountStore
      .getAccountsByGroup(group.id)
      .filter((acc) => acc.status === "正常"),
  }));
});

// 方法定义
const addNewPublishTask = () => {
  const newTask = {
    id: taskIdCounter++,
    title: "",
    currentStep: "video",
    status: "draft",
    videos: [],
    selectedAccounts: [],
    topics: [],
    scheduleEnabled: false,
    scheduleTime: "",
    publishing: false,
    publishProgress: 0,
    publishProgressText: "",
  };

  publishTasks.value.push(newTask);
};

const getStepIndex = (stepKey) => {
  return steps.findIndex((step) => step.key === stepKey);
};

const getTaskStatusType = (status) => {
  const typeMap = {
    draft: "info",
    publishing: "warning",
    published: "success",
    error: "danger",
  };
  return typeMap[status] || "info";
};

const getTaskStatusText = (status) => {
  const textMap = {
    draft: "草稿",
    publishing: "发布中",
    published: "已发布",
    error: "发布失败",
  };
  return textMap[status] || "未知";
};

const setCurrentStep = (task, stepKey) => {
  if (task.publishing) return;
  task.currentStep = stepKey;
};

// 分组相关方法
const getGroupAccountCount = (groupId) => {
  return accountStore
    .getAccountsByGroup(groupId)
    .filter((acc) => acc.status === "正常").length;
};

const isGroupSelected = (task, groupId) => {
  const groupAccounts = accountStore
    .getAccountsByGroup(groupId)
    .filter((acc) => acc.status === "正常");
  if (groupAccounts.length === 0) return false;

  return groupAccounts.every((account) =>
    task.selectedAccounts.includes(account.id)
  );
};

const toggleGroupSelection = (task, group) => {
  const groupAccounts = accountStore
    .getAccountsByGroup(group.id)
    .filter((acc) => acc.status === "正常");
  const isSelected = isGroupSelected(task, group.id);

  if (isSelected) {
    // 取消选择这个分组的所有账号
    groupAccounts.forEach((account) => {
      const index = task.selectedAccounts.indexOf(account.id);
      if (index > -1) {
        task.selectedAccounts.splice(index, 1);
      }
    });
  } else {
    // 选择这个分组的所有账号
    groupAccounts.forEach((account) => {
      if (!task.selectedAccounts.includes(account.id)) {
        task.selectedAccounts.push(account.id);
      }
    });
  }
};

const toggleAllAccounts = (task) => {
  const allAccountIds = availableAccounts.value
    .filter((acc) => acc.status === "正常")
    .map((acc) => acc.id);

  if (task.selectedAccounts.length === allAccountIds.length) {
    // 全部取消选择
    task.selectedAccounts = [];
  } else {
    // 全部选择
    task.selectedAccounts = [...allAccountIds];
  }
};

const toggleAccountSelection = (task, account) => {
  if (account.status !== "正常") return;

  const index = task.selectedAccounts.indexOf(account.id);
  if (index > -1) {
    task.selectedAccounts.splice(index, 1);
  } else {
    task.selectedAccounts.push(account.id);
  }
};

const clearAccountSelection = (task) => {
  task.selectedAccounts = [];
};

const getSelectedPlatforms = (task) => {
  const platforms = new Set();
  task.selectedAccounts.forEach((accountId) => {
    const account = accountStore.accounts.find((acc) => acc.id === accountId);
    if (account) {
      platforms.add(account.platform);
    }
  });
  return Array.from(platforms);
};

const getPlatformTagType = (platform) => {
  const typeMap = {
    抖音: "danger",
    快手: "warning",
    视频号: "success",
    小红书: "primary",
  };
  return typeMap[platform] || "info";
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

const canProceedToNextStep = (task) => {
  switch (task.currentStep) {
    case "video":
      return task.videos.length > 0;
    case "accounts":
      return task.selectedAccounts.length > 0;
    case "content":
      return task.title.trim().length > 0;
    default:
      return true;
  }
};

const canPublish = (task) => {
  return (
    task.videos.length > 0 &&
    task.selectedAccounts.length > 0 &&
    task.title.trim().length > 0
  );
};

const nextStep = (task) => {
  const currentIndex = getStepIndex(task.currentStep);
  if (currentIndex < steps.length - 1) {
    task.currentStep = steps[currentIndex + 1].key;
  }
};

const previousStep = (task) => {
  const currentIndex = getStepIndex(task.currentStep);
  if (currentIndex > 0) {
    task.currentStep = steps[currentIndex - 1].key;
  }
};

const publishTask = async (task) => {
  if (task.publishing) return;

  task.publishing = true;
  task.publishProgress = 0;
  task.publishProgressText = "准备发布...";
  task.status = "publishing";

  try {
    // 构建发布数据
    const publishData = {
      fileList: task.videos.map((video) => video.path),
      accountList: task.selectedAccounts,
      type: 1, // 这里需要根据实际平台类型确定
      title: task.title,
      tags: task.topics.join(" "),
      category: 0,
      enableTimer: task.scheduleEnabled,
      videosPerDay: 1,
      dailyTimes: task.scheduleEnabled ? [task.scheduleTime] : [],
      startDays: 0,
    };

    // 调用发布API
    const response = await fetch("/postVideo", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(publishData),
    });

    task.publishProgressText = "正在发布...";
    task.publishProgress = 50;

    if (response.ok) {
      task.publishProgress = 100;
      task.publishProgressText = "发布成功";
      task.status = "published";
      task.publishing = false;
      ElMessage.success("发布成功");
    } else {
      throw new Error("发布失败");
    }
  } catch (error) {
    console.error("发布错误:", error);
    task.status = "error";
    task.publishProgressText = "发布失败";
    task.publishing = false;
    ElMessage.error("发布失败");
  }
};

const duplicateTask = (task) => {
  const duplicatedTask = {
    ...JSON.parse(JSON.stringify(task)),
    id: taskIdCounter++,
    status: "draft",
    publishing: false,
    publishProgress: 0,
    publishProgressText: "",
  };

  publishTasks.value.push(duplicatedTask);
  ElMessage.success("任务复制成功");
};

const deleteTask = (task) => {
  ElMessageBox.confirm("确定要删除这个发布任务吗？", "删除确认", {
    confirmButtonText: "确定删除",
    cancelButtonText: "取消",
    type: "warning",
  })
    .then(() => {
      const index = publishTasks.value.indexOf(task);
      if (index > -1) {
        publishTasks.value.splice(index, 1);
        ElMessage.success("任务删除成功");
      }
    })
    .catch(() => {});
};

// 获取数据
const fetchData = async () => {
  try {
    // 获取分组数据
    const groupRes = await groupApi.getAllGroups();
    if (groupRes.code === 200) {
      groupStore.setGroups(groupRes.data);
    }

    // 获取账号数据 - 使用现有接口作为fallback
    try {
      const accountRes = await accountApi.getAccountsWithGroups();
      if (accountRes.code === 200) {
        accountStore.setAccounts(accountRes.data);
      }
    } catch (error) {
      console.warn("新接口调用失败，使用原有接口:", error);
      // 如果新接口失败，使用原有接口
      const accountRes = await accountApi.getValidAccounts();
      if (accountRes.code === 200) {
        accountStore.setAccounts(accountRes.data);
      }
    }
  } catch (error) {
    console.error("获取数据失败:", error);
    ElMessage.error("获取数据失败");
  }
};

// 初始化
onMounted(() => {
  fetchData();
  // 创建一个默认任务
  addNewPublishTask();
});
</script>

<style lang="scss" scoped>
// 变量定义保持原有样式
$primary: #5b73de;
$success: #10b981;
$warning: #f59e0b;
$danger: #ef4444;
$info: #6b7280;

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
$radius-2xl: 24px;

$space-xs: 4px;
$space-sm: 8px;
$space-md: 16px;
$space-lg: 24px;
$space-xl: 32px;
$space-2xl: 48px;

.publish-center {
  max-width: 1200px;
  margin: 0 auto;
}

// 分组选择器
.group-selector {
  background: $bg-gray;
  border-radius: $radius-lg;
  padding: $space-lg;
  margin-bottom: $space-lg;

  .selector-title {
    display: flex;
    align-items: center;
    gap: $space-sm;
    font-size: 16px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 $space-md 0;
  }

  .group-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: $space-sm;

    .group-btn {
      display: flex;
      align-items: center;
      gap: $space-sm;
      border-radius: $radius-md;
      transition: all 0.3s ease;

      .group-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
      }

      &:hover {
        transform: translateY(-1px);
      }
    }
  }
}

// 分组账号展示
.grouped-accounts {
  .group-section {
    background: $bg-white;
    border-radius: $radius-lg;
    margin-bottom: $space-lg;
    overflow: hidden;
    box-shadow: $shadow-sm;

    .group-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: $space-lg;
      background: linear-gradient(
        135deg,
        rgba(91, 115, 222, 0.05) 0%,
        rgba(139, 158, 232, 0.05) 100%
      );
      border-bottom: 1px solid $border-light;

      .group-info {
        display: flex;
        align-items: center;
        gap: $space-md;

        .group-icon {
          width: 40px;
          height: 40px;
          border-radius: $radius-lg;
          display: flex;
          align-items: center;
          justify-content: center;

          .el-icon {
            font-size: 20px;
            color: white;
          }
        }

        .group-details {
          .group-name {
            font-size: 16px;
            font-weight: 600;
            color: $text-primary;
            margin: 0 0 $space-xs 0;
          }

          .group-count {
            font-size: 12px;
            color: $text-secondary;
          }
        }
      }
    }

    .group-accounts {
      padding: $space-md;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: $space-md;

      .account-item {
        display: flex;
        align-items: center;
        gap: $space-md;
        padding: $space-md;
        border: 2px solid transparent;
        border-radius: $radius-lg;
        cursor: pointer;
        transition: all 0.3s ease;
        background: $bg-gray;

        &:hover {
          transform: translateY(-2px);
          box-shadow: $shadow-md;
        }

        &.selected {
          border-color: $primary;
          background-color: rgba(91, 115, 222, 0.05);
        }

        &.disabled {
          opacity: 0.5;
          cursor: not-allowed;

          &:hover {
            transform: none;
            box-shadow: none;
          }
        }

        .account-avatar {
          position: relative;
          flex-shrink: 0;

          .status-dot {
            position: absolute;
            bottom: 0;
            right: 0;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            border: 2px solid white;

            &.online {
              background-color: $success;
            }

            &.offline {
              background-color: $danger;
            }
          }

          .selected-mark {
            position: absolute;
            top: -4px;
            right: -4px;
            width: 18px;
            height: 18px;
            background-color: $primary;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 10px;
          }
        }

        .account-info {
          flex: 1;
          min-width: 0;

          .account-name {
            font-weight: 500;
            color: $text-primary;
            margin-bottom: $space-xs;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .account-platform {
            display: flex;
            align-items: center;
            gap: $space-xs;
            font-size: 12px;
            color: $text-secondary;

            .platform-icon {
              font-size: 14px;
            }
          }
        }

        .account-status {
          flex-shrink: 0;
        }
      }
    }
  }
}

// 选中账号统计
.selected-summary {
  background: rgba(91, 115, 222, 0.1);
  border-radius: $radius-lg;
  padding: $space-lg;
  display: flex;
  justify-content: space-between;
  align-items: center;

  .summary-content {
    display: flex;
    align-items: center;
    gap: $space-lg;

    .summary-info {
      display: flex;
      align-items: center;
      gap: $space-sm;
      color: $primary;
      font-weight: 500;
    }

    .selected-platforms {
      display: flex;
      gap: $space-xs;
      flex-wrap: wrap;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .group-buttons {
    flex-direction: column;

    .group-btn {
      width: 100%;
      justify-content: flex-start;
    }
  }

  .group-accounts {
    grid-template-columns: 1fr !important;
  }

  .selected-summary {
    flex-direction: column;
    align-items: stretch;
    gap: $space-md;

    .summary-content {
      flex-direction: column;
      align-items: stretch;
      gap: $space-md;
    }
  }
}

// 其他原有样式保持不变
.publish-task-card {
  background: $bg-white;
  border-radius: $radius-xl;
  padding: $space-xl;
  box-shadow: $shadow-md;
  transition: all 0.3s ease;
  margin-bottom: $space-lg;

  &:hover {
    box-shadow: $shadow-lg;
  }
}

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
      .add-task-btn {
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
</style>