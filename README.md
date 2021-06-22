# auto-arb
Cryptocurrency trading bot that employs a delta-neutral strategy. 

The trading bot arbitrages the contango (if exists) between a crypto-asset's spot price and futures product. Specifically, this bot was implemented to arbitrage the premium between spot and perpetual futures. Instead of contango, the perpetual swaps enforce a premium using funding rates. When there exists a price where funding rates exceed a pretermined configuration of the bot, the bot automatically purchases a crypto asset on spot and simultaneously sells the respective perpetual swaps. The converse trade is not implemented as futures backwardation or sufficiently negative funding is often quickly self-correcting. 
