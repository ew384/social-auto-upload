<template>
  <div class="publish-center">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">发布中心</h1>
          <p class="page-subtitle">一键发布内容到多个平台</p>
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
        <!-- 任务头部 -->
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

        <!-- 进度指示器 -->
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
          <!-- 步骤1: 选择视频 -->
          <div v-show="task.currentStep === 'video'" class="step-panel">
            <div class="step-header">
              <h4>选择视频文件</h4>
              <p>支持上传本地视频或从素材库选择</p>
            </div>
            
            <div class="upload-section">
              <div v-if="task.videos.length === 0" class="upload-area">
                <el-upload
                  class="video-uploader"
                  drag
                  multiple
                  :auto-upload="true"
                  :action="`${apiBaseUrl}/upload`"
                  :on-success="(response, file) => handleVideoUploadSuccess(response, file, task)"
                  :on-error="handleVideoUploadError"
                  accept="video/*"
                  :headers="authHeaders"
                >
                  <div class="upload-content">
                    <el-icon class="upload-icon"><VideoCamera /></el-icon>
                    <div class="upload-text">
                      <div>将视频文件拖拽到此处</div>
                      <div class="upload-hint">或 <em>点击上传</em></div>
                    </div>
                  </div>
                </el-upload>
                
                <div class="upload-options">
                  <el-button @click="selectFromLibrary(task)" class="library-btn">
                    <el-icon><Folder /></el-icon>
                    从素材库选择
                  </el-button>
                </div>
              </div>

              <!-- 已选择的视频列表 -->
              <div v-else class="selected-videos">
                <div class="videos-header">
                  <h5>已选择视频 ({{ task.videos.length }})</h5>
                  <el-button size="small" @click="addMoreVideos(task)">
                    <el-icon><Plus /></el-icon>
                    添加更多
                  </el-button>
                </div>
                <div class="videos-grid">
                  <div 
                    v-for="(video, index) in task.videos" 
                    :key="index"
                    class="video-item"
                  >
                    <div class="video-preview">
                      <el-icon class="video-icon"><VideoPlay /></el-icon>
                      <div class="video-overlay">
                        <el-button size="small" @click="previewVideo(video)">
                          <el-icon><View /></el-icon>
                        </el-button>
                        <el-button size="small" type="danger" @click="removeVideo(task, index)">
                          <el-icon><Delete /></el-icon>
                        </el-button>
                      </div>
                    </div>
                    <div class="video-info">
                      <div class="video-name">{{ video.name }}</div>
                      <div class="video-size">{{ formatFileSize(video.size) }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 步骤2: 选择账号 -->
          <div v-show="task.currentStep === 'accounts'" class="step-panel">
            <div class="step-header">
              <h4>选择发布账号</h4>
              <p>选择要发布内容的账号</p>
            </div>

            <div class="accounts-section">
              <!-- 新增：分组选择器 -->
              <div class="group-selector" v-if="accountStore.groups.length > 0">
                <h5>按分组选择</h5>
                <div class="groups-grid">
                  <div 
                    v-for="group in accountStore.groups"
                    :key="group.id"
                    :class="['group-selector-item', { 
                      'selected': isGroupSelected(task, group.id),
                      'partial': isGroupPartialSelected(task, group.id)
                    }]"
                    @click="toggleGroupSelection(task, group.id)"
                  >
                    <div class="group-info">
                      <div class="group-icon" :style="{ backgroundColor: group.color }">
                        <el-icon><component :is="getGroupIcon(group.icon)" /></el-icon>
                      </div>
                      <div class="group-details">
                        <span class="group-name">{{ group.name }}</span>
                        <span class="group-count">{{ getValidAccountsInGroup(group.id).length }} 个账号</span>
                      </div>
                    </div>
                    <div class="group-selection-status">
                      <el-icon v-if="isGroupSelected(task, group.id)"><Check /></el-icon>
                      <el-icon v-else-if="isGroupPartialSelected(task, group.id)" class="partial-icon"><Minus /></el-icon>
                    </div>
                  </div>

                  <!-- 未分组账号 -->
                  <div 
                    :class="['group-selector-item', { 
                      'selected': isUngroupedSelected(task),
                      'partial': isUngroupedPartialSelected(task)
                    }]"
                    @click="toggleUngroupedSelection(task)"
                  >
                    <div class="group-info">
                      <div class="group-icon ungrouped">
                        <el-icon><User /></el-icon>
                      </div>
                      <div class="group-details">
                        <span class="group-name">未分组账号</span>
                        <span class="group-count">{{ getUngroupedValidAccounts().length }} 个账号</span>
                      </div>
                    </div>
                    <div class="group-selection-status">
                      <el-icon v-if="isUngroupedSelected(task)"><Check /></el-icon>
                      <el-icon v-else-if="isUngroupedPartialSelected(task)" class="partial-icon"><Minus /></el-icon>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 分隔线 -->
              <div class="divider" v-if="accountStore.groups.length > 0">
                <span>或单独选择账号</span>
              </div>

              <!-- 原有的账号选择网格 -->
              <div class="accounts-grid">
                <div 
                  v-for="account in availableAccounts" 
                  :key="account.id"
                  :class="['account-card', { 
                    'selected': task.selectedAccounts.includes(account.id),
                    'disabled': account.status !== '正常'
                  }]"
                  @click="toggleAccountSelection(task, account)"
                >
                  <div class="account-avatar">
                    <el-avatar :size="40" :src="account.avatar" />
                    <div :class="['status-dot', account.status === '正常' ? 'online' : 'offline']"></div>
                    <div v-if="task.selectedAccounts.includes(account.id)" class="selected-mark">
                      <el-icon><Check /></el-icon>
                    </div>
                  </div>
                  <div class="account-info">
                    <div class="account-name">{{ account.name }}</div>
                    <div class="account-platform">{{ account.platform }}</div>
                    <!-- 显示分组信息 -->
                    <div v-if="account.group_name" class="account-group">
                      <el-tag :color="account.group_color" size="small" effect="light">
                        {{ account.group_name }}
                      </el-tag>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 选中账号统计 -->
              <div v-if="task.selectedAccounts.length > 0" class="selected-summary">
                <div class="summary-info">
                  <el-icon><User /></el-icon>
                  <span>已选择 {{ task.selectedAccounts.length }} 个账号</span>
                </div>
                <el-button size="small" @click="clearAccountSelection(task)">
                  清空选择
                </el-button>
              </div>
            </div>
          </div>

          <!-- 步骤3: 表单编辑 -->
          <div v-show="task.currentStep === 'content'" class="step-panel">
            <div class="step-header">
              <h4>内容编辑</h4>
              <p>编辑发布内容的标题、描述等信息</p>
            </div>

            <div class="content-form">
              <el-form :model="task" label-width="80px" class="publish-form">
                <!-- 标题 -->
                <el-form-item label="标题" required>
                  <el-input
                    v-model="task.title"
                    type="textarea"
                    :rows="3"
                    placeholder="请输入内容标题"
                    maxlength="100"
                    show-word-limit
                    class="title-input"
                  />
                </el-form-item>

                <!-- 话题标签 -->
                <el-form-item label="话题">
                  <div class="topics-section">
                    <div class="selected-topics">
                      <el-tag
                        v-for="(topic, index) in task.topics"
                        :key="index"
                        closable
                        @close="removeTopic(task, index)"
                        class="topic-tag"
                      >
                        #{{ topic }}
                      </el-tag>
                    </div>
                    <el-button size="small" @click="openTopicSelector(task)">
                      <el-icon><Plus /></el-icon>
                      添加话题
                    </el-button>
                  </div>
                </el-form-item>

                <!-- 发布设置 -->
                <el-form-item label="发布设置">
                  <div class="publish-settings">
                    <el-switch
                      v-model="task.scheduleEnabled"
                      active-text="定时发布"
                      inactive-text="立即发布"
                    />
                    
                    <div v-if="task.scheduleEnabled" class="schedule-options">
                      <div class="schedule-row">
                        <span class="label">发布时间:</span>
                        <el-date-picker
                          v-model="task.scheduleTime"
                          type="datetime"
                          placeholder="选择发布时间"
                          format="YYYY-MM-DD HH:mm"
                          value-format="YYYY-MM-DD HH:mm:ss"
                        />
                      </div>
                    </div>
                  </div>
                </el-form-item>
              </el-form>
            </div>
          </div>

          <!-- 步骤4: 确认发布 -->
          <div v-show="task.currentStep === 'confirm'" class="step-panel">
            <div class="step-header">
              <h4>确认发布</h4>
              <p>请确认发布信息无误后提交</p>
            </div>

            <div class="confirm-content">
              <!-- 发布预览 -->
              <div class="publish-preview">
                <div class="preview-section">
                  <h5>视频内容</h5>
                  <div class="videos-preview">
                    <div 
                      v-for="(video, index) in task.videos" 
                      :key="index"
                      class="video-preview-item"
                    >
                      <el-icon class="video-icon"><VideoPlay /></el-icon>
                      <span>{{ video.name }}</span>
                    </div>
                  </div>
                </div>

                <div class="preview-section">
                  <h5>发布账号</h5>
                  <div class="accounts-preview">
                    <el-tag
                      v-for="accountId in task.selectedAccounts"
                      :key="accountId"
                      class="account-tag"
                    >
                      {{ getAccountName(accountId) }}
                    </el-tag>
                  </div>
                </div>

                <div class="preview-section">
                  <h5>内容信息</h5>
                  <div class="content-preview">
                    <div class="preview-item">
                      <span class="label">标题:</span>
                      <span class="value">{{ task.title || '未设置' }}</span>
                    </div>
                    <div class="preview-item" v-if="task.topics.length > 0">
                      <span class="label">话题:</span>
                      <span class="value">{{ task.topics.map(t => '#' + t).join(' ') }}</span>
                    </div>
                    <div class="preview-item">
                      <span class="label">发布方式:</span>
                      <span class="value">{{ task.scheduleEnabled ? '定时发布' : '立即发布' }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 发布进度 -->
              <div v-if="task.publishing" class="publish-progress">
                <el-progress 
                  :percentage="task.publishProgress"
                  :status="task.publishProgress === 100 ? 'success' : ''"
                />
                <div class="progress-text">
                  {{ task.publishProgressText || '准备发布...' }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤导航 -->
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

    <!-- 话题选择对话框 -->
    <el-dialog
      v-model="topicDialogVisible"
      title="添加话题"
      width="600px"
      class="topic-dialog"
    >
      <div class="topic-selector">
        <div class="custom-topic">
          <el-input
            v-model="customTopic"
            placeholder="输入自定义话题"
            @keyup.enter="addCustomTopic"
          >
            <template #prepend>#</template>
            <template #append>
              <el-button @click="addCustomTopic">添加</el-button>
            </template>
          </el-input>
        </div>

        <div class="recommended-topics">
          <h5>推荐话题</h5>
          <div class="topics-grid">
            <el-button
              v-for="topic in recommendedTopics"
              :key="topic"
              size="small"
              @click="toggleRecommendedTopic(topic)"
              :type="currentTask?.topics?.includes(topic) ? 'primary' : 'default'"
            >
              #{{ topic }}
            </el-button>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="topicDialogVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
    <!-- 素材选择对话框 -->
    <el-dialog
      v-model="materialDialogVisible"
      title="选择视频"
      width="80%"
      class="material-dialog"
      :close-on-click-modal="false"
    >
      <div class="material-selector">
        <!-- 加载状态 -->
        <div v-if="loadingMaterials" class="loading-container">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载视频中...</span>
        </div>

        <!-- 视频内容 -->
        <div v-else class="videos-content">
          <!-- 标签页切换 -->
          <el-tabs v-model="activeTab" class="video-tabs">
            <!-- 最近上传 -->
            <el-tab-pane label="最近上传" name="recent">
              <div class="tab-content">
                <div v-if="recentVideos.length > 0">
                  <div class="videos-header">
                    <h5>最近上传的视频 ({{ recentVideos.length }} 个)</h5>
                    <div class="selection-info">
                      <span v-if="selectedVideoIds.length > 0">
                        已选择 {{ selectedVideoIds.length }} 个视频
                      </span>
                      <el-button 
                        v-if="selectedVideoIds.length > 0"
                        size="small" 
                        @click="selectedVideoIds = []"
                      >
                        清空选择
                      </el-button>
                    </div>
                  </div>

                  <div class="videos-grid">
                    <div 
                      v-for="video in recentVideos" 
                      :key="video.id"
                      :class="['video-item', { 
                        'selected': selectedVideoIds.includes(video.id) 
                      }]"
                      @click="toggleRecentVideoSelection(video.id)"
                    >
                      <!-- 视频预览 -->
                      <div class="video-preview">
                        <el-icon class="video-icon"><VideoPlay /></el-icon>
                        <div class="video-overlay">
                          <div class="overlay-content">
                            <el-button size="small" @click.stop="previewRecentVideo(video)">
                              <el-icon><View /></el-icon>
                              预览
                            </el-button>
                          </div>
                        </div>
                        <!-- 选中标记 -->
                        <div v-if="selectedVideoIds.includes(video.id)" class="selected-mark">
                          <el-icon><Check /></el-icon>
                        </div>
                        <!-- 来源标记 -->
                        <div class="source-badge recent">最近</div>
                      </div>

                      <!-- 视频信息 -->
                      <div class="video-info">
                        <div class="video-name" :title="video.filename">
                          {{ video.filename }}
                        </div>
                        <div class="video-meta">
                          <span class="video-size">{{ video.filesize }} MB</span>
                          <span class="video-date">{{ formatDate(video.upload_time) }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-videos">
                  <el-empty description="暂无最近上传的视频" />
                </div>
              </div>
            </el-tab-pane>

            <!-- 素材库 -->
            <el-tab-pane label="素材库" name="library">
              <div class="tab-content">
                <div v-if="libraryMaterials.length > 0">
                  <div class="videos-header">
                    <h5>素材库视频 ({{ libraryMaterials.length }} 个)</h5>
                    <div class="selection-info">
                      <span v-if="selectedMaterialIds.length > 0">
                        已选择 {{ selectedMaterialIds.length }} 个素材
                      </span>
                      <el-button 
                        v-if="selectedMaterialIds.length > 0"
                        size="small" 
                        @click="selectedMaterialIds = []"
                      >
                        清空选择
                      </el-button>
                    </div>
                  </div>

                  <div class="videos-grid">
                    <div 
                      v-for="material in libraryMaterials" 
                      :key="material.id"
                      :class="['video-item', { 
                        'selected': selectedMaterialIds.includes(material.id) 
                      }]"
                      @click="toggleMaterialSelection(material.id)"
                    >
                      <!-- 视频预览 -->
                      <div class="video-preview">
                        <el-icon class="video-icon"><VideoPlay /></el-icon>
                        <div class="video-overlay">
                          <div class="overlay-content">
                            <el-button size="small" @click.stop="previewMaterial(material)">
                              <el-icon><View /></el-icon>
                              预览
                            </el-button>
                          </div>
                        </div>
                        <!-- 选中标记 -->
                        <div v-if="selectedMaterialIds.includes(material.id)" class="selected-mark">
                          <el-icon><Check /></el-icon>
                        </div>
                        <!-- 来源标记 -->
                        <div class="source-badge library">素材库</div>
                      </div>

                      <!-- 视频信息 -->
                      <div class="video-info">
                        <div class="video-name" :title="material.filename">
                          {{ material.filename }}
                        </div>
                        <div class="video-meta">
                          <span class="video-size">{{ material.filesize }} MB</span>
                          <span class="video-date">{{ formatDate(material.upload_time) }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-videos">
                  <el-empty description="暂无素材库视频">
                    <el-button type="primary" @click="navigateToMaterialManagement">
                      <el-icon><Upload /></el-icon>
                      去添加素材
                    </el-button>
                  </el-empty>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="cancelSelection">取消</el-button>
          <el-button 
            type="primary" 
            @click="confirmSelection"
            :disabled="selectedVideoIds.length === 0 && selectedMaterialIds.length === 0"
          >
            确认选择 ({{ selectedVideoIds.length + selectedMaterialIds.length }})
          </el-button>
        </div>
      </template>
    </el-dialog>
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
  Minus,
  Star,
  Flag,
  Loading,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useAccountStore } from "@/stores/account";
import { useAppStore } from "@/stores/app";
import { materialApi } from "@/api/material";

// 状态管理
const accountStore = useAccountStore();
const appStore = useAppStore();

// API配置
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:5409";
const authHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem("token") || ""}`,
}));

// 步骤配置
const steps = [
  { key: "video", label: "选择视频" },
  { key: "accounts", label: "选择账号" },
  { key: "content", label: "编辑内容" },
  { key: "confirm", label: "确认发布" },
];

// 推荐话题
const recommendedTopics = [
  "生活",
  "美食",
  "旅行",
  "科技",
  "娱乐",
  "教育",
  "健康",
  "时尚",
  "音乐",
  "电影",
  "游戏",
  "运动",
];

// 发布任务列表
const publishTasks = ref([]);
let taskIdCounter = 1;

// 对话框状态
const topicDialogVisible = ref(false);
const customTopic = ref("");
const currentTask = ref(null);

// 可用账号
const availableAccounts = computed(() => accountStore.accounts);

// 方法定义
// 在每个task对象中添加平台选择字段
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
    // 添加这些字段
    currentPlatform: 2, // 默认视频号
    videosPerDay: 1,
    dailyTimes: ["10:00"],
    startDays: 0,
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

const handleVideoUploadSuccess = (response, file, task) => {
  if (response.code === 200) {
    const filePath = response.data.path || response.data;
    const filename = filePath.split("/").pop();

    const videoInfo = {
      name: file.name,
      path: filePath,
      url: materialApi.getMaterialPreviewUrl(filename),
      size: file.size,
      type: file.type,
    };

    task.videos.push(videoInfo);
    ElMessage.success("视频上传成功");
  } else {
    ElMessage.error(response.msg || "上传失败");
  }
};

const handleVideoUploadError = (error) => {
  ElMessage.error("视频上传失败");
  console.error("上传错误:", error);
};

const materialDialogVisible = ref(false);
const recentVideos = ref([]); // 最近上传的视频 (videoFile目录)
const libraryMaterials = ref([]); // 素材库视频 (videos目录)
const loadingMaterials = ref(false);
const selectedVideoIds = ref([]);
const selectedMaterialIds = ref([]);
const currentSelectingTask = ref(null);
const activeTab = ref("recent"); // 'recent' 或 'library'

const selectFromLibrary = async (task) => {
  currentSelectingTask.value = task;
  materialDialogVisible.value = true;
  selectedVideoIds.value = [];
  selectedMaterialIds.value = [];

  // 加载两种数据源
  await loadAllVideoSources();
};

// 替换原有的 addMoreVideos 方法
const addMoreVideos = async (task) => {
  await selectFromLibrary(task);
};

// 新增：加载所有视频源
const loadAllVideoSources = async () => {
  loadingMaterials.value = true;
  try {
    // 并行加载两种数据源
    const [recentResponse, libraryResponse] = await Promise.all([
      // 最近上传的视频 (videoFile目录) - 使用新接口
      fetch(`${apiBaseUrl}/getRecentUploads`).then((res) => res.json()),
      // 素材库视频 (数据库) - 使用现有接口
      materialApi.getAllMaterials(),
    ]);

    // 处理最近上传的视频
    if (recentResponse.code === 200) {
      recentVideos.value = recentResponse.data; // 后端已经过滤了视频文件
      console.log("最近上传的视频:", recentVideos.value);
    }

    // 处理素材库视频
    if (libraryResponse.code === 200) {
      libraryMaterials.value = libraryResponse.data.filter((material) =>
        isVideoFile(material.filename)
      );
      console.log("素材库视频:", libraryMaterials.value);
    }
  } catch (error) {
    console.error("获取视频列表出错:", error);
    ElMessage.error("获取视频列表失败");
  } finally {
    loadingMaterials.value = false;
  }
};

// 新增：切换最近视频选择状态
const toggleRecentVideoSelection = (videoId) => {
  const index = selectedVideoIds.value.indexOf(videoId);
  if (index > -1) {
    selectedVideoIds.value.splice(index, 1);
  } else {
    selectedVideoIds.value.push(videoId);
  }
};

// 更新：切换素材选择状态
const toggleMaterialSelection = (materialId) => {
  const index = selectedMaterialIds.value.indexOf(materialId);
  if (index > -1) {
    selectedMaterialIds.value.splice(index, 1);
  } else {
    selectedMaterialIds.value.push(materialId);
  }
};

// 新增：确认选择视频和素材
const confirmSelection = () => {
  const totalSelected =
    selectedVideoIds.value.length + selectedMaterialIds.value.length;
  if (totalSelected === 0) {
    ElMessage.warning("请选择至少一个视频");
    return;
  }

  const allSelectedVideos = [];

  // 处理最近上传的视频
  const selectedRecentVideos = recentVideos.value.filter((video) =>
    selectedVideoIds.value.includes(video.id)
  );

  selectedRecentVideos.forEach((video) => {
    allSelectedVideos.push({
      name: video.filename,
      path: video.file_path,
      url: `${apiBaseUrl}/getFile?filename=${video.file_path}`,
      size: video.filesize * 1024 * 1024,
      type: "video/mp4",
      id: `recent_${video.id}`,
      source: "recent", // 标记来源
    });
  });

  // 处理素材库视频
  const selectedLibraryMaterials = libraryMaterials.value.filter((material) =>
    selectedMaterialIds.value.includes(material.id)
  );

  selectedLibraryMaterials.forEach((material) => {
    allSelectedVideos.push({
      name: material.filename,
      path: material.file_path,
      url: materialApi.getMaterialPreviewUrl(
        material.file_path.split("/").pop()
      ),
      size: material.filesize * 1024 * 1024,
      type: "video/mp4",
      id: `library_${material.id}`,
      source: "library", // 标记来源
    });
  });

  // 添加到当前任务，避免重复
  allSelectedVideos.forEach((videoInfo) => {
    const exists = currentSelectingTask.value.videos.find(
      (v) => v.id === videoInfo.id || v.path === videoInfo.path
    );
    if (!exists) {
      currentSelectingTask.value.videos.push(videoInfo);
    }
  });

  materialDialogVisible.value = false;
  ElMessage.success(`已添加 ${allSelectedVideos.length} 个视频`);
};

// 新增：取消选择
const cancelSelection = () => {
  materialDialogVisible.value = false;
  selectedVideoIds.value = [];
  selectedMaterialIds.value = [];
};

// 改进视频文件判断方法（如果原来没有的话）
const isVideoFile = (filename) => {
  const videoExtensions = [
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".flv",
    ".wmv",
    ".webm",
    ".m4v",
    ".3gp",
    ".3g2",
    ".f4v",
    ".asf",
    ".rm",
    ".rmvb",
  ];
  return videoExtensions.some((ext) => filename.toLowerCase().endsWith(ext));
};
const formatDate = (dateString) => {
  if (!dateString) return "-";
  const date = new Date(dateString);
  return date.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
};

const previewMaterial = (material) => {
  const previewUrl = materialApi.getMaterialPreviewUrl(
    material.file_path.split("/").pop()
  );
  window.open(previewUrl, "_blank");
};
const previewRecentVideo = (video) => {
  // videoFile目录的文件直接使用文件名
  const previewUrl = `${apiBaseUrl}/getFile?filename=${video.file_path}`;
  window.open(previewUrl, "_blank");
};
// 新增：导航到素材管理页面
const navigateToMaterialManagement = () => {
  materialDialogVisible.value = false;
  router.push("/material-management");
};

// 改进现有的 removeVideo 方法，支持通过ID删除
const removeVideo = (task, index) => {
  task.videos.splice(index, 1);
};
const previewVideo = (video) => {
  window.open(video.url, "_blank");
};

const toggleAccountSelection = (task, account) => {
  if (account.status !== "正常") return;

  const index = task.selectedAccounts.indexOf(account.id);
  if (index > -1) {
    task.selectedAccounts.splice(index, 1);
  } else {
    task.selectedAccounts.push(account.id);
    task.currentPlatform = account.type;
  }
};

const clearAccountSelection = (task) => {
  task.selectedAccounts = [];
};

const getAccountName = (accountId) => {
  const account = accountStore.accounts.find((acc) => acc.id === accountId);
  return account ? account.name : accountId;
};

const openTopicSelector = (task) => {
  currentTask.value = task;
  customTopic.value = "";
  topicDialogVisible.value = true;
};

const addCustomTopic = () => {
  if (!customTopic.value.trim()) {
    ElMessage.warning("请输入话题内容");
    return;
  }

  if (
    currentTask.value &&
    !currentTask.value.topics.includes(customTopic.value.trim())
  ) {
    currentTask.value.topics.push(customTopic.value.trim());
    customTopic.value = "";
    ElMessage.success("话题添加成功");
  } else {
    ElMessage.warning("话题已存在");
  }
};

const toggleRecommendedTopic = (topic) => {
  if (!currentTask.value) return;

  const index = currentTask.value.topics.indexOf(topic);
  if (index > -1) {
    currentTask.value.topics.splice(index, 1);
  } else {
    currentTask.value.topics.push(topic);
  }
};

const removeTopic = (task, index) => {
  task.topics.splice(index, 1);
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
    // 数据验证（保持新版本的验证逻辑）
    if (task.videos.length === 0) {
      throw new Error("请先上传视频文件");
    }
    if (!task.title.trim()) {
      throw new Error("请输入标题");
    }
    if (task.selectedAccounts.length === 0) {
      throw new Error("请选择发布账号");
    }

    // 使用旧版本的数据格式构造（这是关键！）
    const publishData = {
      type: task.currentPlatform || 2, // 从任务中获取平台类型，默认视频号
      title: task.title,
      tags: task.topics || [], // 话题数组（不带#）
      fileList: task.videos.map((video) => {
        // 直接返回完整的文件路径，包含UUID
        return video.path || video.name;
      }),
      accountList: task.selectedAccounts.map((accountId) => {
        const account = availableAccounts.value.find(
          (acc) => acc.id === accountId
        );
        return account ? account.filePath : accountId;
      }),
      enableTimer: task.scheduleEnabled ? 1 : 0,
      videosPerDay: task.scheduleEnabled ? task.videosPerDay || 1 : 1,
      dailyTimes: task.scheduleEnabled
        ? task.dailyTimes || ["10:00"]
        : ["10:00"],
      startDays: task.scheduleEnabled ? task.startDays || 0 : 0,
      category: 0,
    };

    console.log("发布数据:", publishData); // 调试用

    task.publishProgress = 30;
    task.publishProgressText = "正在发布...";

    // 使用旧版本的fetch调用方式（这很重要！）
    const response = await fetch(`${apiBaseUrl}/postVideo`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders.value,
      },
      body: JSON.stringify(publishData),
    });

    const data = await response.json();

    if (data.code === 200) {
      task.publishProgress = 100;
      task.publishProgressText = "发布成功";
      task.status = "published";
      task.publishing = false;
      ElMessage.success("发布成功");
    } else {
      throw new Error(data.msg || "发布失败");
    }
  } catch (error) {
    console.error("发布错误:", error);
    task.status = "error";
    task.publishProgressText = "发布失败: " + error.message;
    task.publishing = false;
    ElMessage.error("发布失败: " + error.message);
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

const formatFileSize = (size) => {
  const mb = size / (1024 * 1024);
  return mb.toFixed(1) + "MB";
};

// 初始化
onMounted(async () => {
  // 创建一个默认任务
  addNewPublishTask();

  // 获取分组信息
  try {
    const groupsRes = await accountApi.getGroups();
    if (groupsRes.code === 200 && groupsRes.data) {
      accountStore.setGroups(groupsRes.data);
    }
  } catch (error) {
    console.warn("获取分组信息失败:", error);
  }
});
// 新增：分组选择相关方法
// 获取分组中的有效账号
const getValidAccountsInGroup = (groupId) => {
  return availableAccounts.value.filter(
    (acc) => acc.group_id === groupId && acc.status === "正常"
  );
};

// 获取未分组的有效账号
const getUngroupedValidAccounts = () => {
  return availableAccounts.value.filter(
    (acc) => !acc.group_id && acc.status === "正常"
  );
};

// 判断分组是否完全选中
const isGroupSelected = (task, groupId) => {
  const groupAccounts = getValidAccountsInGroup(groupId);
  if (groupAccounts.length === 0) return false;
  return groupAccounts.every((acc) => task.selectedAccounts.includes(acc.id));
};

// 判断分组是否部分选中
const isGroupPartialSelected = (task, groupId) => {
  const groupAccounts = getValidAccountsInGroup(groupId);
  if (groupAccounts.length === 0) return false;
  const selectedCount = groupAccounts.filter((acc) =>
    task.selectedAccounts.includes(acc.id)
  ).length;
  return selectedCount > 0 && selectedCount < groupAccounts.length;
};

// 判断未分组账号是否完全选中
const isUngroupedSelected = (task) => {
  const ungroupedAccounts = getUngroupedValidAccounts();
  if (ungroupedAccounts.length === 0) return false;
  return ungroupedAccounts.every((acc) =>
    task.selectedAccounts.includes(acc.id)
  );
};

// 判断未分组账号是否部分选中
const isUngroupedPartialSelected = (task) => {
  const ungroupedAccounts = getUngroupedValidAccounts();
  if (ungroupedAccounts.length === 0) return false;
  const selectedCount = ungroupedAccounts.filter((acc) =>
    task.selectedAccounts.includes(acc.id)
  ).length;
  return selectedCount > 0 && selectedCount < ungroupedAccounts.length;
};

// 切换分组选择状态
const toggleGroupSelection = (task, groupId) => {
  const groupAccounts = getValidAccountsInGroup(groupId);
  if (groupAccounts.length === 0) return;

  const isSelected = isGroupSelected(task, groupId);

  if (isSelected) {
    // 如果已选中，则取消选中该分组的所有账号
    groupAccounts.forEach((acc) => {
      const index = task.selectedAccounts.indexOf(acc.id);
      if (index > -1) {
        task.selectedAccounts.splice(index, 1);
      }
    });
  } else {
    // 如果未选中，则选中该分组的所有账号
    groupAccounts.forEach((acc) => {
      if (!task.selectedAccounts.includes(acc.id)) {
        task.selectedAccounts.push(acc.id);
        // 设置平台类型
        if (task.selectedAccounts.length === 1) {
          task.currentPlatform = acc.type;
        }
      }
    });
  }
};

// 切换未分组账号选择状态
const toggleUngroupedSelection = (task) => {
  const ungroupedAccounts = getUngroupedValidAccounts();
  if (ungroupedAccounts.length === 0) return;

  const isSelected = isUngroupedSelected(task);

  if (isSelected) {
    // 取消选中所有未分组账号
    ungroupedAccounts.forEach((acc) => {
      const index = task.selectedAccounts.indexOf(acc.id);
      if (index > -1) {
        task.selectedAccounts.splice(index, 1);
      }
    });
  } else {
    // 选中所有未分组账号
    ungroupedAccounts.forEach((acc) => {
      if (!task.selectedAccounts.includes(acc.id)) {
        task.selectedAccounts.push(acc.id);
        if (task.selectedAccounts.length === 1) {
          task.currentPlatform = acc.type;
        }
      }
    });
  }
};
// 简化的图标映射，只使用确实存在的图标
const getGroupIcon = (iconName) => {
  const iconMap = {
    Users: "User",
    User: "User",
    Briefcase: "User",
    Star: "Star",
    Heart: "User",
    Flag: "Flag",
    Trophy: "Star", // 用 Star 代替
    Gift: "User",
    Crown: "Star", // 用 Star 代替
    Diamond: "Star", // 用 Star 代替
    Fire: "User",
    Lightning: "User",
  };
  return iconMap[iconName] || "User";
};

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
</script>

<style lang="scss" scoped>
// 变量定义
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

// 发布任务卡片
.publish-tasks {
  display: flex;
  flex-direction: column;
  gap: $space-lg;
}

.publish-task-card {
  background: $bg-white;
  border-radius: $radius-xl;
  padding: $space-xl;
  box-shadow: $shadow-md;
  transition: all 0.3s ease;

  &:hover {
    box-shadow: $shadow-lg;
  }

  // 任务头部
  .task-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: $space-lg;

    .task-info {
      .task-title {
        font-size: 20px;
        font-weight: 600;
        color: $text-primary;
        margin: 0 0 $space-sm 0;
      }
    }

    .task-actions {
      display: flex;
      gap: $space-sm;
    }
  }

  // 进度指示器
  .progress-steps {
    display: flex;
    justify-content: space-between;
    margin-bottom: $space-2xl;
    position: relative;

    &::before {
      content: "";
      position: absolute;
      top: 20px;
      left: 20px;
      right: 20px;
      height: 2px;
      background-color: $border-light;
      z-index: 1;
    }

    .step-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: $space-sm;
      cursor: pointer;
      transition: all 0.3s ease;
      z-index: 2;

      .step-circle {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: $bg-white;
        border: 2px solid $border-light;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        color: $text-muted;
        transition: all 0.3s ease;
      }

      .step-label {
        font-size: 14px;
        color: $text-muted;
        font-weight: 500;
        transition: all 0.3s ease;
      }

      &.active {
        .step-circle {
          background-color: $primary;
          border-color: $primary;
          color: white;
        }

        .step-label {
          color: $primary;
          font-weight: 600;
        }
      }

      &.completed {
        .step-circle {
          background-color: $success;
          border-color: $success;
          color: white;
        }

        .step-label {
          color: $success;
        }
      }

      &.error {
        .step-circle {
          background-color: $danger;
          border-color: $danger;
          color: white;
        }

        .step-label {
          color: $danger;
        }
      }
    }
  }

  // 步骤内容
  .step-content {
    min-height: 400px;
    margin-bottom: $space-xl;
  }

  .step-panel {
    .step-header {
      margin-bottom: $space-lg;

      h4 {
        font-size: 18px;
        font-weight: 600;
        color: $text-primary;
        margin: 0 0 $space-xs 0;
      }

      p {
        color: $text-secondary;
        margin: 0;
      }
    }
  }

  // 上传区域
  .upload-section {
    .upload-area {
      .video-uploader {
        width: 100%;

        :deep(.el-upload-dragger) {
          width: 100%;
          height: 200px;
          border: 2px dashed $border-light;
          border-radius: $radius-xl;
          background-color: $bg-gray;
          transition: all 0.3s ease;

          &:hover {
            border-color: $primary;
            background-color: rgba(91, 115, 222, 0.05);
          }
        }

        .upload-content {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: $space-md;

          .upload-icon {
            font-size: 48px;
            color: $primary;
          }

          .upload-text {
            text-align: center;

            .upload-hint {
              color: $text-secondary;
              font-size: 14px;

              em {
                color: $primary;
                font-style: normal;
              }
            }
          }
        }
      }

      .upload-options {
        margin-top: $space-lg;
        text-align: center;

        .library-btn {
          padding: 12px 24px;
          border-radius: $radius-lg;
        }
      }
    }

    .selected-videos {
      .videos-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: $space-md;

        h5 {
          font-size: 16px;
          font-weight: 600;
          color: $text-primary;
          margin: 0;
        }
      }

      .videos-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: $space-md;

        .video-item {
          background: $bg-gray;
          border-radius: $radius-lg;
          overflow: hidden;
          transition: all 0.3s ease;

          &:hover {
            transform: translateY(-2px);
            box-shadow: $shadow-md;

            .video-overlay {
              opacity: 1;
            }
          }

          .video-preview {
            height: 120px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;

            .video-icon {
              font-size: 32px;
              color: white;
            }

            .video-overlay {
              position: absolute;
              top: 0;
              left: 0;
              right: 0;
              bottom: 0;
              background: rgba(0, 0, 0, 0.7);
              display: flex;
              align-items: center;
              justify-content: center;
              gap: $space-sm;
              opacity: 0;
              transition: opacity 0.3s ease;
            }
          }

          .video-info {
            padding: $space-md;

            .video-name {
              font-weight: 500;
              color: $text-primary;
              margin-bottom: $space-xs;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }

            .video-size {
              font-size: 12px;
              color: $text-secondary;
            }
          }
        }
      }
    }
  }

  // 账号选择
  .accounts-section {
    .accounts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: $space-md;
      margin-bottom: $space-lg;

      .account-card {
        background: $bg-gray;
        border: 2px solid transparent;
        border-radius: $radius-lg;
        padding: $space-md;
        cursor: pointer;
        transition: all 0.3s ease;
        position: relative;

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
        }

        .account-avatar {
          display: flex;
          justify-content: center;
          margin-bottom: $space-md;
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

          .selected-mark {
            position: absolute;
            top: -5px;
            right: -5px;
            width: 20px;
            height: 20px;
            background-color: $primary;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
          }
        }

        .account-info {
          text-align: center;

          .account-name {
            font-weight: 500;
            color: $text-primary;
            margin-bottom: $space-xs;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .account-platform {
            font-size: 12px;
            color: $text-secondary;
          }
        }
      }
    }

    .selected-summary {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(91, 115, 222, 0.1);
      padding: $space-md;
      border-radius: $radius-lg;

      .summary-info {
        display: flex;
        align-items: center;
        gap: $space-sm;
        color: $primary;
        font-weight: 500;
      }
    }
  }

  // 内容表单
  .content-form {
    .publish-form {
      .title-input {
        :deep(.el-textarea__inner) {
          border-radius: $radius-md;
        }
      }

      .topics-section {
        .selected-topics {
          display: flex;
          flex-wrap: wrap;
          gap: $space-sm;
          margin-bottom: $space-md;
          min-height: 32px;

          .topic-tag {
            border-radius: $radius-md;
          }
        }
      }

      .publish-settings {
        .schedule-options {
          margin-top: $space-md;
          padding: $space-md;
          background: $bg-gray;
          border-radius: $radius-md;

          .schedule-row {
            display: flex;
            align-items: center;
            gap: $space-md;

            .label {
              min-width: 80px;
              font-weight: 500;
              color: $text-primary;
            }
          }
        }
      }
    }
  }

  // 确认发布
  .confirm-content {
    .publish-preview {
      background: $bg-gray;
      border-radius: $radius-lg;
      padding: $space-lg;
      margin-bottom: $space-lg;

      .preview-section {
        &:not(:last-child) {
          margin-bottom: $space-lg;
          padding-bottom: $space-lg;
          border-bottom: 1px solid $border-light;
        }

        h5 {
          font-size: 16px;
          font-weight: 600;
          color: $text-primary;
          margin: 0 0 $space-md 0;
        }

        .videos-preview {
          display: flex;
          flex-wrap: wrap;
          gap: $space-sm;

          .video-preview-item {
            display: flex;
            align-items: center;
            gap: $space-xs;
            background: $bg-white;
            padding: $space-sm $space-md;
            border-radius: $radius-md;
            font-size: 14px;

            .video-icon {
              color: $primary;
            }
          }
        }

        .accounts-preview {
          display: flex;
          flex-wrap: wrap;
          gap: $space-sm;

          .account-tag {
            border-radius: $radius-md;
          }
        }

        .content-preview {
          .preview-item {
            display: flex;
            margin-bottom: $space-sm;

            &:last-child {
              margin-bottom: 0;
            }

            .label {
              min-width: 80px;
              font-weight: 500;
              color: $text-secondary;
            }

            .value {
              color: $text-primary;
            }
          }
        }
      }
    }

    .publish-progress {
      text-align: center;
      padding: $space-lg;

      .progress-text {
        margin-top: $space-md;
        color: $text-secondary;
      }
    }
  }

  // 步骤导航
  .step-navigation {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: $space-lg;
    border-top: 1px solid $border-light;

    .nav-left,
    .nav-right {
      display: flex;
      gap: $space-sm;
    }
  }
}

// 话题选择对话框
.topic-dialog {
  .topic-selector {
    .custom-topic {
      margin-bottom: $space-lg;
    }

    .recommended-topics {
      h5 {
        font-size: 16px;
        font-weight: 600;
        color: $text-primary;
        margin: 0 0 $space-md 0;
      }

      .topics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
        gap: $space-sm;
      }
    }
  }
}
/* 在 PublishCenter.vue 的 <style> 中添加以下样式： */

// 素材选择对话框
.material-dialog {
  .material-selector {
    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: $space-md;
      padding: $space-2xl;
      color: $text-secondary;

      .is-loading {
        font-size: 32px;
        animation: rotate 1s linear infinite;
      }
    }

    .videos-content {
      .video-tabs {
        :deep(.el-tabs__header) {
          margin-bottom: $space-lg;
        }

        :deep(.el-tabs__nav-wrap) {
          background: $bg-gray;
          border-radius: $radius-md;
          padding: $space-xs;
        }

        :deep(.el-tabs__active-bar) {
          display: none;
        }

        :deep(.el-tabs__item) {
          padding: $space-sm $space-lg;
          border-radius: $radius-sm;
          font-weight: 500;
          transition: all 0.3s ease;

          &.is-active {
            background: white;
            color: $primary;
            box-shadow: $shadow-sm;
          }
        }
      }

      .tab-content {
        .videos-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: $space-lg;

          h5 {
            font-size: 16px;
            font-weight: 600;
            color: $text-primary;
            margin: 0;
          }

          .selection-info {
            display: flex;
            align-items: center;
            gap: $space-md;
            font-size: 14px;
            color: $text-secondary;
          }
        }

        .videos-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: $space-md;
          max-height: 400px;
          overflow-y: auto;

          .video-item {
            background: $bg-gray;
            border: 2px solid transparent;
            border-radius: $radius-lg;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.3s ease;

            &:hover {
              transform: translateY(-2px);
              box-shadow: $shadow-md;

              .video-overlay {
                opacity: 1;
              }
            }

            &.selected {
              border-color: $primary;
              box-shadow: 0 0 0 2px rgba(91, 115, 222, 0.2);
            }

            .video-preview {
              height: 120px;
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
              display: flex;
              align-items: center;
              justify-content: center;
              position: relative;

              .video-icon {
                font-size: 32px;
                color: white;
              }

              .video-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: 0;
                transition: opacity 0.3s ease;

                .overlay-content {
                  display: flex;
                  gap: $space-sm;
                }
              }

              .selected-mark {
                position: absolute;
                top: 8px;
                right: 8px;
                width: 24px;
                height: 24px;
                background-color: $primary;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 14px;
                box-shadow: $shadow-md;
              }

              .source-badge {
                position: absolute;
                top: 8px;
                left: 8px;
                padding: 2px 8px;
                border-radius: $radius-sm;
                font-size: 11px;
                font-weight: 500;
                color: white;

                &.recent {
                  background-color: $warning;
                }

                &.library {
                  background-color: $success;
                }
              }
            }

            .video-info {
              padding: $space-md;

              .video-name {
                font-weight: 500;
                color: $text-primary;
                margin-bottom: $space-xs;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                font-size: 14px;
              }

              .video-meta {
                display: flex;
                justify-content: space-between;
                font-size: 12px;
                color: $text-secondary;

                .video-size {
                  font-weight: 500;
                }
              }
            }
          }
        }

        .empty-videos {
          padding: $space-2xl;
          text-align: center;
        }
      }
    }
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
} /* 在 PublishCenter.vue 的 <style> 中添加以下样式： */

// 素材选择对话框
.material-dialog {
  .material-selector {
    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: $space-md;
      padding: $space-2xl;
      color: $text-secondary;

      .is-loading {
        font-size: 32px;
        animation: rotate 1s linear infinite;
      }
    }

    .materials-content {
      .materials-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: $space-lg;

        h5 {
          font-size: 16px;
          font-weight: 600;
          color: $text-primary;
          margin: 0;
        }

        .selection-info {
          display: flex;
          align-items: center;
          gap: $space-md;
          font-size: 14px;
          color: $text-secondary;
        }
      }

      .materials-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: $space-md;
        max-height: 400px;
        overflow-y: auto;

        .material-item {
          background: $bg-gray;
          border: 2px solid transparent;
          border-radius: $radius-lg;
          overflow: hidden;
          cursor: pointer;
          transition: all 0.3s ease;

          &:hover {
            transform: translateY(-2px);
            box-shadow: $shadow-md;

            .material-overlay {
              opacity: 1;
            }
          }

          &.selected {
            border-color: $primary;
            box-shadow: 0 0 0 2px rgba(91, 115, 222, 0.2);
          }

          .material-preview {
            height: 120px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;

            .video-icon {
              font-size: 32px;
              color: white;
            }

            .material-overlay {
              position: absolute;
              top: 0;
              left: 0;
              right: 0;
              bottom: 0;
              background: rgba(0, 0, 0, 0.7);
              display: flex;
              align-items: center;
              justify-content: center;
              opacity: 0;
              transition: opacity 0.3s ease;

              .overlay-content {
                display: flex;
                gap: $space-sm;
              }
            }

            .selected-mark {
              position: absolute;
              top: 8px;
              right: 8px;
              width: 24px;
              height: 24px;
              background-color: $primary;
              border-radius: 50%;
              display: flex;
              align-items: center;
              justify-content: center;
              color: white;
              font-size: 14px;
              box-shadow: $shadow-md;
            }
          }

          .material-info {
            padding: $space-md;

            .material-name {
              font-weight: 500;
              color: $text-primary;
              margin-bottom: $space-xs;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
              font-size: 14px;
            }

            .material-meta {
              display: flex;
              justify-content: space-between;
              font-size: 12px;
              color: $text-secondary;

              .material-size {
                font-weight: 500;
              }
            }
          }
        }
      }
    }

    .empty-materials {
      padding: $space-2xl;
      text-align: center;
    }
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
// 响应式设计
@media (max-width: 768px) {
  .page-header .header-content {
    flex-direction: column;
    align-items: stretch;
    gap: $space-md;
  }

  .publish-task-card {
    padding: $space-lg;

    .task-header {
      flex-direction: column;
      gap: $space-md;
    }

    .progress-steps {
      flex-direction: column;
      gap: $space-md;

      &::before {
        display: none;
      }

      .step-item {
        flex-direction: row;
        justify-content: flex-start;
      }
    }

    .accounts-section {
      .accounts-grid {
        grid-template-columns: 1fr !important;
      }
    }

    .step-navigation {
      flex-direction: column;
      gap: $space-md;
    }
  }
}
// 分组选择器样式
.group-selector {
  margin-bottom: $space-xl;

  h5 {
    font-size: 16px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 $space-md 0;
  }

  .groups-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: $space-md;

    .group-selector-item {
      background: $bg-gray;
      border: 2px solid transparent;
      border-radius: $radius-lg;
      padding: $space-md;
      cursor: pointer;
      transition: all 0.3s ease;
      display: flex;
      justify-content: space-between;
      align-items: center;

      &:hover {
        transform: translateY(-1px);
        box-shadow: $shadow-md;
        border-color: rgba(91, 115, 222, 0.3);
      }

      &.selected {
        border-color: $primary;
        background-color: rgba(91, 115, 222, 0.1);
      }

      &.partial {
        border-color: $warning;
        background-color: rgba(245, 158, 11, 0.1);
      }

      .group-info {
        display: flex;
        align-items: center;
        gap: $space-sm;

        .group-icon {
          width: 36px;
          height: 36px;
          border-radius: $radius-md;
          display: flex;
          align-items: center;
          justify-content: center;

          .el-icon {
            font-size: 18px;
            color: white;
          }

          &.ungrouped {
            background-color: $text-muted;
          }
        }

        .group-details {
          .group-name {
            display: block;
            font-weight: 500;
            color: $text-primary;
            margin-bottom: 2px;
          }

          .group-count {
            font-size: 12px;
            color: $text-secondary;
          }
        }
      }

      .group-selection-status {
        .el-icon {
          font-size: 20px;
          color: $primary;

          &.partial-icon {
            color: $warning;
          }
        }
      }
    }
  }
}

.divider {
  text-align: center;
  margin: $space-xl 0;
  position: relative;

  &::before {
    content: "";
    position: absolute;
    top: 50%;
    left: 0;
    right: 0;
    height: 1px;
    background-color: $border-light;
  }

  span {
    background-color: $bg-light;
    padding: 0 $space-md;
    color: $text-secondary;
    font-size: 14px;
  }
}

// 账号卡片中的分组标签
.account-card {
  .account-group {
    margin-top: 4px;
  }
}
</style>