/**
 * AI个人助理 - Electron主进程
 * 连接到云服务器版本
 */

const { app, BrowserWindow, Menu, Tray, nativeImage, shell, ipcMain, Notification } = require('electron');
const path = require('path');

// 云服务器地址
const CLOUD_SERVER_URL = 'http://47.109.148.176/ai/';

let mainWindow = null;
let tray = null;

/**
 * 创建主窗口
 */
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 700,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
            webSecurity: true,
            allowRunningInsecureContent: false
        },
        // Mac原生标题栏样式
        titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
        trafficLightPosition: process.platform === 'darwin' ? { x: 15, y: 15 } : undefined,
        backgroundColor: '#667eea',
        show: false, // 先不显示，等加载完成
        icon: getAppIcon()
    });

    // 加载云服务器Web页面
    mainWindow.loadURL(CLOUD_SERVER_URL);

    // 页面加载完成后显示窗口
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    // 处理新窗口打开（在默认浏览器中打开外部链接）
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        // 云服务器内部链接在应用内打开
        if (url.startsWith(CLOUD_SERVER_URL)) {
            return { action: 'allow' };
        }
        // 其他链接在浏览器中打开
        shell.openExternal(url);
        return { action: 'deny' };
    });

    // 页面加载失败处理
    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
        console.error('页面加载失败:', errorDescription);
        // 显示错误页面或重试
        if (errorCode !== -3) { // -3 是取消加载，不算错误
            showErrorPage();
        }
    });

    // 开发环境打开开发者工具
    if (!app.isPackaged) {
        mainWindow.webContents.openDevTools();
    }

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // 创建系统托盘
    createTray();
}

/**
 * 显示错误页面
 */
function showErrorPage() {
    const errorHtml = `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .error-container {
                    text-align: center;
                    padding: 40px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                }
                h1 { font-size: 48px; margin: 0 0 20px 0; }
                p { font-size: 18px; margin: 10px 0; }
                button {
                    margin-top: 30px;
                    padding: 12px 30px;
                    font-size: 16px;
                    background: white;
                    color: #667eea;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 600;
                }
                button:hover { opacity: 0.9; }
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>❌ 连接失败</h1>
                <p>无法连接到云服务器</p>
                <p style="font-size:14px; opacity:0.8;">服务器地址: ${CLOUD_SERVER_URL}</p>
                <button onclick="location.reload()">🔄 重试</button>
            </div>
        </body>
        </html>
    `;
    mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(errorHtml));
}

/**
 * 创建系统托盘
 */
function createTray() {
    const icon = getTrayIcon();
    tray = new Tray(icon);

    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'AI个人助理',
            enabled: false,
            icon: icon.resize({ width: 16, height: 16 })
        },
        { type: 'separator' },
        {
            label: '显示窗口',
            click: () => {
                if (mainWindow) {
                    mainWindow.show();
                    mainWindow.focus();
                }
            }
        },
        {
            label: '刷新',
            click: () => {
                if (mainWindow) {
                    mainWindow.reload();
                }
            }
        },
        { type: 'separator' },
        {
            label: '退出',
            click: () => {
                app.quit();
            }
        }
    ]);

    tray.setToolTip('AI个人助理');
    tray.setContextMenu(contextMenu);

    // 点击托盘图标显示窗口
    tray.on('click', () => {
        if (mainWindow) {
            if (mainWindow.isVisible()) {
                mainWindow.hide();
            } else {
                mainWindow.show();
                mainWindow.focus();
            }
        }
    });
}

/**
 * 获取应用图标
 */
function getAppIcon() {
    // 这里可以返回自定义图标
    // 暂时返回默认图标
    if (process.platform === 'darwin') {
        return path.join(__dirname, 'assets/icons/icon.icns');
    } else if (process.platform === 'win32') {
        return path.join(__dirname, 'assets/icons/icon.ico');
    } else {
        return path.join(__dirname, 'assets/icons/icon.png');
    }
}

/**
 * 获取托盘图标
 */
function getTrayIcon() {
    const iconPath = process.platform === 'darwin'
        ? path.join(__dirname, 'assets/icons/tray-icon.png')
        : path.join(__dirname, 'assets/icons/tray-icon.png');

    try {
        return nativeImage.createFromPath(iconPath);
    } catch (e) {
        // 如果找不到图标文件，创建一个简单的图标
        return nativeImage.createFromDataURL('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAERlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQAAAABAAAAIKADAAQAAAABAAAAIAAAAACshmLzAAAA2UlEQVRYCe2WQQ6AIAxE6f2PrBvjQhMTo1CnNODGN4EmhT5oC4L8fAKEEELI/wFmxjVr1+xdt2/dfvXtm7dvn7vvp++f/d39fvt9TwghZP8AZsa1aNei3Yv2Ltq/aP+iA4wOMDrE6BCjg4wOMjrM6DCjA40ONDrU6FCjg40ONjrc6HCjA44OODro6KCjA48OPDr46OCjB4AeAHoI6CGgx4AeA3oQ6EGgR4EeBXoY6GGgx4EeB3og6IGgR4IeCXoo6KGgx4IeC3ow6MGgR4MeDXo46OGgx4MeDiGEEPILPoN7EqjYJzlEAAAAAElFTkSuQmCC');
    }
}

/**
 * 应用启动
 */
app.whenReady().then(() => {
    createWindow();

    // Mac特定：点击Dock图标时重新创建窗口
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

/**
 * 所有窗口关闭时的处理
 */
app.on('window-all-closed', () => {
    // Mac上即使所有窗口关闭，应用也保持运行
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

/**
 * 应用退出前的清理
 */
app.on('before-quit', () => {
    // 清理托盘
    if (tray) {
        tray.destroy();
    }
});

// IPC通信处理
ipcMain.on('app-info', (event) => {
    event.returnValue = {
        name: app.getName(),
        version: app.getVersion(),
        platform: process.platform
    };
});

/**
 * 显示macOS原生通知
 */
ipcMain.on('show-notification', (event, { title, body, silent = false }) => {
    try {
        if (Notification.isSupported()) {
            const notification = new Notification({
                title: title || 'AI个人助理',
                body: body || '',
                silent: silent,
                sound: 'Glass', // macOS系统提示音
                urgency: 'critical' // 重要级别
            });

            notification.show();

            // 点击通知时显示主窗口
            notification.on('click', () => {
                if (mainWindow) {
                    if (mainWindow.isMinimized()) mainWindow.restore();
                    mainWindow.show();
                    mainWindow.focus();
                }
            });

            console.log('✅ 通知已显示:', title, body);
            event.reply('notification-shown', { success: true });
        } else {
            console.warn('⚠️ 系统不支持通知');
            event.reply('notification-shown', { success: false, error: 'Notifications not supported' });
        }
    } catch (error) {
        console.error('❌ 显示通知失败:', error);
        event.reply('notification-shown', { success: false, error: error.message });
    }
});

/**
 * 播放提示音
 */
ipcMain.on('play-sound', (event, soundName = 'Glass') => {
    try {
        // macOS系统音效
        const { execSync } = require('child_process');
        execSync(`afplay /System/Library/Sounds/${soundName}.aiff`);
        event.reply('sound-played', { success: true });
    } catch (error) {
        console.error('❌ 播放声音失败:', error);
        event.reply('sound-played', { success: false, error: error.message });
    }
});

// ========================================
// 用户认证相关IPC处理器（新增）
// ========================================

// 本地服务器地址（如果使用本地Python服务器）
const LOCAL_SERVER_URL = 'http://localhost:8000';
// 使用云服务器或本地服务器
const API_BASE_URL = CLOUD_SERVER_URL || LOCAL_SERVER_URL;

/**
 * 用户登录
 */
ipcMain.handle('user-login', async (event, { username, password }) => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await response.json();
        return { success: true, data };
    } catch (error) {
        console.error('❌ 登录失败:', error);
        return { success: false, message: error.message };
    }
});

/**
 * 用户注册（旧版，兼容保留）
 */
ipcMain.handle('user-register', async (event, { username, password, phone }) => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, phone })
        });
        const data = await response.json();
        return { success: true, data };
    } catch (error) {
        console.error('❌ 注册失败:', error);
        return { success: false, message: error.message };
    }
});

/**
 * 用户退出
 */
ipcMain.handle('user-logout', async (event) => {
    try {
        // 获取存储的token（如果有）
        // 注意：这里无法直接访问localStorage，需要前端传递token
        // 暂时简单返回成功
        return { success: true, message: '已退出登录' };
    } catch (error) {
        console.error('❌ 退出失败:', error);
        return { success: false, message: error.message };
    }
});

/**
 * 发送验证码
 */
ipcMain.handle('send-verification-code', async (event, { contactType, contactValue, codeType }) => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/verification/send-code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contact_type: contactType,
                contact_value: contactValue,
                code_type: codeType
            })
        });
        const data = await response.json();
        console.log('✅ 验证码发送结果:', data);
        return { success: true, data };
    } catch (error) {
        console.error('❌ 发送验证码失败:', error);
        return { success: false, message: error.message };
    }
});

/**
 * 带验证码注册
 */
ipcMain.handle('register-with-verification', async (event, data) => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/register-with-verification`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        console.log('✅ 注册结果:', result);
        return { success: true, data: result };
    } catch (error) {
        console.error('❌ 注册失败:', error);
        return { success: false, message: error.message };
    }
});

/**
 * 重置密码
 */
ipcMain.handle('reset-password', async (event, data) => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        console.log('✅ 密码重置结果:', result);
        return { success: true, data: result };
    } catch (error) {
        console.error('❌ 密码重置失败:', error);
        return { success: false, message: error.message };
    }
});

console.log('AI个人助理启动中...');
console.log('服务器地址:', CLOUD_SERVER_URL);
console.log('API基础URL:', API_BASE_URL);
