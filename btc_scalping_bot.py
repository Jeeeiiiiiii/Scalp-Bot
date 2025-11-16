#!/usr/bin/env python3
"""
BTC Scalping Bot - Paper Trading
Based on supply/demand zone strategy with full-bodied candle confirmation
"""

import ccxt
import pandas as pd
import time
from datetime import datetime
import json
import os

class ScalpingBot:
    def __init__(self, symbol='BTC/USDT', timeframe='5m', paper_trading=True):
        """
        Initialize the scalping bot
        
        Args:
            symbol: Trading pair (default: BTC/USDT)
            timeframe: Candle timeframe (default: 5m)
            paper_trading: Enable paper trading mode (default: True)
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.paper_trading = paper_trading
        
        # Initialize exchange (using Binance)
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
        })
        
        # Trading parameters
        self.position = None
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.position_size = 0
        
        # Paper trading balance
        self.paper_balance = 10000  # Starting with $10,000
        self.paper_btc_balance = 0
        self.trades_history = []
        
        # Strategy parameters
        self.lookback_candles = 20  # Look back for supply/demand zones
        self.min_body_ratio = 0.6  # Minimum body-to-wick ratio for "full-bodied" candle
        
        # Log file
        self.log_file = '/mnt/user-data/outputs/scalping_bot_log.json'
        
    def get_candles(self, limit=100):
        """Fetch OHLCV candles from exchange"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"Error fetching candles: {e}")
            return None
    
    def is_full_bodied_candle(self, candle):
        """
        Check if candle is full-bodied (strong directional movement)
        
        Args:
            candle: Series containing open, high, low, close
            
        Returns:
            tuple: (is_bullish, is_bearish, body_ratio)
        """
        body = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']
        
        if total_range == 0:
            return False, False, 0
        
        body_ratio = body / total_range
        
        is_bullish = (candle['close'] > candle['open']) and (body_ratio >= self.min_body_ratio)
        is_bearish = (candle['close'] < candle['open']) and (body_ratio >= self.min_body_ratio)
        
        return is_bullish, is_bearish, body_ratio
    
    def find_supply_demand_zones(self, df):
        """
        Find supply (resistance) and demand (support) zones
        
        Returns:
            dict: {'supply': price, 'demand': price}
        """
        # Get recent highs and lows
        recent_data = df.tail(self.lookback_candles)
        
        # Find swing highs (supply zones)
        supply_zone = recent_data['high'].max()
        
        # Find swing lows (demand zones)
        demand_zone = recent_data['low'].min()
        
        # Find most recent significant low for sell setup
        recent_lows = recent_data[recent_data['low'] == recent_data['low'].rolling(3, center=True).min()]['low']
        previous_low = recent_lows.iloc[-2] if len(recent_lows) >= 2 else demand_zone
        
        # Find most recent significant high for buy setup
        recent_highs = recent_data[recent_data['high'] == recent_data['high'].rolling(3, center=True).max()]['high']
        previous_high = recent_highs.iloc[-2] if len(recent_highs) >= 2 else supply_zone
        
        return {
            'supply': supply_zone,
            'demand': demand_zone,
            'previous_low': previous_low,
            'previous_high': previous_high
        }
    
    def check_sell_setup(self, df, zones):
        """
        Check for sell setup:
        - Price approaching supply/previous low
        - Full-bodied bearish candle closes below previous low
        """
        if len(df) < 2:
            return False, None
        
        current_candle = df.iloc[-1]
        previous_candle = df.iloc[-2]
        previous_low = zones['previous_low']
        
        # Check if current candle closed below previous low
        candle_closed_below = current_candle['close'] < previous_low
        
        # Check if it's a full-bodied bearish candle
        is_bullish, is_bearish, body_ratio = self.is_full_bodied_candle(current_candle)
        
        if candle_closed_below and is_bearish:
            # Calculate stop loss (above the supply zone/previous high of the candle)
            stop_loss = max(current_candle['high'], previous_low) * 1.001  # Add 0.1% buffer
            
            # Calculate take profit (1:1 risk-reward)
            risk = stop_loss - current_candle['close']
            take_profit = current_candle['close'] - risk
            
            setup = {
                'type': 'SELL',
                'entry': current_candle['close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'body_ratio': body_ratio,
                'timestamp': current_candle['timestamp']
            }
            
            return True, setup
        
        return False, None
    
    def check_buy_setup(self, df, zones):
        """
        Check for buy setup:
        - Price approaching demand/previous high
        - Full-bodied bullish candle closes above previous high
        """
        if len(df) < 2:
            return False, None
        
        current_candle = df.iloc[-1]
        previous_candle = df.iloc[-2]
        previous_high = zones['previous_high']
        
        # Check if current candle closed above previous high
        candle_closed_above = current_candle['close'] > previous_high
        
        # Check if it's a full-bodied bullish candle
        is_bullish, is_bearish, body_ratio = self.is_full_bodied_candle(current_candle)
        
        if candle_closed_above and is_bullish:
            # Calculate stop loss (below the demand zone/previous low of the candle)
            stop_loss = min(current_candle['low'], previous_high) * 0.999  # Subtract 0.1% buffer
            
            # Calculate take profit (1:1 risk-reward)
            risk = current_candle['close'] - stop_loss
            take_profit = current_candle['close'] + risk
            
            setup = {
                'type': 'BUY',
                'entry': current_candle['close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'body_ratio': body_ratio,
                'timestamp': current_candle['timestamp']
            }
            
            return True, setup
        
        return False, None
    
    def open_position(self, setup):
        """Open a new position (paper trading)"""
        if self.paper_trading:
            # Calculate position size (use 10% of balance per trade)
            risk_amount = self.paper_balance * 0.10
            
            if setup['type'] == 'SELL':
                # For sells, we're shorting - calculate based on risk
                risk_per_unit = setup['stop_loss'] - setup['entry']
                position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
            else:  # BUY
                risk_per_unit = setup['entry'] - setup['stop_loss']
                position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
            
            self.position = setup['type']
            self.entry_price = setup['entry']
            self.stop_loss = setup['stop_loss']
            self.take_profit = setup['take_profit']
            self.position_size = position_size
            
            log_entry = {
                'timestamp': str(datetime.now()),
                'action': 'OPEN_POSITION',
                'type': setup['type'],
                'entry': setup['entry'],
                'stop_loss': setup['stop_loss'],
                'take_profit': setup['take_profit'],
                'position_size': position_size,
                'body_ratio': setup['body_ratio']
            }
            
            self.trades_history.append(log_entry)
            print(f"\n{'='*60}")
            print(f"🚀 POSITION OPENED: {setup['type']}")
            print(f"Entry: ${setup['entry']:.2f}")
            print(f"Stop Loss: ${setup['stop_loss']:.2f}")
            print(f"Take Profit: ${setup['take_profit']:.2f}")
            print(f"Position Size: {position_size:.6f} BTC")
            print(f"Body Ratio: {setup['body_ratio']:.2%}")
            print(f"{'='*60}\n")
    
    def close_position(self, current_price, reason):
        """Close current position (paper trading)"""
        if not self.position:
            return
        
        # Calculate P&L
        if self.position == 'SELL':
            pnl = (self.entry_price - current_price) * self.position_size
        else:  # BUY
            pnl = (current_price - self.entry_price) * self.position_size
        
        self.paper_balance += pnl
        
        log_entry = {
            'timestamp': str(datetime.now()),
            'action': 'CLOSE_POSITION',
            'type': self.position,
            'entry': self.entry_price,
            'exit': current_price,
            'pnl': pnl,
            'reason': reason,
            'balance': self.paper_balance
        }
        
        self.trades_history.append(log_entry)
        
        print(f"\n{'='*60}")
        print(f"🔴 POSITION CLOSED: {self.position}")
        print(f"Entry: ${self.entry_price:.2f}")
        print(f"Exit: ${current_price:.2f}")
        print(f"P&L: ${pnl:.2f} ({(pnl/self.paper_balance)*100:.2f}%)")
        print(f"Reason: {reason}")
        print(f"New Balance: ${self.paper_balance:.2f}")
        print(f"{'='*60}\n")
        
        # Reset position
        self.position = None
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.position_size = 0
    
    def check_exit_conditions(self, current_price):
        """Check if position should be closed"""
        if not self.position:
            return
        
        # Check stop loss
        if self.position == 'SELL':
            if current_price >= self.stop_loss:
                self.close_position(current_price, 'Stop Loss Hit')
                return
            if current_price <= self.take_profit:
                self.close_position(current_price, 'Take Profit Hit')
                return
            # Check if price returned to entry (exit immediately)
            if current_price >= self.entry_price:
                self.close_position(current_price, 'Price Returned to Entry')
                return
        else:  # BUY
            if current_price <= self.stop_loss:
                self.close_position(current_price, 'Stop Loss Hit')
                return
            if current_price >= self.take_profit:
                self.close_position(current_price, 'Take Profit Hit')
                return
            # Check if price returned to entry (exit immediately)
            if current_price <= self.entry_price:
                self.close_position(current_price, 'Price Returned to Entry')
                return
    
    def save_log(self):
        """Save trading log to file"""
        try:
            os.makedirs('/mnt/user-data/outputs', exist_ok=True)
            with open(self.log_file, 'w') as f:
                json.dump({
                    'balance': self.paper_balance,
                    'trades': self.trades_history,
                    'current_position': {
                        'type': self.position,
                        'entry': self.entry_price,
                        'stop_loss': self.stop_loss,
                        'take_profit': self.take_profit
                    } if self.position else None
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving log: {e}")
    
    def run(self, iterations=None):
        """
        Run the scalping bot
        
        Args:
            iterations: Number of iterations to run (None = infinite)
        """
        print(f"\n{'='*60}")
        print(f"🤖 BTC SCALPING BOT STARTED")
        print(f"Mode: {'PAPER TRADING' if self.paper_trading else 'LIVE TRADING'}")
        print(f"Symbol: {self.symbol}")
        print(f"Timeframe: {self.timeframe}")
        print(f"Starting Balance: ${self.paper_balance:.2f}")
        print(f"{'='*60}\n")
        
        iteration = 0
        
        try:
            while iterations is None or iteration < iterations:
                iteration += 1
                
                # Fetch candles
                df = self.get_candles()
                if df is None or len(df) < self.lookback_candles:
                    print("Waiting for data...")
                    time.sleep(60)
                    continue
                
                current_price = df.iloc[-1]['close']
                current_time = df.iloc[-1]['timestamp']
                
                print(f"[{current_time}] Price: ${current_price:.2f} | Balance: ${self.paper_balance:.2f}", end='')
                
                # Check exit conditions first if we have a position
                if self.position:
                    print(f" | Position: {self.position} @ ${self.entry_price:.2f}")
                    self.check_exit_conditions(current_price)
                else:
                    print(" | No Position")
                    
                    # Look for new setups
                    zones = self.find_supply_demand_zones(df)
                    
                    # Check for sell setup
                    sell_signal, sell_setup = self.check_sell_setup(df, zones)
                    if sell_signal:
                        self.open_position(sell_setup)
                    
                    # Check for buy setup (only if no sell signal)
                    if not sell_signal:
                        buy_signal, buy_setup = self.check_buy_setup(df, zones)
                        if buy_signal:
                            self.open_position(buy_setup)
                
                # Save log periodically
                if iteration % 10 == 0:
                    self.save_log()
                
                # Wait for next candle (5 minutes for 5m timeframe)
                time.sleep(300)  # 5 minutes
                
        except KeyboardInterrupt:
            print("\n\n🛑 Bot stopped by user")
            self.save_log()
            self.print_summary()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            self.save_log()
    
    def print_summary(self):
        """Print trading summary"""
        print(f"\n{'='*60}")
        print(f"📊 TRADING SUMMARY")
        print(f"{'='*60}")
        print(f"Starting Balance: $10,000.00")
        print(f"Current Balance: ${self.paper_balance:.2f}")
        print(f"Total P&L: ${self.paper_balance - 10000:.2f}")
        print(f"ROI: {((self.paper_balance - 10000) / 10000) * 100:.2f}%")
        print(f"Total Trades: {len([t for t in self.trades_history if t['action'] == 'CLOSE_POSITION'])}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    # Initialize bot in paper trading mode
    bot = ScalpingBot(
        symbol='BTC/USDT',
        timeframe='5m',
        paper_trading=True
    )
    
    # Run the bot
    bot.run()
