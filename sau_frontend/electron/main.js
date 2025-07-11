const { app, BrowserWindow, dialog } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const fs = require('fs')

let mainWindow
let backendProcess
const isDev = process.env.NODE_ENV === 'development'

// 日志函数
function log(message) {
    console.log(`[SAU] ${new Date().toISOString()}: ${message}`)
}

function logError(message, error) {
    console.error(`[SAU ERROR] ${new Date().toISOString()}: ${message}`, error)
}

// 检查端口是否被占用
function isPortInUse(port) {
    return new Promise((resolve) => {
        const net = require('net')
        const server = net.createServer()
        
        server.once('error', () => {
            log(`端口 ${port} 已被占用`)
            resolve(true)
        })
        server.once('listening', () => {
            server.close()
            log(`端口 ${port} 可用`)
            resolve(false)
        })
        
        server.listen(port)
    })
}

// 等待后端服务启动
async function waitForBackend(maxWait = 30000) {
    log('开始等待后端启动...')
    const startTime = Date.now()
    
    while (Date.now() - startTime < maxWait) {
        if (await isPortInUse(5409)) {
            log('后端服务已启动')
            return true
        }
        await new Promise(resolve => setTimeout(resolve, 1000))
        log(`等待后端启动... ${Math.floor((Date.now() - startTime) / 1000)}s`)
    }
    
    log('后端启动超时')
    return false
}

// 显示错误对话框
function showErrorDialog(title, content) {
    if (mainWindow) {
        dialog.showErrorBox(title, content)
    }
}

// 创建窗口
function createWindow() {
    log('创建主窗口...')
    
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        show: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            webSecurity: false
        },
        titleBarStyle: 'hiddenInset'
    })

    if (isDev) {
        log('开发环境模式')
        mainWindow.loadURL('http://localhost:5173')
        mainWindow.webContents.openDevTools()
        mainWindow.show()
        return
    }

    log('生产环境模式，等待后端启动...')
    
    // 生产环境 - 等待后端启动
    waitForBackend().then(backendReady => {
        if (backendReady) {
            log('后端已准备就绪，加载后端界面')
            mainWindow.loadURL('http://localhost:5409')
        } else {
            log('后端启动失败，加载静态文件')
            const indexPath = path.join(__dirname, '../dist/index.html')
            log(`静态文件路径: ${indexPath}`)
            
            if (fs.existsSync(indexPath)) {
                mainWindow.loadFile(indexPath)
            } else {
                logError('静态文件不存在', indexPath)
                showErrorDialog('启动错误', '无法找到应用文件，请重新安装应用。')
            }
        }
        mainWindow.show()
    }).catch(err => {
        logError('检查后端失败', err)
        // 回退到静态文件
        const indexPath = path.join(__dirname, '../dist/index.html')
        mainWindow.loadFile(indexPath)
        mainWindow.show()
    })

    // 添加页面加载事件监听
    mainWindow.webContents.on('did-finish-load', () => {
        log('页面加载完成')
    })

    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
        logError('页面加载失败', `${errorCode}: ${errorDescription}`)
    })

    mainWindow.on('closed', () => {
        mainWindow = null
    })
}

// 启动后端服务
function startBackend() {
    if (isDev) {
        log('开发环境：跳过后端启动')
        return
    }

    log('开始启动后端服务...')
    
    // 获取后端路径
    const resourcesPath = process.resourcesPath
    const backendPath = path.join(resourcesPath, 'backend')
    const execPath = path.join(backendPath, 'sau_backend')
    
    log(`Resources 路径: ${resourcesPath}`)
    log(`后端目录: ${backendPath}`)
    log(`可执行文件: ${execPath}`)
    
    // 检查路径是否存在
    if (!fs.existsSync(resourcesPath)) {
        logError('Resources 目录不存在', resourcesPath)
        showErrorDialog('启动错误', `Resources 目录不存在: ${resourcesPath}`)
        return
    }
    
    if (!fs.existsSync(backendPath)) {
        logError('后端目录不存在', backendPath)
        showErrorDialog('启动错误', `后端目录不存在: ${backendPath}`)
        return
    }
    
    if (!fs.existsSync(execPath)) {
        logError('后端可执行文件不存在', execPath)
        showErrorDialog('启动错误', `后端可执行文件不存在: ${execPath}\n\n请确保应用完整安装。`)
        return
    }

    // 检查执行权限
    try {
        fs.accessSync(execPath, fs.constants.X_OK)
        log('后端文件具有执行权限')
    } catch (err) {
        logError('后端文件没有执行权限', err)
        try {
            fs.chmodSync(execPath, 0o755)
            log('已设置执行权限')
        } catch (chmodErr) {
            logError('设置执行权限失败', chmodErr)
            showErrorDialog('权限错误', '无法设置后端文件执行权限，请手动设置。')
            return
        }
    }

    // 启动后端进程
    try {
        log('启动后端进程...')
        
        backendProcess = spawn(execPath, [], {
            cwd: backendPath,
            stdio: ['pipe', 'pipe', 'pipe'],
            env: {
                ...process.env,
                PYTHONPATH: backendPath,
                PYTHONUNBUFFERED: '1'
            }
        })

        log(`后端进程已启动，PID: ${backendProcess.pid}`)

        backendProcess.stdout.on('data', (data) => {
            const output = data.toString().trim()
            log(`[Backend] ${output}`)
        })

        backendProcess.stderr.on('data', (data) => {
            const output = data.toString().trim()
            logError(`[Backend Error] ${output}`)
        })

        backendProcess.on('error', (error) => {
            logError('后端进程启动失败', error)
            showErrorDialog('后端启动失败', `后端服务启动失败: ${error.message}`)
        })

        backendProcess.on('close', (code, signal) => {
            log(`后端进程退出，代码: ${code}, 信号: ${signal}`)
            if (code !== 0 && code !== null) {
                logError('后端异常退出', `退出代码: ${code}`)
            }
        })

        backendProcess.on('spawn', () => {
            log('后端进程已成功启动')
        })

    } catch (error) {
        logError('启动后端进程时发生异常', error)
        showErrorDialog('启动失败', `启动后端服务时发生错误: ${error.message}`)
    }
}

// 停止后端服务
function stopBackend() {
    if (backendProcess) {
        log('正在停止后端进程...')
        
        try {
            backendProcess.kill('SIGTERM')
            
            setTimeout(() => {
                if (backendProcess && !backendProcess.killed) {
                    log('强制结束后端进程')
                    backendProcess.kill('SIGKILL')
                }
            }, 5000)
            
        } catch (error) {
            logError('停止后端进程时发生错误', error)
        }
        
        backendProcess = null
    }
}

// 应用事件处理
app.whenReady().then(() => {
    log('Electron 应用已准备就绪')
    startBackend()
    createWindow()

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow()
        }
    })
})

app.on('window-all-closed', () => {
    log('所有窗口已关闭')
    stopBackend()
    if (process.platform !== 'darwin') {
        app.quit()
    }
})

app.on('before-quit', () => {
    log('应用即将退出')
    stopBackend()
})

// 进程退出处理
process.on('SIGINT', () => {
    log('收到 SIGINT 信号')
    stopBackend()
    app.quit()
})

process.on('SIGTERM', () => {
    log('收到 SIGTERM 信号')
    stopBackend()
    app.quit()
})

// 未捕获异常处理
process.on('uncaughtException', (error) => {
    logError('未捕获的异常', error)
    stopBackend()
})

process.on('unhandledRejection', (reason, promise) => {
    logError('未处理的 Promise 拒绝', { reason, promise })
})

log('Electron main.js 已加载完成')
