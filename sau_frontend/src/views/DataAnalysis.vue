<!-- sau_frontend/src/views/DataAnalysis.vue -->
<template>
  <div class="data-analysis-page">
    <div class="page-header">
      <h1 class="page-title">数据分析</h1>
      <p class="page-subtitle">查看账号和内容的数据分析报告</p>
    </div>
    
    <div class="content-area">
      <el-card class="feature-card">
        <template #header>
          <div class="card-header">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据分析</span>
          </div>
        </template>
        <p>数据分析功能正在开发中...</p>
        <el-button type="primary" disabled>敬请期待</el-button>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { DataAnalysis } from "@element-plus/icons-vue";
</script>

<style lang="scss" scoped>
.data-analysis-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;

  .page-title {
    font-size: 28px;
    font-weight: 700;
    color: #1e293b;
    margin: 0 0 8px 0;
  }

  .page-subtitle {
    font-size: 16px;
    color: #64748b;
    margin: 0;
  }
}

.content-area {
  .feature-card {
    text-align: center;
    padding: 40px;

    .card-header {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-weight: bold;

      .el-icon {
        color: #5b73de;
      }
    }

    p {
      color: #64748b;
      margin: 20px 0;
    }
  }
}
</style>
</template>