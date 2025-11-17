#!/usr/bin/env python3
"""
Range Scalping Bot with Fair Value Gap Strategy - LIVE TRADING VERSION
Supports both paper trading and live trading with API keys
"""

import ccxt
import pandas as pd
import time
from datetime import datetime
import pytz
import json
import os
import sys

class RangeFVGBotLive:
    def __init__(self, config_file='config_live.json'):
        """
        Initialize the Range FVG Scalping Bot from config file

        Args:
            config_file: Path to JSON configuration file
        """
        # Load configuration
        self.config = self.load_config(config_file)

        # Extract settings
        exchange_config = self.config['exchange']
        bot_settings = self.config['bot_settings']
        self.strategy_params = self.config['strategy_parameters']
        self.risk_mgmt = self.config['risk_management']
        time_settings = self.config['time_settings']

        self.symbol = bot_settings['symbol']
        self.paper_trading = bot_settings['paper_trading']

        # Initialize exchange
        self.exchange = self.setup_exchange(exchange_config)

        # Timezone setup
        self.timezone = pytz.timezone(time_settings['timezone'])

        # Range tracking
        self.daily_range = {
            'high': None,
            'low': None,
            'date': None,
            'marked': False
        }

        # Trading state
        self.position = None
        self.pending_order = None
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.position_size = 0

        # Paper trading balance
        if self.paper_trading:
            self.paper_balance = bot_settings['initial_balance']
            self.initial_balance = bot_settings['initial_balance']
        else:
            # Get real balance from exchange
            self.update_real_balance()

        self.trades_history = []
        self.daily_trades = 0
        self.daily_loss = 0

        # Time settings
        self.time_settings = time_settings

        # Logging
        self.setup_logging()

        # Print initialization
        self.print_startup_info()

    def load_config(self, config_file):
        """Load configuration from JSON file"""
        if not os.path.exists(config_file):
            print(f"❌ Config file not found: {config_file}")
            print(f"Please create {config_file} with your API keys and settings")
            sys.exit(1)

        with open(config_file, 'r') as f:
            config = json.load(f)

        return config

    def setup_exchange(self, exchange_config):
        """Setup exchange connection with API keys"""
        exchange_name = exchange_config['name']

        # Exchange configuration
        exchange_params = {
            'enableRateLimit': True,
        }

        # Add API keys if not in paper trading mode
        if not self.paper_trading:
            api_key = exchange_config.get('api_key', '')
            api_secret = exchange_config.get('api_secret', '')

            if not api_key or api_key == 'YOUR_API_KEY_HERE':
                print("❌ ERROR: No API key configured!")
                print("Please edit config_live.json and add your Binance API keys")
                sys.exit(1)

            exchange_params['apiKey'] = api_key
            exchange_params['secret'] = api_secret

            # Testnet support
            if exchange_config.get('testnet', False):
                exchange_params['urls'] = {
                    'api': 'https://testnet.binance.vision/api'
                }

        # Initialize exchange
        if exchange_name == 'binance':
            exchange = ccxt.binance(exchange_params)
        else:
            print(f"❌ Unsupported exchange: {exchange_name}")
            sys.exit(1)

        return exchange

    def update_real_balance(self):
        """Get real balance from exchange"""
        try:
            balance = self.exchange.fetch_balance()
            self.paper_balance = balance['USDT']['free']
            self.initial_balance = self.paper_balance
            print(f"✅ Real balance loaded: ${self.paper_balance:,.2f} USDT")
        except Exception as e:
            print(f"❌ Error fetching balance: {e}")
            print("Make sure your API keys have 'Read' permission")
            sys.exit(1)

    def setup_logging(self):
        """Setup logging directory"""
        log_dir = os.path.dirname(self.config['logging']['log_file'])
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def print_startup_info(self):
        """Print startup information"""
        print(f"\n{'='*60}")
        print(f"🤖 RANGE FVG SCALPING BOT - LIVE VERSION")
        print(f"{'='*60}")
        print(f"Symbol: {self.symbol}")
        print(f"Mode: {'PAPER TRADING' if self.paper_trading else '🔴 LIVE TRADING'}")
        print(f"Exchange: {self.exchange.name}")
        print(f"Balance: ${self.paper_balance:,.2f} USDT")
        print(f"Risk per Trade: {self.strategy_params['risk_per_trade']*100}%")
        print(f"Risk/Reward: 1:{self.strategy_params['reward_ratio']}")
        print(f"Max Daily Loss: ${self.risk_mgmt['max_daily_loss_usd']}")
        print(f"Max Daily Trades: {self.risk_mgmt['max_daily_trades']}")
        print(f"Timezone: {self.time_settings['timezone']}")

        if not self.paper_trading:
            print(f"\n⚠️  WARNING: LIVE TRADING MODE ENABLED ⚠️")
            print(f"Real money will be used for trading!")
            response = input("Type 'YES' to confirm and continue: ")
            if response != 'YES':
                print("❌ Live trading cancelled")
                sys.exit(0)

        print(f"{'='*60}\n")

    def get_current_time(self):
        """Get current time in configured timezone"""
        return datetime.now(self.timezone)

    def is_market_open_time(self):
        """Check if current time is during market hours"""
        current_time = self.get_current_time()

        market_open_str = self.time_settings['market_open']
        market_close_str = self.time_settings['market_close']

        market_open = current_time.replace(
            hour=int(market_open_str.split(':')[0]),
            minute=int(market_open_str.split(':')[1]),
            second=0, microsecond=0
        )
        market_close = current_time.replace(
            hour=int(market_close_str.split(':')[0]),
            minute=int(market_close_str.split(':')[1]),
            second=0, microsecond=0
        )

        return market_open <= current_time <= market_close

    def should_mark_range(self):
        """Check if we should mark the daily range"""
        current_time = self.get_current_time()

        range_end_str = self.time_settings['range_end_time']
        range_mark_time = current_time.replace(
            hour=int(range_end_str.split(':')[0]),
            minute=int(range_end_str.split(':')[1]),
            second=0, microsecond=0
        )

        current_date = current_time.date()

        if self.daily_range['date'] != current_date:
            self.daily_range['marked'] = False
            self.daily_range['date'] = current_date
            self.daily_trades = 0  # Reset daily trade count
            self.daily_loss = 0    # Reset daily loss

        return current_time >= range_mark_time and not self.daily_range['marked']

    def can_enter_trade(self):
        """Check if we can still enter trades"""
        current_time = self.get_current_time()

        entry_cutoff_str = self.time_settings['entry_cutoff_time']
        entry_cutoff = current_time.replace(
            hour=int(entry_cutoff_str.split(':')[0]),
            minute=int(entry_cutoff_str.split(':')[1]),
            second=0, microsecond=0
        )

        # Check time
        time_ok = current_time < entry_cutoff

        # Check daily trade limit
        trades_ok = self.daily_trades < self.risk_mgmt['max_daily_trades']

        # Check daily loss limit
        loss_ok = abs(self.daily_loss) < self.risk_mgmt['max_daily_loss_usd']

        return time_ok and trades_ok and loss_ok

    def get_candles(self, timeframe='5m', limit=100):
        """Fetch OHLCV candles from exchange"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert(self.timezone)
            return df
        except Exception as e:
            print(f"❌ Error fetching candles: {e}")
            return None

    def mark_daily_range(self):
        """Mark the high and low of the opening range candle"""
        try:
            range_tf = self.strategy_params['range_timeframe']
            df = self.get_candles(timeframe=range_tf, limit=10)

            if df is None or len(df) == 0:
                return False

            current_time = self.get_current_time()
            current_date = current_time.date()

            range_start_str = self.time_settings['range_start_time']
            range_hour = int(range_start_str.split(':')[0])
            range_minute = int(range_start_str.split(':')[1])

            for idx, row in df.iterrows():
                candle_time = row['timestamp']
                if (candle_time.date() == current_date and
                    candle_time.hour == range_hour and
                    candle_time.minute == range_minute):

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

            print(f"⏳ Waiting for opening range candle to close...")
            return False

        except Exception as e:
            print(f"❌ Error marking range: {e}")
            return False

    def detect_fair_value_gap(self, df):
        """Detect Fair Value Gap pattern"""
        if not self.daily_range['marked'] or len(df) < 3:
            return None

        candle1 = df.iloc[-3]
        candle2 = df.iloc[-2]
        candle3 = df.iloc[-1]

        range_high = self.daily_range['high']
        range_low = self.daily_range['low']

        # Bullish FVG
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
                    'candle1': candle1,
                    'candle2': candle2,
                    'candle3': candle3,
                    'timestamp': candle3['timestamp']
                }

        # Bearish FVG
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
                    'candle1': candle1,
                    'candle2': candle2,
                    'candle3': candle3,
                    'timestamp': candle3['timestamp']
                }

        return None

    def calculate_position_size(self, entry_price, stop_loss):
        """Calculate position size based on risk"""
        risk_amount = self.paper_balance * self.strategy_params['risk_per_trade']

        # Apply max position size limit
        max_position_usd = self.risk_mgmt['max_position_size_usd']
        risk_amount = min(risk_amount, max_position_usd)

        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            return 0

        position_size = risk_amount / risk_per_unit

        # Round to exchange precision (e.g., 0.001 BTC for Binance)
        position_size = round(position_size, 6)

        return position_size

    def create_limit_order(self, fvg):
        """Create a limit order at the FVG level"""
        if not self.can_enter_trade():
            if self.daily_trades >= self.risk_mgmt['max_daily_trades']:
                print(f"⚠️ Max daily trades reached ({self.risk_mgmt['max_daily_trades']})")
            if abs(self.daily_loss) >= self.risk_mgmt['max_daily_loss_usd']:
                print(f"⚠️ Max daily loss reached (${abs(self.daily_loss):.2f})")
            return

        if self.pending_order or self.position:
            return

        entry_price = fvg['fvg_price']

        if fvg['direction'] == 'LONG':
            stop_loss = fvg['candle1']['low'] * 0.999
        else:
            stop_loss = fvg['candle1']['high'] * 1.001

        risk = abs(entry_price - stop_loss)

        if fvg['direction'] == 'LONG':
            take_profit = entry_price + (risk * self.strategy_params['reward_ratio'])
        else:
            take_profit = entry_price - (risk * self.strategy_params['reward_ratio'])

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
        print(f"Position Size: {position_size:.6f} BTC")
        print(f"Risk: ${risk * position_size:,.2f}")
        print(f"Potential Reward: ${risk * position_size * self.strategy_params['reward_ratio']:,.2f}")
        print(f"{'='*60}\n")

    def check_limit_order_fill(self, current_price):
        """Check if pending limit order should be filled"""
        if not self.pending_order:
            return

        order = self.pending_order
        filled = False

        if order['direction'] == 'LONG':
            if current_price <= order['entry_price']:
                filled = True
        else:
            if current_price >= order['entry_price']:
                filled = True

        if filled:
            self.position = {
                'direction': order['direction'],
                'entry_price': order['entry_price'],
                'stop_loss': order['stop_loss'],
                'take_profit': order['take_profit'],
                'position_size': order['position_size'],
                'entry_time': datetime.now(self.timezone)
            }

            self.daily_trades += 1

            print(f"\n{'='*60}")
            print(f"✅ LIMIT ORDER FILLED")
            print(f"Type: {order['direction']}")
            print(f"Entry: ${order['entry_price']:,.2f}")
            print(f"Current Price: ${current_price:,.2f}")
            print(f"{'='*60}\n")

            self.pending_order = None

    def check_exit_conditions(self, current_high, current_low, current_close):
        """Check if position should be closed"""
        if not self.position:
            return

        pos = self.position
        exit_price = None
        exit_reason = None

        if pos['direction'] == 'LONG':
            if current_low <= pos['stop_loss']:
                exit_price = pos['stop_loss']
                exit_reason = 'Stop Loss'
            elif current_high >= pos['take_profit']:
                exit_price = pos['take_profit']
                exit_reason = 'Take Profit'

        else:
            if current_high >= pos['stop_loss']:
                exit_price = pos['stop_loss']
                exit_reason = 'Stop Loss'
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

        if pos['direction'] == 'LONG':
            pnl = (exit_price - pos['entry_price']) * pos['position_size']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['position_size']

        self.paper_balance += pnl
        self.daily_loss += pnl if pnl < 0 else 0

        trade = {
            'entry_time': str(pos['entry_time']),
            'exit_time': str(datetime.now(self.timezone)),
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'stop_loss': pos['stop_loss'],
            'take_profit': pos['take_profit'],
            'position_size': pos['position_size'],
            'pnl': pnl,
            'pnl_pct': (pnl / self.initial_balance) * 100,
            'reason': reason,
            'balance': self.paper_balance
        }

        self.trades_history.append(trade)

        print(f"\n{'='*60}")
        print(f"🔴 POSITION CLOSED")
        print(f"Type: {pos['direction']}")
        print(f"Entry: ${pos['entry_price']:,.2f}")
        print(f"Exit: ${exit_price:,.2f}")
        print(f"Reason: {reason}")
        print(f"P&L: ${pnl:,.2f} ({(pnl / self.initial_balance) * 100:.2f}%)")
        print(f"New Balance: ${self.paper_balance:,.2f}")
        print(f"Total Return: {((self.paper_balance - self.initial_balance) / self.initial_balance) * 100:.2f}%")
        print(f"Daily Trades: {self.daily_trades}/{self.risk_mgmt['max_daily_trades']}")
        print(f"{'='*60}\n")

        self.position = None
        self.save_log()

    def save_log(self):
        """Save trading log to file"""
        try:
            log_data = {
                'initial_balance': self.initial_balance,
                'current_balance': self.paper_balance,
                'total_pnl': self.paper_balance - self.initial_balance,
                'roi': ((self.paper_balance - self.initial_balance) / self.initial_balance) * 100,
                'total_trades': len(self.trades_history),
                'daily_trades': self.daily_trades,
                'daily_loss': self.daily_loss,
                'trades': self.trades_history
            }

            log_file = self.config['logging']['log_file']
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)

        except Exception as e:
            print(f"❌ Error saving log: {e}")

    def run(self):
        """Main bot loop"""
        print(f"✅ Bot started successfully\n")

        try:
            while True:
                current_time = self.get_current_time()

                if self.should_mark_range():
                    self.mark_daily_range()

                if not self.is_market_open_time():
                    print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Market closed. Waiting...")
                    time.sleep(300)
                    continue

                trading_tf = self.strategy_params['trading_timeframe']
                df = self.get_candles(timeframe=trading_tf, limit=20)

                if df is None or len(df) < 3:
                    print(f"⏳ Waiting for data...")
                    time.sleep(60)
                    continue

                current_candle = df.iloc[-1]
                current_price = current_candle['close']
                current_high = current_candle['high']
                current_low = current_candle['low']

                status = f"[{current_time.strftime('%H:%M:%S')}] Price: ${current_price:,.2f} | Balance: ${self.paper_balance:,.2f}"

                if self.position:
                    status += f" | Position: {self.position['direction']} @ ${self.position['entry_price']:,.2f}"
                elif self.pending_order:
                    status += f" | Pending: {self.pending_order['direction']} @ ${self.pending_order['entry_price']:,.2f}"
                else:
                    status += " | No Position"

                print(status)

                if self.pending_order:
                    self.check_limit_order_fill(current_price)

                if self.position:
                    self.check_exit_conditions(current_high, current_low, current_price)

                if not self.position and not self.pending_order and self.daily_range['marked']:
                    fvg = self.detect_fair_value_gap(df)
                    if fvg:
                        print(f"\n🔍 Fair Value Gap Detected: {fvg['type']}")
                        self.create_limit_order(fvg)

                time.sleep(60)

        except KeyboardInterrupt:
            print(f"\n\n🛑 Bot stopped by user")
            self.save_log()
        except Exception as e:
            print(f"\n❌ Error in main loop: {e}")
            import traceback
            traceback.print_exc()
            self.save_log()


if __name__ == "__main__":
    bot = RangeFVGBotLive(config_file='config_live.json')
    bot.run()
