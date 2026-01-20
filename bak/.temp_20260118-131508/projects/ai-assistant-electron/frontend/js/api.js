/**
 * API封装 - 通过Electron IPC与Python后端通信
 *
 * 所有API调用都通过window.electronAPI进行
 * electronAPI在preload.js中通过contextBridge暴露
 */

// API调用都已在preload.js中定义
// 这个文件仅用于扩展辅助函数或全局状态管理

// 全局状态
const AppState = {
    user: null,
    token: null
};

// 初始化
function initApp() {
    const token = localStorage.getItem('token');
    const username = localStorage.getItem('username');
    const user_id = localStorage.getItem('user_id');

    if (token && username) {
        AppState.token = token;
        AppState.user = {
            id: user_id,
            username: username
        };
    }
}

// 检查是否已登录
function isAuthenticated() {
    return !!AppState.token;
}

// 获取当前用户
function getCurrentUser() {
    return AppState.user;
}

// 退出登录
async function logoutUser() {
    if (AppState.token && window.electronAPI) {
        try {
            await window.electronAPI.logout();
        } catch (error) {
            console.error('退出登录失败:', error);
        }
    }

    AppState.token = null;
    AppState.user = null;
    localStorage.clear();
    window.location.href = 'login.html';
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});
