import os 
import sys
import configr
import ccxt
import time
import threading

configs = {}
running = False

# using taker fees as all orders will be placed at market due to complications with
# limit chasing and risk of not being filled. Slippage is negligible as trade sizes will
# be low and only configs using liquid exchanges are permitted.
spot_taker_fee = 0.001 
fut_taker_fee = 0.0004
usdt_rate = 0.0003 # usdt lending rate for binance
leverage = 2 # default max leverage

def main():
    global configs 
    # load configurations
    configs = configr.setup()
    # infinite input loop
    while True:
        command = input('Enter a command (start, close, config, pos, quit): ')
        if parse_commands(command) == 0:
            break
    return 0

'''
Bad implementation to parse command line arguments. Wanted a simple way to 
loop input and command parsing to enable continuous execution of the 
script. Must be a more elegant way to do it in Python.
'''
def parse_commands(command):
    if command == 'quit' or command == 'q':
        return 0
    elif command == 'start': 
        startbot()
    elif command == 'close':
        close_all()
    elif command == 'config':
        configr.print_conf_list()
        confname = input('Enter the config name: ')
        global configs 
        configs = configr.setup(confname)
    elif command == 'pos' or command == 'positions':
        query_pos()
    else:
        print('\nERROR: Command is not recognized\n')

'''
Query and print currently open positions. Used for 'pos' command line
input. Display the relevant values.
'''
def query_pos():
    exchange = connect_xchange()
    positions = exchange.fetchPositions()
    for pos in positions:
        symb = pos['symbol']
        side = pos['side']
        notional = pos['notional']
        pnl = pos['unrealizedPnl']
        print(f'\n{side} {symb}, size: {notional}, upnl: {pnl}\n')
    return positions


'''
Connect to an exchange using the API key and secret. Was planning to implement
concurrency but didn't understand it in Python quite yet. 
'''
def connect_xchange(testnet=True):
    # connect to exchange using config info
    exchange_id = configs['exchange']
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
        'apiKey': configs['apikey'],
        'secret': configs['apisecret'],
        'timeout': 30000,
        'enableRateLimit': True,
    })
    exchange.options['createMarketBuyOrderRequiresPrice'] = False
    # use testnet
    if testnet:
        print('Testnet Active, Paper Trading Mode\n')
        exchange.set_sandbox_mode(True)
    else:
        print('Testnet Inactive, Capital Trading Mode\n')
        exchange.set_sandbox_mode(False)

    return exchange

'''
Method used to open trades in both Spot and Futures markets. 
@param exchange ccxt object used to connect to exchange
@param type long or short
@param symbol symbol of pair (i.e. BTC/USDT)
@return True if trade is opened, False otherwise
'''
def open_trade(exchange, type, symbol):
    if running:
        return False
    
    if type == 'spot':
        exchange.options['defaultType'] = 'spot'
        exchange.loadMarkets()
        if exchange.has['createMarketOrder']:
            order = exchange.createMarketBuyOrder(symbol, float(configs['size'])/2)
            print('Market Buy %s %s @%s '% order['amount'], symbol, order['average'])
            return order['status'] == 'open'
    elif type == 'future':
        exchange.options['defaultType'] = 'future'
        exchange.loadMarkets()
        market = exchange.markets[symbol]
        exchange.fapiPrivate_post_leverage({
            'symbol': market['id'],
            'leverage': configs['maxleverage'], # it will always be 2
        })
        if exchange.has['createMarketOrder']:
            order = exchange.createMarketSellOrder(symbol, float(configs['size'])/2)
            print('Market Buy %s %s @%s '% order['amount'], symbol, order['average'])
            return order['status'] == 'open'
    else:
        print('Invalid Trade Type')
        return False

'''
Method used to close trades in both Spot and Futures markets. Spot and Futures
positions are closed simultaneously so no market needs to be specified.
@param exchange ccxt object used to connect to exchange
@param type long or short
@param symbol symbol of pair (i.e. BTC/USDT)
@return True if trade is closed, False otherwise
'''
def close_trade(exchange, type, symbol):
    if not running:
        return False

    if type == 'spot':
        exchange.options['defaultType'] = 'spot'
        exchange.loadMarkets()
        if exchange.has['createMarketOrder']:
            order = exchange.create_order(symbol=symbol, type="MARKET", side="sell", 
                    amount=float(configs['size'])/2, params={"reduceOnly": True}) 
            print('Market Sell %s %s @%s '% order['amount'], symbol, order['average'])
            return order['status'] == 'closed'
    elif type == 'future':
        exchange.options['defaultType'] = 'future'
        exchange.loadMarkets()
        market = exchange.markets[symbol]
        exchange.fapiPrivate_post_leverage({
            'symbol': market['id'],
            'leverage': configs['maxleverage'], # it will always be 2
        })
        if exchange.has['createMarketOrder']:
            order = exchange.create_order(symbol=symbol, type="MARKET", side="buy", 
                    amount=float(configs['size'])/2, params={"reduceOnly": True})
            print('Market Sell %s %s @%s '% order['amount'], symbol, order['average'])
            return order['status'] == 'closed'
    else:
        print('Invalid Trade Type')
        return False
    

# Calculation for Price Index is not included as it requires price data from multiple spot exchanges
# weighted by volume, which is not practical as the mark price yields a sufficient "True" value of 
# the contract. 

''' 
Determine funding rate of a specific symbol
@param exchange object providing connection to exchange created by ccxt
@param symbol symbol of pair (i.e. BTC/USDT)
@return funding rate
'''
def funding_rate(exchange, symbol):
    # calculating future mark
    exchange.options['defaultType'] = 'future'

    # impact margin notional calculator
    def imn(price, maxlev):
        return price/(1/maxlev)

    # in practice, binance calculates premium index every minute and averages it over 
    # the funding period. the current calculation does not compute the average, as it 
    # is only a demonstration.

    # funding rate calculation may differ between exchanges but the below procedure is 
    # based on binance's funding rate calculation method.

    # impact bid/ask calculator 
    def impact_bidask(bidask):
        imn_const = imn(200, 125)
        book = exchange.fetch_order_book(symbol)[bidask]
        sumpx_qx = 0
        sumpxmin1_qxmin1 = 0
        qx = 0
        qxmin1 = 0
        count = 0
        for bidask in book:
            sumpxmin1_qxmin1 = sumpx_qx
            qxmin1 = qx
            sumpx_qx += bidask[0]*bidask[1] 
            qx += bidask[1]
            if sumpx_qx > imn_const and sumpxmin1_qxmin1 < imn_const:
                # equation for impact bid/ask price
                return imn_const/((imn_const-sumpxmin1_qxmin1)/bidask[0]+qxmin1)
    bid, ask, spread = get_bas(exchange, symbol)
    prem_index = (max(0, impact_bidask('bids')-ask) - max(0, ask-impact_bidask('asks')))/ask
    interest_rate = 0.0001
    funding = prem_index + max(0.0005, max(-0.0005, interest_rate-prem_index)) # clamp(i/r - prem_ind, 0.0005, -0.0005)

    return funding*100

'''
Method used to execute spot-perp trades.The trades are aimed to produce minimal net long 
or short exposure by simultaneously executing the trades on spot and perps. 
The threading implementation is trivial (or incomplete) as it's my first time using it.
@param exchange ccxt object used to execute trades
@param funding the funding rate calculated 
@param symbol symbol of pair (i.e. BTC/USDT)
@return string to indicate a string representation of the trade
'''
def arb_it(exchange, funding, symbol):
    global running
    if funding >= float(configs['fundinghigh']) and not running:
        temp = open_trade(exchange, 'spot', symbol)
        running = temp and open_trade(exchange, 'future', symbol)
        if running:
            return 'Long Spot, Short Perps \n'
        elif temp:
            close_trade(exchange, 'spot', symbol)
        elif not temp:
            close_trade(exchange, 'future', symbol)
        else:
            return 'Open Arbitrage Failed \n'
    elif funding <= float(configs['fundinglow']):
        temp = close_trade(exchange, 'spot', symbol)
        running = not(temp and close_trade(exchange, 'future', symbol))
        if running:
            return 'Closed Spot, Closed Perps \n'
        else:
            return 'Close Arbitrage Failed \n'
    else:
        return 'No action, Funding is in no-arb-zone \n'
    
# get bid ask spread 
def get_bas(exchange, symbol):
    exchange.load_markets()
    orderbook = exchange.fetch_order_book(symbol)
    bid = orderbook['bids'][0][0] if len (orderbook['bids']) > 0 else None
    ask = orderbook['asks'][0][0] if len (orderbook['asks']) > 0 else None
    spread = (ask - bid) if (bid and ask) else None
    return bid, ask, spread 

# loop arbitrage to use for thread
def loop_arb(exchange, funding, symbol):
    try:
        while True:
            print('Checking for arbitrage...\n')
            arb_it(exchange, funding, symbol)
            time.sleep(1800) # check arb condition every 30 mins 
    except KeyboardInterrupt:
        print('Stop checking for arbitrage...\n')
        pass

# Start the bot (scan API, check for trade condition, execute trades + output) 
def startbot():
    print('\nBot starting...')
    try:
        exchange = connect_xchange()
        print('Successfully connected to exchange\n')
    except:
        print('\nError when connecting to exchange\n')
        print('** MAKE SURE CONFIG IS RUN BEFORE YOU RUN start **\n')
    
    symbol = configs['maintoken']
    funding = funding_rate(exchange, symbol)
    
    print('Starting Arb-Loop, Ctrl-C to Stop\n')
    loop_arb(exchange, funding, symbol)

# Close all trades.
def close_all():
    print('Current Positions... \n')
    if not query_pos():
        print('No Current Positions, nothing to close')
    else:
        print('Force Closing All Positions...')
        try:
            exchange = connect_xchange()
            symbol = configs['maintoken']
            funding = funding_rate(exchange, symbol)

            close_trade(exchange, 'spot', symbol)
            close_trade(exchange, 'future', symbol)
        except:
            print('\nERROR: Attempted Force Close Failed\n')


if __name__ == '__main__':
    main()