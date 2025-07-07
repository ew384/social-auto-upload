const { app, BrowserWindow, Menu } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const net = require('net')

let mainWindow
let pythonProcess
const isDev = process.env.NODE_ENV === 'development'

// 检查端口是否被占用
function checkPort(port) {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.listen(port, () => {
      server.once('close', () => resolve(true))
      server.close()
    })
    server.on('error', () => resolve(false))
  })
}

// 等待后端服务启动
function waitForBackend(maxRetries = 30) {
  return new Promise((resolve, reject) => {
    let retries = 0
    
    const check = () => {
      checkPort(5409).then(portAvailable => {
        if (!portAvailable) {
          console.log('✅ 后端服务已启动')
          resolve()
        } else if (retries < maxRetries) {
          retries++
          console.log(`⏳ 等待后端启动... (${retries}/${maxRetries})`)
          setTimeout(check, 1000)
        } else {
          reject(new Error('后端启动超时'))
        }
      })
    }
    
    check()
  })
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      webSecurity: false
    },
    titleBarStyle: 'hiddenInset',
    show: false,
    icon: path.join(__dirname, '../public/vite.svg')
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
    mainWindow.show()
  } else {
    waitForBackend().then(() => {
      mainWindow.loadURL('http://localhost:5409')
      mainWindow.show()
    }).catch(err => {
      console.error('后端启动失败:', err)
      // 如果后端启动失败，加载静态文件
      mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
      mainWindow.show()
    })
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function startPythonBackend() {
  if (isDev) {
    console.log('开发环境：跳过启动 Python 后端')
    return
  }

  // 修复后端路径
  const backendPath = path.join(process.resourcesPath, 'backend')
  let pythonExecutable = path.join(backendPath, 'sau_backend')
  
  // 检查可执行文件是否存在
  const fs = require('fs')
  if (!fs.existsSync(pythonExecutable)) {
    console.error('Python 后端可执行文件不存在:', pythonExecutable)
    return
  }

  console.log('启动 Python 后端:', pythonExecutable)
  console.log('工作目录:', backendPath)

  pythonProcess = spawn(pythonExecutable, [], {
    cwd: backendPath,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: {
      ...process.env,
      PYTHONPATH: backendPath
    }
  })

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`)
  })

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Backend Error] ${data.toString().trim()}`)
  })

  pythonProcess.on('close', (code) => {
    console.log(`Python 后端进程退出，代码: ${code}`)
  })

  pythonProcess.on('error', (err) => {
    console.error('Python 后端启动失败:', err)
  })
}

function stopPythonBackend() {
  if (pythonProcess) {
    console.log('正在停止 Python 后端...')
    pythonProcess.kill('SIGTERM')
    
    setTimeout(() => {
      if (pythonProcess && !pythonProcess.killed) {
        console.log('强制结束 Python 后端')
        pythonProcess.kill('SIGKILL')
      }
    }, 5000)
    
    pythonProcess = null
  }
}

function createMenu() {
  const template = [
    {
      label: 'SAU系统',
      submenu: [
        { role: 'about', label: '关于 SAU' },
        { type: 'separator' },
        { role: 'services', label: '服务' },
        { type: 'separator' },
        { role: 'hide', label: '隐藏' },
        { role: 'hideothers', label: '隐藏其他' },
        { role: 'unhide', label: '显示全部' },
        { type: 'separator' },
        { role: 'quit', label: '退出 SAU' }
      ]
    },
    {
      label: '编辑',
      submenu: [
        { role: 'undo', label: '撤销' },
        { role: 'redo', label: '重做' },
        { type: 'separator' },
        { role: 'cut', label: '剪切' },
        { role: 'copy', label: '复制' },
        { role: 'paste', label: '粘贴' },
        { role: 'selectall', label: '全选' }
      ]
    },
    {
      label: '视图',
      submenu: [
        { role: 'reload', label: '重新加载' },
        { role: 'forceReload', label: '强制重新加载' },
        { role: 'toggleDevTools', label: '开发者工具' },
        { type: 'separator' },
        { role: 'resetZoom', label: '实际大小' },
        { role: 'zoomIn', label: '放大' },
        { role: 'zoomOut', label: '缩小' },
        { type: 'separator' },
        { role: 'togglefullscreen', label: '切换全屏' }
      ]
    },
    {
      label: '窗口',
      submenu: [
        { role: 'minimize', label: '最小化' },
        { role: 'close', label: '关闭' }
      ]
    }
  ]

  const menu = Menu.buildFromTemplate(template)
  Menu.setApplicationMenu(menu)
}

app.whenReady().then(() => {
  createMenu()
  startPythonBackend()
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  stopPythonBackend()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  stopPythonBackend()
})

process.on('SIGINT', () => {
  stopPythonBackend()
  app.quit()
})

process.on('SIGTERM', () => {
  stopPythonBackend()
  app.quit()
})
