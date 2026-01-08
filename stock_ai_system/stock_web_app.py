import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 配置页面
st.set_page_config(
    page_title="AI 智能股票分析系统",
    page_icon="📈",
    layout="wide"
)

# --- 核心分析逻辑 (复用并优化自 CLI 版本) ---
class AdvancedStockAnalyzer:
    def __init__(self, ticker):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.data = None
        self.info = None
        self.score = 0
        self.analysis_log = []

    def fetch_data(self, period="1y"):
        try:
            self.data = self.stock.history(period=period)
            if self.data.empty:
                return False
            self.info = self.stock.info
            return True
        except Exception as e:
            st.error(f"获取数据失败: {e}")
            return False

    def calculate_technicals(self):
        df = self.data
        # 移动平均线
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # 布林带
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        df['BB_Std'] = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (2 * df['BB_Std'])
        df['BB_Lower'] = df['BB_Middle'] - (2 * df['BB_Std'])

        # ATR
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['ATR'] = true_range.rolling(14).mean()

        self.data = df

    def evaluate_score(self):
        current_price = self.data['Close'].iloc[-1]
        rsi = self.data['RSI'].iloc[-1]
        macd = self.data['MACD'].iloc[-1]
        signal = self.data['Signal_Line'].iloc[-1]
        sma50 = self.data['SMA_50'].iloc[-1]
        sma200 = self.data['SMA_200'].iloc[-1]
        
        score = 50 
        reasons = []

        # 趋势
        if current_price > sma50:
            score += 10
            reasons.append("✅ 股价 > 50日均线 (中期看涨)")
        else:
            score -= 10
            reasons.append("🔻 股价 < 50日均线 (中期看跌)")
            
        if sma50 > sma200:
            score += 5
            reasons.append("✅ 50日线 > 200日线 (金叉/多头)")
        
        # 动量
        if rsi < 30:
            score += 15
            reasons.append("🚀 RSI超卖 (<30)，存在反弹可能")
        elif rsi > 70:
            score -= 15
            reasons.append("⚠️ RSI超买 (>70)，回调风险大")
        else:
            reasons.append(f"⚖️ RSI中性 ({rsi:.2f})")

        # 信号
        if macd > signal:
            score += 10
            reasons.append("✅ MACD在信号线上方 (买入动能)")
        else:
            score -= 10
            reasons.append("🔻 MACD在信号线下方 (卖出压力)")

        # 估值 (基本面)
        try:
            peg_ratio = self.info.get('pegRatio', None)
            if peg_ratio:
                if peg_ratio < 1.0:
                    score += 15
                    reasons.append(f"💎 PEG ({peg_ratio}) 低于1.0，价值低估")
                elif peg_ratio > 2.0:
                    score -= 10
                    reasons.append(f"☁️ PEG ({peg_ratio}) 过高，可能高估")
                else:
                    score += 5
                    reasons.append(f"⚖️ PEG ({peg_ratio}) 估值合理")
        except:
            reasons.append("⚠️ 无法获取完整估值数据")

        self.score = max(0, min(100, score))
        self.analysis_log = reasons

    def get_plot_figure(self):
        plt.style.use('bmh')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), gridspec_kw={'height_ratios': [3, 1]})
        
        df_plot = self.data.iloc[-120:] # 最近120天
        
        # 主图
        ax1.plot(df_plot.index, df_plot['Close'], label='Price', color='black', alpha=0.8)
        ax1.plot(df_plot.index, df_plot['SMA_20'], label='SMA 20', linestyle='--', color='blue', alpha=0.5)
        ax1.plot(df_plot.index, df_plot['SMA_50'], label='SMA 50', linestyle='--', color='orange', alpha=0.5)
        ax1.fill_between(df_plot.index, df_plot['BB_Upper'], df_plot['BB_Lower'], color='gray', alpha=0.1)
        ax1.set_title(f"{self.ticker} Price Trend")
        ax1.legend(loc='upper left')
        
        # 副图 RSI
        ax2.plot(df_plot.index, df_plot['RSI'], color='purple', label='RSI')
        ax2.axhline(70, linestyle='--', color='red', alpha=0.5)
        ax2.axhline(30, linestyle='--', color='green', alpha=0.5)
        ax2.set_title("RSI")
        ax2.set_ylim(0, 100)
        
        plt.tight_layout()
        return fig

# --- 网页界面 ---

st.title("📈 AI 智能股票分析系统")
st.markdown("基于 **多因子量化模型 (Multi-Factor Model)**，结合技术面与基本面进行实时诊断。")

# 侧边栏：输入控制
with st.sidebar:
    st.header("📊 参数设置")
    ticker_input = st.text_input("股票代码 (Ticker)", value="AAPL", help="美股直接输入代码，A股加后缀 .SS (沪) 或 .SZ (深)，港股 .HK").upper()
    period = st.selectbox("分析周期", ["6mo", "1y", "2y", "5y"], index=1)
    
    st.info("""
    **代码示例：**
    *   美股: `AAPL`, `TSLA`, `NVDA`
    *   A股: `600519.SS` (茅台)
    *   港股: `0700.HK` (腾讯)
    """)
    
    run_btn = st.button("🚀 开始分析", type="primary")

# 主区域逻辑
if run_btn:
    with st.spinner(f'正在深入分析 {ticker_input} ...'):
        analyzer = AdvancedStockAnalyzer(ticker_input)
        success = analyzer.fetch_data(period=period)
        
        if success:
            analyzer.calculate_technicals()
            analyzer.evaluate_score()
            
            # 1. 顶部关键指标栏
            current_price = analyzer.data['Close'].iloc[-1]
            prev_price = analyzer.data['Close'].iloc[-2]
            change = current_price - prev_price
            change_pct = (change / prev_price) * 100
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("当前价格", f"${current_price:.2f}", f"{change:.2f} ({change_pct:.2f}%)")
            
            # 根据分数显示颜色
            score = analyzer.score
            if score >= 80:
                score_color = "normal" # Streamlit metric doesn't support color directly, handled logic below
                rec = "强力买入 (Strong Buy)"
            elif score >= 60:
                rec = "买入 (Buy)"
            elif score >= 40:
                rec = "观望 (Hold)"
            else:
                rec = "卖出 (Sell)"
            
            col2.metric("AI 综合评分", f"{score}/100", delta=score-50, delta_color="normal")
            col3.metric("评级建议", rec)
            
            atr = analyzer.data['ATR'].iloc[-1]
            stop_loss = current_price - 2 * atr
            col4.metric("建议止损位", f"${stop_loss:.2f}", "-2x ATR")

            # 2. 图表区域
            st.divider()
            st.subheader("📉 趋势与动量分析")
            fig = analyzer.get_plot_figure()
            st.pyplot(fig)

            # 3. 详细逻辑分析
            st.divider()
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("🧠 AI 分析逻辑")
                for log in analyzer.analysis_log:
                    st.write(log)
                    
            with c2:
                st.subheader("📋 关键数据概览")
                info = analyzer.info
                # 提取一些关键的基本面数据展示
                fund_data = {
                    "市盈率 (PE)": info.get('trailingPE', 'N/A'),
                    "远期市盈率 (Forward PE)": info.get('forwardPE', 'N/A'),
                    "市值 (Market Cap)": info.get('marketCap', 'N/A'),
                    "52周最高": info.get('fiftyTwoWeekHigh', 'N/A'),
                    "52周最低": info.get('fiftyTwoWeekLow', 'N/A'),
                    "Beta (波动率)": info.get('beta', 'N/A')
                }
                st.dataframe(pd.DataFrame([fund_data]).T.rename(columns={0: '数值'}))

        else:
            st.error(f"无法获取股票 {ticker_input} 的数据，请检查代码是否正确。")
else:
    st.write("👈 请在左侧输入股票代码并点击“开始分析”")
