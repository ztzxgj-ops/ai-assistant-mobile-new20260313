import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
from datetime import datetime, timedelta

class AdvancedStockAnalyzer:
    def __init__(self, ticker):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.data = None
        self.info = None
        self.score = 0
        self.analysis_log = []

    def fetch_data(self, period="1y"):
        """获取历史数据和基本面数据"""
        print(f"正在获取 {self.ticker} 的数据...")
        try:
            # 获取历史K线
            self.data = self.stock.history(period=period)
            if self.data.empty:
                raise ValueError("未找到数据")
            
            # 获取基本面信息
            self.info = self.stock.info
        except Exception as e:
            print(f"获取数据失败: {e}")
            sys.exit(1)

    def calculate_technicals(self):
        """计算核心技术指标"""
        df = self.data
        
        # 1. 移动平均线 (Trend)
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        # 2. RSI (Momentum)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 3. MACD (Trend Reversal)
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # 4. 布林带 (Volatility)
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        df['BB_Std'] = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (2 * df['BB_Std'])
        df['BB_Lower'] = df['BB_Middle'] - (2 * df['BB_Std'])

        # 5. ATR (Risk Management)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['ATR'] = true_range.rolling(14).mean()

        self.data = df

    def evaluate_score(self):
        """根据多因子模型计算综合得分 (0-100)"""
        current_price = self.data['Close'].iloc[-1]
        rsi = self.data['RSI'].iloc[-1]
        macd = self.data['MACD'].iloc[-1]
        signal = self.data['Signal_Line'].iloc[-1]
        sma50 = self.data['SMA_50'].iloc[-1]
        sma200 = self.data['SMA_200'].iloc[-1]
        
        score = 50 # 初始中性分
        reasons = []

        # --- 技术面评分 ---
        
        # 趋势判断 (权重: 20分)
        if current_price > sma50:
            score += 10
            reasons.append("[趋势] 股价位于50日均线上方 (中期看涨)")
        else:
            score -= 10
            reasons.append("[趋势] 股价位于50日均线下方 (中期看跌)")
            
        if sma50 > sma200:
            score += 5
            reasons.append("[趋势] 50日线 > 200日线 (金叉/多头排列)")
        
        # RSI 动量 (权重: 15分)
        if rsi < 30:
            score += 15
            reasons.append("[动量] RSI超卖 (<30)，存在反弹可能")
        elif rsi > 70:
            score -= 15
            reasons.append("[动量] RSI超买 (>70)，回调风险大")
        else:
            reasons.append(f"[动量] RSI中性 ({rsi:.2f})")

        # MACD 信号 (权重: 15分)
        if macd > signal:
            score += 10
            reasons.append("[信号] MACD在信号线上方 (买入动能)")
        else:
            score -= 10
            reasons.append("[信号] MACD在信号线下方 (卖出压力)")

        # --- 基本面评分 (如果可用) ---
        try:
            pe_ratio = self.info.get('trailingPE', None)
            peg_ratio = self.info.get('pegRatio', None)
            beta = self.info.get('beta', None)
            
            # PEG (成长价值比) - 权重 20分
            if peg_ratio:
                if peg_ratio < 1.0:
                    score += 15
                    reasons.append(f"[估值] PEG ({peg_ratio}) 低于1.0，价值被低估")
                elif peg_ratio > 2.0:
                    score -= 10
                    reasons.append(f"[估值] PEG ({peg_ratio}) 过高，可能透支未来")
                else:
                    score += 5
                    reasons.append(f"[估值] PEG ({peg_ratio}) 估值合理")
            
            # Beta (波动性风险)
            if beta:
                if beta < 1.0:
                    reasons.append(f"[风险] Beta ({beta}) 小于1，波动性低于大盘 (防御性)")
                else:
                    reasons.append(f"[风险] Beta ({beta}) 大于1，波动性高于大盘 (进攻性)")

        except:
            reasons.append("[警告] 无法获取完整基本面数据，仅基于技术面评分")

        self.score = max(0, min(100, score)) # 限制在 0-100
        self.analysis_log = reasons

    def generate_report(self):
        """生成并打印分析报告"""
        last_date = self.data.index[-1].strftime('%Y-%m-%d')
        current_close = self.data['Close'].iloc[-1]
        atr = self.data['ATR'].iloc[-1]
        
        stop_loss = current_close - (2 * atr) # 2倍ATR止损法
        
        print("\n" + "="*50)
        print(f"股票代码: {self.ticker} | 分析日期: {last_date}")
        print(f"当前价格: {current_close:.2f}")
        print("="*50)
        
        print(f"\n【AI综合评分】: {self.score}/100")
        if self.score >= 80:
            print(">> 评级: 强力买入 (Strong Buy)")
        elif self.score >= 60:
            print(">> 评级: 谨慎买入 (Buy)")
        elif self.score >= 40:
            print(">> 评级: 持有/观望 (Hold)")
        else:
            print(">> 评级: 卖出/规避 (Sell)")
            
        print("\n【分析逻辑】:")
        for log in self.analysis_log:
            print(f" - {log}")
            
        print(f"\n【交易建议 (仅供参考)】:")
        print(f" - 建议止损位 (2xATR): {stop_loss:.2f}")
        print(f" - 短期支撑位 (布林下轨): {self.data['BB_Lower'].iloc[-1]:.2f}")
        print(f" - 短期阻力位 (布林上轨): {self.data['BB_Upper'].iloc[-1]:.2f}")
        print("="*50 + "\n")

    def plot_chart(self):
        """绘制可视化图表"""
        plt.style.use('bmh') # 使用一种好看的样式
        
        # 创建两个子图：上图是K线和均线，下图是RSI
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
        
        # 主图
        df_plot = self.data.iloc[-100:] # 只画最近100天
        ax1.plot(df_plot.index, df_plot['Close'], label='Close Price', linewidth=2, color='black')
        ax1.plot(df_plot.index, df_plot['SMA_20'], label='SMA 20', linestyle='--', alpha=0.7)
        ax1.plot(df_plot.index, df_plot['SMA_50'], label='SMA 50', linestyle='--', alpha=0.7)
        ax1.plot(df_plot.index, df_plot['BB_Upper'], label='BB Upper', color='green', alpha=0.3)
        ax1.plot(df_plot.index, df_plot['BB_Lower'], label='BB Lower', color='red', alpha=0.3)
        ax1.fill_between(df_plot.index, df_plot['BB_Upper'], df_plot['BB_Lower'], color='gray', alpha=0.1)
        
        ax1.set_title(f"{self.ticker} Price Trend & Volatility")
        ax1.legend(loc='upper left')
        ax1.grid(True)
        
        # RSI 子图
        ax2.plot(df_plot.index, df_plot['RSI'], color='purple', label='RSI')
        ax2.axhline(70, linestyle='--', alpha=0.5, color='red')
        ax2.axhline(30, linestyle='--', alpha=0.5, color='green')
        ax2.fill_between(df_plot.index, df_plot['RSI'], 70, where=(df_plot['RSI']>=70), color='red', alpha=0.3)
        ax2.fill_between(df_plot.index, df_plot['RSI'], 30, where=(df_plot['RSI']<=30), color='green', alpha=0.3)
        ax2.set_title("RSI Momentum")
        ax2.set_ylim(0, 100)
        ax2.grid(True)
        
        plt.tight_layout()
        filename = f"{self.ticker}_analysis.png"
        plt.savefig(filename)
        print(f"图表已保存为: {filename}")
        # plt.show() # 如果在服务器环境，通常不需要直接show

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python3 stock_analysis_tool.py <股票代码>")
        print("示例: python3 stock_analysis_tool.py AAPL")
        print("示例 (A股需加后缀): python3 stock_analysis_tool.py 600519.SS")
    else:
        ticker_symbol = sys.argv[1]
        analyzer = AdvancedStockAnalyzer(ticker_symbol)
        analyzer.fetch_data()
        analyzer.calculate_technicals()
        analyzer.evaluate_score()
        analyzer.generate_report()
        analyzer.plot_chart()
