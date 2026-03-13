import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = 'http://47.109.148.176/ai';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (token) {
      setIsLoggedIn(true);
      fetchUserProfile();
      fetchMessages();
    }
  }, [token]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const response = await axios.post(`${API_BASE_URL}/api/auth/login`, {
        username,
        password
      });
      const newToken = response.data.token;
      setToken(newToken);
      localStorage.setItem('token', newToken);
      setIsLoggedIn(true);
      setUsername('');
      setPassword('');
    } catch (error) {
      alert('登录失败: ' + (error.response?.data?.message || error.message));
    } finally {
      setLoading(false);
    }
  };

  const fetchUserProfile = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/user/profile`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUserInfo(response.data);
    } catch (error) {
      console.error('获取用户信息失败:', error);
    }
  };

  const fetchMessages = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/chats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMessages(response.data.messages || []);
    } catch (error) {
      console.error('获取消息失败:', error);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const userMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString()
    };

    setMessages([...messages, userMessage]);
    setInputValue('');
    setLoading(true);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/ai/chat`,
        { message: inputValue },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: '抱歉，发生错误: ' + (error.response?.data?.message || error.message),
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setToken('');
    setIsLoggedIn(false);
    setMessages([]);
    setUserInfo(null);
    localStorage.removeItem('token');
  };

  if (!isLoggedIn) {
    return (
      <div className="login-container">
        <div className="login-box">
          <h1>AI 助手</h1>
          <form onSubmit={handleLogin}>
            <input
              type="text"
              placeholder="用户名"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
            />
            <input
              type="password"
              placeholder="密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
            />
            <button type="submit" disabled={loading}>
              {loading ? '登录中...' : '登录'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <div className="header">
        <div className="header-left">
          <h1>AI 助手</h1>
          {userInfo && <span className="username">用户: {userInfo.username}</span>}
        </div>
        <button className="logout-btn" onClick={handleLogout}>
          退出登录
        </button>
      </div>

      <div className="chat-container">
        <div className="messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="message-content">{msg.content}</div>
              <div className="message-time">
                {new Date(msg.timestamp).toLocaleTimeString('zh-CN')}
              </div>
            </div>
          ))}
          {loading && <div className="message assistant loading">思考中...</div>}
          <div ref={messagesEndRef} />
        </div>

        <form className="input-form" onSubmit={handleSendMessage}>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="输入消息..."
            disabled={loading}
          />
          <button type="submit" disabled={loading || !inputValue.trim()}>
            发送
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
