# auto-arb
Cryptocurrency trading bot that employs a delta-neutral strategy. 

The trading bot arbitrages the contango between a crypto-asset's spot price and futures product. Specifically, this bot was implemented to arbitrage the premium between spot and perpetual futures. Instead of contango, the perpetual swaps enforce a premium using funding rates. When there exists a price where funding rates exceed a pretermined configuration of the bot, the bot automatically purchases a crypto asset on spot and simultaneously sells the respective perpetual swaps. The converse trade is not implemented as futures backwardation, or sufficiently negative funding, is often quickly self-correcting.

## Funding Rate 
The funding rates were calculated using Binance's supported documentation which can be found here

https://www.binance.com/en/support/faq/360033525031

## Price Index
The price index, a component of the funding calculation, were calculated using Binance's supported documentation which can be found here

https://www.binance.com/en/support/faq/547ba48141474ab3bddc5d7898f97928

## Margin and Leverage 
For more information about margin and leverage

https://www.binance.com/en/support/faq/360033162192

* Some parameters are fixed for the specific neutral-risk profile. 
