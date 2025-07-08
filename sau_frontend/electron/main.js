const { app, BrowserWindow } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let mainWindow
let backendProcess

// 简化的端口检查
function isPortInUse(port) {
  return new Promise((resolve) => {
    const net = require('net')
    const server = net.createServer()
    
    server.once('error', () => resolve(true))
    server.once('listening', () => {
      server.close()
      resolve(false)
    })
    
    server.listen(port)
  })
}

// 等待后端启动
async function waitForBackend(maxWait = 30000) {
  const startTime = Date.now()
  
  while (Date.now() - startTime < maxWait) {
    if (await isPortInUse(5409)) {
      return true
    }
    await new Promise(resolve => setTimeout(resolve, 1000))
  }
  
  return false
}

// 创建窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  })

  // 开发环境
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.show()
    return
  }

  // 生产环境 - 等待后端启动
  waitForBackend().then(backendReady => {
    if (backendReady) {
      mainWindow.loadURL('http://localhost:5409')
    } else {
      // 后端启动失败，加载静态文件
      mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
    }
    mainWindow.show()
  })
}

// 启动 Python 后端
function startBackend() {
  if (process.env.NODE_ENV === 'development') return

  const backendPath = path.join(process.resourcesPath, 'backend')
  const execPath = path.join(backendPath, 'sau_backend')
  
  try {
    backendProcess = spawn(execPath, [], {
      cwd: backendPath,
      stdio: 'pipe'
    })
    
    backendProcess.on('error', console.error)
  } catch (error) {
    console.error('启动后端失败:', error)
  }
}

// 停止后端
function stopBackend() {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
}

// 应用事件
app.whenReady().then(() => {
  startBackend()
  createWindow()
})

app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', stopBackend)
