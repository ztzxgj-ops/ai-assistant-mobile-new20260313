/**
 * Preload Script
 * 在渲染进程和主进程之间建立安全的通信桥梁
 */

const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
    // 获取应用信息
    getAppInfo: () => ipcRenderer.sendSync('app-info'),

    // 显示系统通知
    showNotification: (title, body, silent = false) => {
        ipcRenderer.send('show-notification', { title, body, silent });
    },

    // 播放提示音
    playSound: (soundName = 'Glass') => {
        ipcRenderer.send('play-sound', soundName);
    },

    // 监听通知显示结果
    onNotificationShown: (callback) => {
        ipcRenderer.on('notification-shown', (event, result) => callback(result));
    },

    // 监听声音播放结果
    onSoundPlayed: (callback) => {
        ipcRenderer.on('sound-played', (event, result) => callback(result));
    },

    // ========================================
    // 用户认证相关API
    // ========================================

    // 用户登录
    login: (username, password) =>
        ipcRenderer.invoke('user-login', { username, password }),

    // 用户注册（旧版，兼容保留）
    register: (username, password, phone) =>
        ipcRenderer.invoke('user-register', { username, password, phone }),

    // 用户退出
    logout: () =>
        ipcRenderer.invoke('user-logout'),

    // ========================================
    // 验证码相关API（新增）
    // ========================================

    // 发送验证码
    sendVerificationCode: (contactType, contactValue, codeType) =>
        ipcRenderer.invoke('send-verification-code', { contactType, contactValue, codeType }),

    // 带验证码注册
    registerWithVerification: (data) =>
        ipcRenderer.invoke('register-with-verification', data),

    // 重置密码
    resetPassword: (data) =>
        ipcRenderer.invoke('reset-password', data),

    // 可以在这里添加更多需要的API
    platform: process.platform,
    version: process.versions.electron
});

console.log('Preload script loaded - All APIs ready (包括验证码功能)');
