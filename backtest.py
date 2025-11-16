#!/usr/bin/env python3
"""
Backtest the BTC Scalping Strategy on Historical Data
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import json

class ScalpingBacktest:
    def __init__(self, initial_balance=10000, position_size_pct=0.10):
        self.exchange = ccxt.binance({'enableRateLimit': True})
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position_size_pct = position_size_pct
        
        self.min_body_ratio = 0.6
        self.lookback = 20
        
        self.trades = []
        self.position = None
        
    def fetch_historical_data(self, symbol='BTC/USDT', timeframe='5m', days=7):
        """Fetch historical OHLCV data"""
        print(f"Fetching {days} days of {timeframe} data for {symbol}...")
        
        since = self.exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
        all_candles = []
        
        while True:
            candles = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not candles:
                break
            all_candles.extend(candles)
            since = candles[-1][0] + 1
            
            # Break if we've caught up to now
            if candles[-1][0] >= self.exchange.milliseconds():
                break
        
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        print(f"Fetched {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
        return df
    
    def is_full_bodied_candle(self, row):
        """Check if candle is full-bodied"""
        body = abs(row['close'] - row['open'])
        total_range = row['high'] - row['low']
        
        if total_range == 0:
            return False, False, 0
        
        body_ratio = body / total_range
        is_bullish = (row['close'] > row['open']) and (body_ratio >= self.min_body_ratio)
        is_bearish = (row['close'] < row['open']) and (body_ratio >= self.min_body_ratio)
        
        return is_bullish, is_bearish, body_ratio
    
    def find_zones(self, df, idx):
        """Find supply/demand zones up to current index"""
        start_idx = max(0, idx - self.lookback)
        window = df.iloc[start_idx:idx]
        
        if len(window) < 3:
            return None
        
        # Find swing lows
        lows = window[window['low'] == window['low'].rolling(3, center=True).min()]['low']
        previous_low = lows.iloc[-2] if len(lows) >= 2 else window['low'].min()
        
        # Find swing highs
        highs = window[window['high'] == window['high'].rolling(3, center=True).max()]['high']
        previous_high = highs.iloc[-2] if len(highs) >= 2 else window['high'].max()
        
        return {
            'previous_low': previous_low,
            'previous_high': previous_high
        }
    
    def check_sell_setup(self, df, idx, zones):
        """Check for sell setup at given index"""
        if idx < 1:
            return False, None
        
        current = df.iloc[idx]
        previous_low = zones['previous_low']
        
        # Check if closed below previous low
        if current['close'] >= previous_low:
            return False, None
        
        # Check if full-bodied bearish
        is_bullish, is_bearish, body_ratio = self.is_full_bodied_candle(current)
        if not is_bearish:
            return False, None
        
        # Calculate levels
        stop_loss = max(current['high'], previous_low) * 1.001
        risk = stop_loss - current['close']
        take_profit = current['close'] - risk
        
        return True, {
            'type': 'SELL',
            'entry': current['close'],
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': current['timestamp'],
            'body_ratio': body_ratio
        }
    
    def check_buy_setup(self, df, idx, zones):
        """Check for buy setup at given index"""
        if idx < 1:
            return False, None
        
        current = df.iloc[idx]
        previous_high = zones['previous_high']
        
        # Check if closed above previous high
        if current['close'] <= previous_high:
            return False, None
        
        # Check if full-bodied bullish
        is_bullish, is_bearish, body_ratio = self.is_full_bodied_candle(current)
        if not is_bullish:
            return False, None
        
        # Calculate levels
        stop_loss = min(current['low'], previous_high) * 0.999
        risk = current['close'] - stop_loss
        take_profit = current['close'] + risk
        
        return True, {
            'type': 'BUY',
            'entry': current['close'],
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': current['timestamp'],
            'body_ratio': body_ratio
        }
    
    def open_position(self, setup):
        """Open a position"""
        risk_amount = self.balance * self.position_size_pct
        
        if setup['type'] == 'SELL':
            risk_per_unit = setup['stop_loss'] - setup['entry']
        else:
            risk_per_unit = setup['entry'] - setup['stop_loss']
        
        position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
        
        self.position = {
            'type': setup['type'],
            'entry': setup['entry'],
            'stop_loss': setup['stop_loss'],
            'take_profit': setup['take_profit'],
            'size': position_size,
            'entry_time': setup['timestamp']
        }
    
    def check_exit(self, current_row):
        """Check if position should exit"""
        if not self.position:
            return False, None, None
        
        current_price = current_row['close']
        high = current_row['high']
        low = current_row['low']
        
        if self.position['type'] == 'SELL':
            # Check stop loss
            if high >= self.position['stop_loss']:
                return True, self.position['stop_loss'], 'Stop Loss'
            
            # Check take profit
            if low <= self.position['take_profit']:
                return True, self.position['take_profit'], 'Take Profit'
            
            # Check return to entry
            if high >= self.position['entry']:
                return True, self.position['entry'], 'Return to Entry'
        
        else:  # BUY
            # Check stop loss
            if low <= self.position['stop_loss']:
                return True, self.position['stop_loss'], 'Stop Loss'
            
            # Check take profit
            if high >= self.position['take_profit']:
                return True, self.position['take_profit'], 'Take Profit'
            
            # Check return to entry
            if low <= self.position['entry']:
                return True, self.position['entry'], 'Return to Entry'
        
        return False, None, None
    
    def close_position(self, exit_price, reason, exit_time):
        """Close position and record trade"""
        if self.position['type'] == 'SELL':
            pnl = (self.position['entry'] - exit_price) * self.position['size']
        else:
            pnl = (exit_price - self.position['entry']) * self.position['size']
        
        self.balance += pnl
        
        trade = {
            'entry_time': str(self.position['entry_time']),
            'exit_time': str(exit_time),
            'type': self.position['type'],
            'entry': self.position['entry'],
            'exit': exit_price,
            'stop_loss': self.position['stop_loss'],
            'take_profit': self.position['take_profit'],
            'pnl': pnl,
            'pnl_pct': (pnl / self.balance) * 100,
            'reason': reason,
            'balance': self.balance
        }
        
        self.trades.append(trade)
        self.position = None
    
    def run_backtest(self, df):
        """Run backtest on historical data"""
        print(f"\n{'='*60}")
        print(f"🔬 STARTING BACKTEST")
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"{'='*60}\n")
        
        for idx in range(self.lookback, len(df)):
            current_row = df.iloc[idx]
            
            # Check if we should exit existing position
            if self.position:
                should_exit, exit_price, reason = self.check_exit(current_row)
                if should_exit:
                    self.close_position(exit_price, reason, current_row['timestamp'])
                    print(f"[{current_row['timestamp']}] Closed {self.position['type'] if self.position else 'position'}: {reason} | P&L: ${self.trades[-1]['pnl']:.2f} | Balance: ${self.balance:,.2f}")
            
            # Look for new setup if no position
            if not self.position:
                zones = self.find_zones(df, idx)
                if zones:
                    # Check sell
                    sell_signal, sell_setup = self.check_sell_setup(df, idx, zones)
                    if sell_signal:
                        self.open_position(sell_setup)
                        print(f"[{current_row['timestamp']}] Opened SELL @ ${sell_setup['entry']:.2f}")
                        continue
                    
                    # Check buy
                    buy_signal, buy_setup = self.check_buy_setup(df, idx, zones)
                    if buy_signal:
                        self.open_position(buy_setup)
                        print(f"[{current_row['timestamp']}] Opened BUY @ ${buy_setup['entry']:.2f}")
        
        # Close any remaining position at last price
        if self.position:
            last_row = df.iloc[-1]
            self.close_position(last_row['close'], 'Backtest End', last_row['timestamp'])
        
        self.print_results()
    
    def print_results(self):
        """Print backtest results"""
        print(f"\n{'='*60}")
        print(f"📊 BACKTEST RESULTS")
        print(f"{'='*60}")
        
        if not self.trades:
            print("No trades executed during backtest period")
            return
        
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]
        
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = self.balance - self.initial_balance
        roi = (total_pnl / self.initial_balance) * 100
        
        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Final Balance: ${self.balance:,.2f}")
        print(f"Total P&L: ${total_pnl:,.2f}")
        print(f"ROI: {roi:.2f}%")
        print(f"\nTotal Trades: {total_trades}")
        print(f"Winning Trades: {len(winning_trades)} ({win_rate:.1f}%)")
        print(f"Losing Trades: {len(losing_trades)} ({100-win_rate:.1f}%)")
        print(f"\nAverage Win: ${avg_win:.2f}")
        print(f"Average Loss: ${avg_loss:.2f}")
        
        if avg_loss != 0:
            profit_factor = abs(avg_win / avg_loss)
            print(f"Profit Factor: {profit_factor:.2f}")
        
        # Exit reasons breakdown
        exit_reasons = {}
        for trade in self.trades:
            reason = trade['reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        print(f"\nExit Reasons:")
        for reason, count in exit_reasons.items():
            print(f"  {reason}: {count} ({(count/total_trades)*100:.1f}%)")
        
        print(f"{'='*60}\n")
        
        # Save results
        results = {
            'summary': {
                'initial_balance': self.initial_balance,
                'final_balance': self.balance,
                'total_pnl': total_pnl,
                'roi': roi,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss
            },
            'trades': self.trades
        }
        
        with open('/mnt/user-data/outputs/backtest_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print("✅ Results saved to /mnt/user-data/outputs/backtest_results.json")


if __name__ == "__main__":
    # Run backtest
    backtest = ScalpingBacktest(initial_balance=10000, position_size_pct=0.10)
    
    # Fetch 7 days of 5-minute data
    df = backtest.fetch_historical_data(symbol='BTC/USDT', timeframe='5m', days=7)
    
    # Run the backtest
    backtest.run_backtest(df)
