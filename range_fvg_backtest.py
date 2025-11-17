#!/usr/bin/env python3
"""
Backtest the Range FVG Scalping Strategy on Historical Data
Tests the strategy: Mark 9:30-9:45 EST range, trade FVG breakouts with 2:1 R/R
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import pytz
import json
import os

class RangeFVGBacktest:
    def __init__(self, initial_balance=10000, risk_per_trade=0.02, reward_ratio=2):
        """
        Initialize backtest

        Args:
            initial_balance: Starting balance
            risk_per_trade: Risk percentage per trade (0.02 = 2%)
            reward_ratio: Reward to risk ratio (2 = 2:1)
        """
        self.exchange = ccxt.binance({'enableRateLimit': True})
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.reward_ratio = reward_ratio

        self.est = pytz.timezone('America/New_York')

        self.trades = []
        self.position = None
        self.pending_order = None
        self.daily_range = None

    def fetch_historical_data(self, symbol='BTC/USDT', timeframe='5m', days=7):
        """Fetch historical OHLCV data"""
        print(f"Fetching {days} days of {timeframe} data for {symbol}...")

        since = self.exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
        all_candles = []

        while True:
            try:
                candles = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
                if not candles:
                    break
                all_candles.extend(candles)
                since = candles[-1][0] + 1

                # Break if we've caught up to now
                if candles[-1][0] >= self.exchange.milliseconds() - (60 * 1000):
                    break

                # Rate limiting
                import time
                time.sleep(0.5)

            except Exception as e:
                print(f"Error fetching data: {e}")
                break

        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert(self.est)

        print(f"Fetched {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
        return df

    def mark_daily_range_from_15m(self, df_15m, current_date):
        """
        Mark the daily range from 15-minute data for a specific date

        Args:
            df_15m: DataFrame with 15-minute candles
            current_date: Date to find the 9:30 candle for

        Returns:
            dict: Range high/low or None
        """
        # Find the 9:30 candle for this date
        candle_930 = df_15m[
            (df_15m['timestamp'].dt.date == current_date) &
            (df_15m['timestamp'].dt.hour == 9) &
            (df_15m['timestamp'].dt.minute == 30)
        ]

        if len(candle_930) > 0:
            candle = candle_930.iloc[0]
            return {
                'high': candle['high'],
                'low': candle['low'],
                'date': current_date
            }

        return None

    def detect_fair_value_gap(self, candle1, candle2, candle3, range_high, range_low):
        """
        Detect Fair Value Gap pattern from 3 candles

        Returns:
            dict: FVG details or None
        """
        # Check for BULLISH Fair Value Gap
        bullish_gap_bottom = candle1['high']
        bullish_gap_top = candle3['low']

        if bullish_gap_top > bullish_gap_bottom:
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

            if candles_close_above >= 1 and candles_touch_range >= 1:
                fvg_price = (bullish_gap_bottom + bullish_gap_top) / 2

                return {
                    'type': 'BULLISH',
                    'direction': 'LONG',
                    'gap_top': bullish_gap_top,
                    'gap_bottom': bullish_gap_bottom,
                    'fvg_price': fvg_price,
                    'stop_loss': candle1['low'] * 0.999,
                    'candle1_low': candle1['low']
                }

        # Check for BEARISH Fair Value Gap
        bearish_gap_top = candle1['low']
        bearish_gap_bottom = candle3['high']

        if bearish_gap_top > bearish_gap_bottom:
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

            if candles_close_below >= 1 and candles_touch_range >= 1:
                fvg_price = (bearish_gap_top + bearish_gap_bottom) / 2

                return {
                    'type': 'BEARISH',
                    'direction': 'SHORT',
                    'gap_top': bearish_gap_top,
                    'gap_bottom': bearish_gap_bottom,
                    'fvg_price': fvg_price,
                    'stop_loss': candle1['high'] * 1.001,
                    'candle1_high': candle1['high']
                }

        return None

    def calculate_position_size(self, entry_price, stop_loss):
        """Calculate position size based on risk"""
        risk_amount = self.balance * self.risk_per_trade
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            return 0

        return risk_amount / risk_per_unit

    def create_order(self, fvg, current_time):
        """Create a pending limit order"""
        entry_price = fvg['fvg_price']
        stop_loss = fvg['stop_loss']

        risk = abs(entry_price - stop_loss)

        if fvg['direction'] == 'LONG':
            take_profit = entry_price + (risk * self.reward_ratio)
        else:
            take_profit = entry_price - (risk * self.reward_ratio)

        position_size = self.calculate_position_size(entry_price, stop_loss)

        if position_size == 0:
            return

        self.pending_order = {
            'direction': fvg['direction'],
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'created_at': current_time
        }

    def check_order_fill(self, candle):
        """Check if pending order gets filled"""
        if not self.pending_order:
            return False

        order = self.pending_order
        filled = False

        if order['direction'] == 'LONG':
            # Price must come down to our limit order
            if candle['low'] <= order['entry_price']:
                filled = True
        else:  # SHORT
            # Price must come up to our limit order
            if candle['high'] >= order['entry_price']:
                filled = True

        if filled:
            self.position = {
                'direction': order['direction'],
                'entry_price': order['entry_price'],
                'stop_loss': order['stop_loss'],
                'take_profit': order['take_profit'],
                'position_size': order['position_size'],
                'entry_time': candle['timestamp']
            }
            self.pending_order = None
            return True

        return False

    def check_exit(self, candle):
        """Check if position should exit"""
        if not self.position:
            return False, None, None

        pos = self.position

        if pos['direction'] == 'LONG':
            # Check stop loss
            if candle['low'] <= pos['stop_loss']:
                return True, pos['stop_loss'], 'Stop Loss'

            # Check take profit
            if candle['high'] >= pos['take_profit']:
                return True, pos['take_profit'], 'Take Profit'

        else:  # SHORT
            # Check stop loss
            if candle['high'] >= pos['stop_loss']:
                return True, pos['stop_loss'], 'Stop Loss'

            # Check take profit
            if candle['low'] <= pos['take_profit']:
                return True, pos['take_profit'], 'Take Profit'

        return False, None, None

    def close_position(self, exit_price, reason, exit_time):
        """Close position and record trade"""
        pos = self.position

        if pos['direction'] == 'LONG':
            pnl = (exit_price - pos['entry_price']) * pos['position_size']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['position_size']

        self.balance += pnl

        trade = {
            'entry_time': str(pos['entry_time']),
            'exit_time': str(exit_time),
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'stop_loss': pos['stop_loss'],
            'take_profit': pos['take_profit'],
            'position_size': pos['position_size'],
            'pnl': pnl,
            'pnl_pct': (pnl / self.balance) * 100,
            'reason': reason,
            'balance': self.balance
        }

        self.trades.append(trade)
        self.position = None

    def run_backtest(self, df_5m, df_15m):
        """
        Run backtest on historical data

        Args:
            df_5m: 5-minute candles
            df_15m: 15-minute candles
        """
        print(f"\n{'='*60}")
        print(f"🔬 STARTING RANGE FVG BACKTEST")
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Risk per Trade: {self.risk_per_trade * 100}%")
        print(f"Reward/Risk Ratio: {self.reward_ratio}:1")
        print(f"{'='*60}\n")

        current_date = None
        daily_range = None
        trades_today = 0

        for idx in range(3, len(df_5m)):
            candle = df_5m.iloc[idx]
            candle_date = candle['timestamp'].date()
            candle_time = candle['timestamp'].time()

            # New day - reset and mark range
            if candle_date != current_date:
                current_date = candle_date
                daily_range = self.mark_daily_range_from_15m(df_15m, current_date)
                trades_today = 0
                self.pending_order = None  # Cancel any pending orders from previous day

                if daily_range:
                    print(f"\n📅 {current_date} - Range Marked: High ${daily_range['high']:,.2f} | Low ${daily_range['low']:,.2f}")

            # Skip if no range marked yet
            if not daily_range:
                continue

            # Only trade between 9:45 AM and 12:00 PM EST
            if not (candle_time >= datetime.strptime('09:45', '%H:%M').time() and
                    candle_time <= datetime.strptime('12:00', '%H:%M').time()):
                continue

            # Check if pending order is filled
            if self.pending_order:
                if self.check_order_fill(candle):
                    print(f"  [{candle['timestamp'].strftime('%H:%M')}] Order Filled: {self.position['direction']} @ ${self.position['entry_price']:,.2f}")

            # Check exit conditions
            if self.position:
                should_exit, exit_price, reason = self.check_exit(candle)
                if should_exit:
                    self.close_position(exit_price, reason, candle['timestamp'])
                    trades_today += 1
                    pnl_str = f"+${self.trades[-1]['pnl']:,.2f}" if self.trades[-1]['pnl'] > 0 else f"-${abs(self.trades[-1]['pnl']):,.2f}"
                    print(f"  [{candle['timestamp'].strftime('%H:%M')}] Closed: {reason} | P&L: {pnl_str} | Balance: ${self.balance:,.2f}")

            # Look for new FVG setups (max 1 trade per day for now)
            if not self.position and not self.pending_order and trades_today < 1:
                if idx >= 2:
                    candle1 = df_5m.iloc[idx - 2]
                    candle2 = df_5m.iloc[idx - 1]
                    candle3 = candle

                    fvg = self.detect_fair_value_gap(
                        candle1, candle2, candle3,
                        daily_range['high'], daily_range['low']
                    )

                    if fvg:
                        self.create_order(fvg, candle['timestamp'])
                        if self.pending_order:
                            print(f"  [{candle['timestamp'].strftime('%H:%M')}] FVG Detected: {fvg['direction']} | Limit Order @ ${self.pending_order['entry_price']:,.2f}")

        # Close any remaining position
        if self.position:
            last_candle = df_5m.iloc[-1]
            self.close_position(last_candle['close'], 'Backtest End', last_candle['timestamp'])

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

        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

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
        print(f"Losing Trades: {len(losing_trades)} ({100 - win_rate:.1f}%)")
        print(f"\nAverage Win: ${avg_win:,.2f}")
        print(f"Average Loss: ${avg_loss:,.2f}")

        if avg_loss != 0:
            profit_factor = abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades))
            print(f"Profit Factor: {profit_factor:.2f}")

        # Exit reasons breakdown
        exit_reasons = {}
        for trade in self.trades:
            reason = trade['reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        print(f"\nExit Reasons:")
        for reason, count in exit_reasons.items():
            print(f"  {reason}: {count} ({(count / total_trades) * 100:.1f}%)")

        print(f"{'='*60}\n")

        # Save results
        os.makedirs('/mnt/user-data/outputs', exist_ok=True)
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

        with open('/mnt/user-data/outputs/range_fvg_backtest_results.json', 'w') as f:
            json.dump(results, f, indent=2)

        print("✅ Results saved to /mnt/user-data/outputs/range_fvg_backtest_results.json")


if __name__ == "__main__":
    # Initialize backtest
    backtest = RangeFVGBacktest(
        initial_balance=10000,
        risk_per_trade=0.02,  # 2% risk per trade
        reward_ratio=2  # 2:1 reward/risk
    )

    # Fetch historical data
    print("Fetching 5-minute data...")
    df_5m = backtest.fetch_historical_data(symbol='BTC/USDT', timeframe='5m', days=7)

    print("Fetching 15-minute data...")
    df_15m = backtest.fetch_historical_data(symbol='BTC/USDT', timeframe='15m', days=7)

    # Run backtest
    if df_5m is not None and df_15m is not None:
        backtest.run_backtest(df_5m, df_15m)
    else:
        print("❌ Failed to fetch historical data")
