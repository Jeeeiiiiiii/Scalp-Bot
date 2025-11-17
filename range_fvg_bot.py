#!/usr/bin/env python3
"""
Range Scalping Bot with Fair Value Gap Strategy
Based on the mentor's trading strategy:
1. Mark the 9:30-9:45 EST range on 15-minute chart
2. Wait for Fair Value Gap breakout on 5-minute chart
3. Enter with limit order at FVG level
4. 2:1 risk/reward ratio
5. Entry cutoff at 12 PM EST
"""

import ccxt
import pandas as pd
import time
from datetime import datetime, timezone
import pytz
import json
import os

class RangeFVGBot:
    def __init__(self, symbol='BTC/USDT', paper_trading=True, initial_balance=10000):
        """
        Initialize the Range FVG Scalping Bot

        Args:
            symbol: Trading pair (default: BTC/USDT)
            paper_trading: Enable paper trading mode (default: True)
            initial_balance: Starting balance for paper trading
        """
        self.symbol = symbol
        self.paper_trading = paper_trading

        # Initialize exchange (using Binance)
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
        })

        # Timezone setup (Eastern Standard Time)
        self.est = pytz.timezone('America/New_York')

        # Range tracking
        self.daily_range = {
            'high': None,
            'low': None,
            'date': None,
            'marked': False
        }

        # Trading parameters
        self.position = None
        self.pending_order = None
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.position_size = 0

        # Paper trading balance
        self.paper_balance = initial_balance
        self.initial_balance = initial_balance
        self.trades_history = []

        # Strategy parameters
        self.risk_per_trade = 0.02  # Risk 2% per trade
        self.reward_ratio = 2  # 2:1 reward/risk ratio

        # Log file
        self.log_file = '/mnt/user-data/outputs/range_fvg_bot_log.json'

        print(f"✅ Range FVG Bot initialized")
        print(f"Symbol: {self.symbol}")
        print(f"Mode: {'PAPER TRADING' if self.paper_trading else 'LIVE TRADING'}")
        print(f"Initial Balance: ${self.paper_balance:,.2f}")

    def get_est_time(self):
        """Get current time in EST"""
        return datetime.now(self.est)

    def is_market_open_time(self):
        """Check if current time is during market hours (9:30 AM - 4:00 PM EST)"""
        current_time = self.get_est_time()
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= current_time <= market_close

    def should_mark_range(self):
        """Check if we should mark the daily range (after 9:45 AM EST)"""
        current_time = self.get_est_time()
        range_mark_time = current_time.replace(hour=9, minute=45, second=0, microsecond=0)
        current_date = current_time.date()

        # Check if it's a new day and after 9:45 AM
        if self.daily_range['date'] != current_date:
            self.daily_range['marked'] = False
            self.daily_range['date'] = current_date

        return current_time >= range_mark_time and not self.daily_range['marked']

    def can_enter_trade(self):
        """Check if we can still enter trades (before 12 PM EST)"""
        current_time = self.get_est_time()
        entry_cutoff = current_time.replace(hour=12, minute=0, second=0, microsecond=0)
        return current_time < entry_cutoff

    def get_candles(self, timeframe='5m', limit=100):
        """Fetch OHLCV candles from exchange"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            # Convert to EST
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert(self.est)
            return df
        except Exception as e:
            print(f"❌ Error fetching candles: {e}")
            return None

    def mark_daily_range(self):
        """Mark the high and low of the 9:30-9:45 EST candle on 15-minute chart"""
        try:
            # Fetch 15-minute candles
            df = self.get_candles(timeframe='15m', limit=10)
            if df is None or len(df) == 0:
                return False

            current_time = self.get_est_time()
            current_date = current_time.date()

            # Find the 9:30 candle (which closes at 9:45)
            for idx, row in df.iterrows():
                candle_time = row['timestamp']
                if (candle_time.date() == current_date and
                    candle_time.hour == 9 and
                    candle_time.minute == 30):

                    self.daily_range['high'] = row['high']
                    self.daily_range['low'] = row['low']
                    self.daily_range['marked'] = True
                    self.daily_range['date'] = current_date

                    print(f"\n{'='*60}")
                    print(f"📊 DAILY RANGE MARKED")
                    print(f"Date: {current_date}")
                    print(f"High: ${self.daily_range['high']:,.2f}")
                    print(f"Low: ${self.daily_range['low']:,.2f}")
                    print(f"Range: ${self.daily_range['high'] - self.daily_range['low']:,.2f}")
                    print(f"{'='*60}\n")

                    return True

            print(f"⏳ Waiting for 9:30-9:45 EST candle to close...")
            return False

        except Exception as e:
            print(f"❌ Error marking range: {e}")
            return False

    def detect_fair_value_gap(self, df):
        """
        Detect Fair Value Gap pattern on 5-minute chart

        FVG Requirements:
        - 3 candle pattern
        - Gap between candle 1's wick and candle 3's wick
        - Middle candle is expansive and leaves a gap
        - At least one candle closes inside range, one closes outside
        - Pattern touches the daily range high or low

        Returns:
            dict: FVG details if found, None otherwise
        """
        if not self.daily_range['marked']:
            return None

        if len(df) < 3:
            return None

        # Get last 3 candles
        candle1 = df.iloc[-3]
        candle2 = df.iloc[-2]
        candle3 = df.iloc[-1]

        range_high = self.daily_range['high']
        range_low = self.daily_range['low']

        # Check for BULLISH Fair Value Gap (for long entries)
        # Gap between candle1's high and candle3's low
        bullish_gap_bottom = candle1['high']
        bullish_gap_top = candle3['low']

        if bullish_gap_top > bullish_gap_bottom:  # There's a gap
            # Check if this is a bullish FVG breaking above range high
            # At least one candle should close outside range, one should be touching/inside
            candles_close_above = sum([
                candle1['close'] > range_high,
                candle2['close'] > range_high,
                candle3['close'] > range_high
            ])

            candles_touch_range = sum([
                candle1['low'] <= range_high,
                candle2['low'] <= range_high,
                candle3['low'] <= range_high
            ])

            # Valid bullish FVG: at least one candle closes above range, and pattern touches range
            if candles_close_above >= 1 and candles_touch_range >= 1:
                fvg_price = (bullish_gap_bottom + bullish_gap_top) / 2  # Middle of the gap

                return {
                    'type': 'BULLISH',
                    'direction': 'LONG',
                    'gap_top': bullish_gap_top,
                    'gap_bottom': bullish_gap_bottom,
                    'fvg_price': fvg_price,
                    'candle1': candle1,
                    'candle2': candle2,
                    'candle3': candle3,
                    'timestamp': candle3['timestamp']
                }

        # Check for BEARISH Fair Value Gap (for short entries)
        # Gap between candle1's low and candle3's high
        bearish_gap_top = candle1['low']
        bearish_gap_bottom = candle3['high']

        if bearish_gap_top > bearish_gap_bottom:  # There's a gap
            # Check if this is a bearish FVG breaking below range low
            candles_close_below = sum([
                candle1['close'] < range_low,
                candle2['close'] < range_low,
                candle3['close'] < range_low
            ])

            candles_touch_range = sum([
                candle1['high'] >= range_low,
                candle2['high'] >= range_low,
                candle3['high'] >= range_low
            ])

            # Valid bearish FVG: at least one candle closes below range, and pattern touches range
            if candles_close_below >= 1 and candles_touch_range >= 1:
                fvg_price = (bearish_gap_top + bearish_gap_bottom) / 2  # Middle of the gap

                return {
                    'type': 'BEARISH',
                    'direction': 'SHORT',
                    'gap_top': bearish_gap_top,
                    'gap_bottom': bearish_gap_bottom,
                    'fvg_price': fvg_price,
                    'candle1': candle1,
                    'candle2': candle2,
                    'candle3': candle3,
                    'timestamp': candle3['timestamp']
                }

        return None

    def calculate_position_size(self, entry_price, stop_loss):
        """
        Calculate position size based on risk percentage

        Args:
            entry_price: Entry price for the trade
            stop_loss: Stop loss price

        Returns:
            float: Position size
        """
        risk_amount = self.paper_balance * self.risk_per_trade
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            return 0

        position_size = risk_amount / risk_per_unit
        return position_size

    def create_limit_order(self, fvg):
        """
        Create a limit order at the FVG level

        Args:
            fvg: Fair Value Gap details
        """
        if not self.can_enter_trade():
            print(f"⏰ Entry cutoff time (12 PM EST) has passed. No new trades today.")
            return

        if self.pending_order or self.position:
            return  # Already have an order or position

        entry_price = fvg['fvg_price']

        # Calculate stop loss
        if fvg['direction'] == 'LONG':
            # Stop loss below the first candle's low in the FVG pattern
            stop_loss = fvg['candle1']['low'] * 0.999  # Add small buffer
        else:  # SHORT
            # Stop loss above the first candle's high in the FVG pattern
            stop_loss = fvg['candle1']['high'] * 1.001  # Add small buffer

        # Calculate take profit (2:1 risk/reward)
        risk = abs(entry_price - stop_loss)
        if fvg['direction'] == 'LONG':
            take_profit = entry_price + (risk * self.reward_ratio)
        else:  # SHORT
            take_profit = entry_price - (risk * self.reward_ratio)

        # Calculate position size
        position_size = self.calculate_position_size(entry_price, stop_loss)

        if position_size == 0:
            print(f"❌ Invalid position size calculated")
            return

        self.pending_order = {
            'direction': fvg['direction'],
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'fvg_type': fvg['type'],
            'created_at': fvg['timestamp']
        }

        print(f"\n{'='*60}")
        print(f"🎯 LIMIT ORDER CREATED")
        print(f"Type: {fvg['direction']}")
        print(f"Entry: ${entry_price:,.2f}")
        print(f"Stop Loss: ${stop_loss:,.2f}")
        print(f"Take Profit: ${take_profit:,.2f}")
        print(f"Position Size: {position_size:.6f}")
        print(f"Risk: ${risk * position_size:,.2f} ({self.risk_per_trade * 100}%)")
        print(f"Potential Reward: ${risk * position_size * self.reward_ratio:,.2f}")
        print(f"Risk/Reward: 1:{self.reward_ratio}")
        print(f"{'='*60}\n")

    def check_limit_order_fill(self, current_price):
        """Check if pending limit order should be filled"""
        if not self.pending_order:
            return

        order = self.pending_order

        # Check if price has touched the entry level
        filled = False
        if order['direction'] == 'LONG':
            # For long, we want price to come down to our limit order
            if current_price <= order['entry_price']:
                filled = True
        else:  # SHORT
            # For short, we want price to come up to our limit order
            if current_price >= order['entry_price']:
                filled = True

        if filled:
            self.position = {
                'direction': order['direction'],
                'entry_price': order['entry_price'],
                'stop_loss': order['stop_loss'],
                'take_profit': order['take_profit'],
                'position_size': order['position_size'],
                'entry_time': datetime.now(self.est)
            }

            print(f"\n{'='*60}")
            print(f"✅ LIMIT ORDER FILLED")
            print(f"Type: {order['direction']}")
            print(f"Entry: ${order['entry_price']:,.2f}")
            print(f"Current Price: ${current_price:,.2f}")
            print(f"{'='*60}\n")

            self.pending_order = None  # Clear pending order

    def check_exit_conditions(self, current_high, current_low, current_close):
        """Check if position should be closed"""
        if not self.position:
            return

        pos = self.position
        exit_price = None
        exit_reason = None

        if pos['direction'] == 'LONG':
            # Check stop loss
            if current_low <= pos['stop_loss']:
                exit_price = pos['stop_loss']
                exit_reason = 'Stop Loss'
            # Check take profit
            elif current_high >= pos['take_profit']:
                exit_price = pos['take_profit']
                exit_reason = 'Take Profit'

        else:  # SHORT
            # Check stop loss
            if current_high >= pos['stop_loss']:
                exit_price = pos['stop_loss']
                exit_reason = 'Stop Loss'
            # Check take profit
            elif current_low <= pos['take_profit']:
                exit_price = pos['take_profit']
                exit_reason = 'Take Profit'

        if exit_price:
            self.close_position(exit_price, exit_reason)

    def close_position(self, exit_price, reason):
        """Close the current position"""
        if not self.position:
            return

        pos = self.position

        # Calculate P&L
        if pos['direction'] == 'LONG':
            pnl = (exit_price - pos['entry_price']) * pos['position_size']
        else:  # SHORT
            pnl = (pos['entry_price'] - exit_price) * pos['position_size']

        # Update balance
        self.paper_balance += pnl

        # Record trade
        trade = {
            'entry_time': str(pos['entry_time']),
            'exit_time': str(datetime.now(self.est)),
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'stop_loss': pos['stop_loss'],
            'take_profit': pos['take_profit'],
            'position_size': pos['position_size'],
            'pnl': pnl,
            'pnl_pct': (pnl / self.paper_balance) * 100,
            'reason': reason,
            'balance': self.paper_balance
        }

        self.trades_history.append(trade)

        # Print trade result
        print(f"\n{'='*60}")
        print(f"🔴 POSITION CLOSED")
        print(f"Type: {pos['direction']}")
        print(f"Entry: ${pos['entry_price']:,.2f}")
        print(f"Exit: ${exit_price:,.2f}")
        print(f"Reason: {reason}")
        print(f"P&L: ${pnl:,.2f} ({(pnl / self.initial_balance) * 100:.2f}%)")
        print(f"New Balance: ${self.paper_balance:,.2f}")
        print(f"Total Return: {((self.paper_balance - self.initial_balance) / self.initial_balance) * 100:.2f}%")
        print(f"{'='*60}\n")

        # Clear position
        self.position = None

        # Save log
        self.save_log()

    def save_log(self):
        """Save trading log to file"""
        try:
            os.makedirs('/mnt/user-data/outputs', exist_ok=True)

            log_data = {
                'initial_balance': self.initial_balance,
                'current_balance': self.paper_balance,
                'total_pnl': self.paper_balance - self.initial_balance,
                'roi': ((self.paper_balance - self.initial_balance) / self.initial_balance) * 100,
                'total_trades': len(self.trades_history),
                'daily_range': {
                    'high': self.daily_range['high'],
                    'low': self.daily_range['low'],
                    'date': str(self.daily_range['date']),
                    'marked': self.daily_range['marked']
                },
                'current_position': {
                    'direction': self.position['direction'],
                    'entry_price': self.position['entry_price'],
                    'stop_loss': self.position['stop_loss'],
                    'take_profit': self.position['take_profit'],
                    'entry_time': str(self.position['entry_time'])
                } if self.position else None,
                'pending_order': self.pending_order,
                'trades': self.trades_history
            }

            with open(self.log_file, 'w') as f:
                json.dump(log_data, f, indent=2)

        except Exception as e:
            print(f"❌ Error saving log: {e}")

    def print_summary(self):
        """Print trading summary"""
        print(f"\n{'='*60}")
        print(f"📊 TRADING SUMMARY")
        print(f"{'='*60}")

        if len(self.trades_history) == 0:
            print("No trades executed yet")
            print(f"Current Balance: ${self.paper_balance:,.2f}")
            print(f"{'='*60}\n")
            return

        winning_trades = [t for t in self.trades_history if t['pnl'] > 0]
        losing_trades = [t for t in self.trades_history if t['pnl'] < 0]

        total_trades = len(self.trades_history)
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

        total_pnl = self.paper_balance - self.initial_balance
        roi = (total_pnl / self.initial_balance) * 100

        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0

        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Current Balance: ${self.paper_balance:,.2f}")
        print(f"Total P&L: ${total_pnl:,.2f}")
        print(f"ROI: {roi:.2f}%")
        print(f"\nTotal Trades: {total_trades}")
        print(f"Winning Trades: {len(winning_trades)} ({win_rate:.1f}%)")
        print(f"Losing Trades: {len(losing_trades)} ({100 - win_rate:.1f}%)")
        print(f"\nAverage Win: ${avg_win:,.2f}")
        print(f"Average Loss: ${avg_loss:,.2f}")

        if avg_loss != 0:
            profit_factor = abs(avg_win / avg_loss)
            print(f"Profit Factor: {profit_factor:.2f}")

        print(f"{'='*60}\n")

    def run(self):
        """Main bot loop"""
        print(f"\n{'='*60}")
        print(f"🤖 RANGE FVG SCALPING BOT STARTED")
        print(f"{'='*60}\n")

        try:
            while True:
                current_time = self.get_est_time()

                # Check if we should mark the daily range
                if self.should_mark_range():
                    self.mark_daily_range()

                # Only trade during market hours
                if not self.is_market_open_time():
                    print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}] Market closed. Waiting...")
                    time.sleep(300)  # Sleep 5 minutes
                    continue

                # Fetch 5-minute candles
                df = self.get_candles(timeframe='5m', limit=20)
                if df is None or len(df) < 3:
                    print(f"⏳ Waiting for data...")
                    time.sleep(60)
                    continue

                current_candle = df.iloc[-1]
                current_price = current_candle['close']
                current_high = current_candle['high']
                current_low = current_candle['low']

                # Status update
                status = f"[{current_time.strftime('%H:%M:%S')}] Price: ${current_price:,.2f} | Balance: ${self.paper_balance:,.2f}"

                if self.position:
                    status += f" | Position: {self.position['direction']} @ ${self.position['entry_price']:,.2f}"
                elif self.pending_order:
                    status += f" | Pending: {self.pending_order['direction']} @ ${self.pending_order['entry_price']:,.2f}"
                else:
                    status += " | No Position"

                print(status)

                # Check if pending limit order is filled
                if self.pending_order:
                    self.check_limit_order_fill(current_price)

                # Check exit conditions if we have a position
                if self.position:
                    self.check_exit_conditions(current_high, current_low, current_price)

                # Look for new FVG setups if no position or pending order
                if not self.position and not self.pending_order and self.daily_range['marked']:
                    fvg = self.detect_fair_value_gap(df)
                    if fvg:
                        print(f"\n🔍 Fair Value Gap Detected: {fvg['type']}")
                        self.create_limit_order(fvg)

                # Sleep for 1 minute before next check
                time.sleep(60)

        except KeyboardInterrupt:
            print(f"\n\n🛑 Bot stopped by user")
            self.save_log()
            self.print_summary()
        except Exception as e:
            print(f"\n❌ Error in main loop: {e}")
            import traceback
            traceback.print_exc()
            self.save_log()


if __name__ == "__main__":
    # Initialize and run the bot
    bot = RangeFVGBot(
        symbol='BTC/USDT',
        paper_trading=True,
        initial_balance=10000
    )

    bot.run()
