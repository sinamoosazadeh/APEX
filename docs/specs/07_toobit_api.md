Skip to content



Menu
On this page
Sidebar Navigation
Integration Guide
Introduction

Basic Information

Code Examples

Changelog

Spot
Examples

Wallet Endpoints

Market Data Endpoints

Websocket Market Streams

Spot Account/Trade

Account/Trades (v2)

User Data Streams

Error Codes

USDT-M
Examples

Market Data Endpoints

Websocket Market Streams

Account/Trades Endpoints

Account/Trades (v2)

User Data Streams

Error Codes

Copy Trading
Examples

Leader Endpoints

Follower Endpoints

Examples
For general basic information, please refer to the Basic Information documentation.

Rest API Information
All data types adopt definition in JAVA.
Websocket Information
Base Url: wss://stream.toobit.com
Rate Limits
Users who repeatedly trigger rate limits, or who continue sending requests after receiving 429, may have their IP banned (error code 418)
IP bans are tracked, and ban duration is adjusted based on repeated rate limit triggers. The duration can range from 2 minutes to 3 days
SIGNED Endpoint Examples
SIGNED Endpoint Examples for POST /api/v1/futures/order
Here is a step-by-step example of how to send a vaild signed payload from the Linux command line using echo, openssl, and curl.

Key<w:t>Value
apiKey<w:t>SRQGN9M8Sr87nbfKsaSxm33Y6CmGVtUu9Erz73g9vHFNn36VROOKSaWBQ8OSOtSq
secretKey<w:t>30lfjDT51iOG1kYZnDoLNynOyMdIcmQyO1XYfxzYOmQfx9tjiI98Pzio4uhZ0Uk2
Parameter<w:t>Value
symbol<w:t>BTC-SWAP-USDT
side<w:t>SELL
type<w:t>LIMIT
timeInForce<w:t>GTC
quantity<w:t>1
price<w:t>400
recvWindow<w:t>100000
timestamp<w:t>1668481902307
Example 1: As a query string

Example 1:
HMAC SHA256 signature:
$ echo -n "symbol=BTC-SWAP-USDT&side=SELL&type=LIMIT&timeInForce=GTC&quantity=1&price=400&recvWindow=100000&timestamp=1668481902307" | openssl dgst -sha256 -hmac "30lfjDT51iOG1kYZnDoLNynOyMdIcmQyO1XYfxzYOmQfx9tjiI98Pzio4uhZ0Uk2"
(stdin)= 8420e499e71cce4a00946db16543198b6bcae01791bdb75a06b5a7098b156468
1
2
3
4

curl command:
(HMAC SHA256)
$ curl -H "X-BB-APIKEY: SRQGN9M8Sr87nbfKsaSxm33Y6CmGVtUu9Erz73g9vHFNn36VROOKSaWBQ8OSOtSq" -X POST 'https://api.toobit.com/api/v1/futures/order' -d 'symbol=BTC-SWAP-USDT&side=SELL&type=LIMIT&timeInForce=GTC&quantity=1&price=400&recvWindow=100000&timestamp=1668481902307&signature=8420e499e71cce4a00946db16543198b6bcae01791bdb75a06b5a7098b156468'
1
2
3
queryString symbol=BTC-SWAP-USDT
&side=SELL
&type=LIMIT
&timeInForce=GTC
&quantity=1
&price=400
&recvWindow=100000
&timestamp=1668481902307
Example 2: As a request body

Example 2:
HMAC SHA256 signature:
$ echo -n "symbol=BTC-SWAP-USDT&side=SELL&type=LIMIT&timeInForce=GTC&quantity=1&price=400&recvWindow=100000&timestamp=1668481902307" | openssl dgst -sha256 -hmac "30lfjDT51iOG1kYZnDoLNynOyMdIcmQyO1XYfxzYOmQfx9tjiI98Pzio4uhZ0Uk2"
(stdin)= 8420e499e71cce4a00946db16543198b6bcae01791bdb75a06b5a7098b156468
1
2
3
4

curl command:
(HMAC SHA256)
$ curl -H "X-BB-APIKEY: SRQGN9M8Sr87nbfKsaSxm33Y6CmGVtUu9Erz73g9vHFNn36VROOKSaWBQ8OSOtSq" -X POST 'https://api.toobit.com/api/v1/spot/order' -d 'symbol=BTC-SWAP-USDT&side=SELL&type=LIMIT&timeInForce=GTC&quantity=1&price=400&recvWindow=100000&timestamp=1668481902307&signature=8420e499e71cce4a00946db16543198b6bcae01791bdb75a06b5a7098b156468'
1
2
3
requestBody symbol=BTC-SWAP-USDT
&side=SELL
&type=LIMIT
&timeInForce=GTC
&quantity=1
&price=400
&recvWindow=100000
&timestamp=1668481902307
Example 3: Mixed query string and request body
queryString: symbol=BTC-SWAP-USDT&side=SELL&type=LIMIT&timeInForce=GTC
requestBody: quantity=1&price=400&recvWindow=10000000&timestamp=1668481902307

Example 3:
HMAC SHA256 signature:
$ echo -n "symbol=BTC-SWAP-USDT&side=SELL&type=LIMIT&timeInForce=GTCquantity=1&price=400&recvWindow=10000000&timestamp=1668481902307" | openssl dgst -sha256 -hmac "30lfjDT51iOG1kYZnDoLNynOyMdIcmQyO1XYfxzYOmQfx9tjiI98Pzio4uhZ0Uk2"
(stdin)= 59ef0b2085ebb99cca5b6445c202d99add17be2d5d1861c0f4aa17bc785ac4d5
1
2
3
4

curl command:
(HMAC SHA256)
$ curl -H "X-BB-APIKEY: SRQGN9M8Sr87nbfKsaSxm33Y6CmGVtUu9Erz73g9vHFNn36VROOKSaWBQ8OSOtSq" -X POST 'https://api.toobit.com/api/v1/spot/order?symbol=BTC-SWAP-USDT&side=SELL&type=LIMIT&timeInForce=GTC' -d 'quantity=1&price=400&recvWindow=10000000&timestamp=1668481902307&signature=59ef0b2085ebb99cca5b6445c202d99add17be2d5d1861c0f4aa17bc785ac4d5'
1
2
3
Note that the signature is different in example 3.There is no & between "GTC" and "quantity=1".

Menu
On this page
Sidebar Navigation
Integration Guide
Introduction

Basic Information

Code Examples

Changelog

Spot
Examples

Wallet Endpoints

Market Data Endpoints

Websocket Market Streams

Spot Account/Trade

Account/Trades (v2)

User Data Streams

Error Codes

USDT-M
Examples

Market Data Endpoints

Websocket Market Streams

Account/Trades Endpoints

Account/Trades (v2)

User Data Streams

Error Codes

Copy Trading
Examples

Leader Endpoints

Follower Endpoints

Market Data Endpoints
Check Server Time
GET /api/v1/time
Test connectivity to the Rest API and get the current server time.

Weight: 1
Parameters:
NONE

Response:


{
  "serverTime": 1538323200000
}
1
2
3
Exchange Information
GET /api/v1/exchangeInfo
Current exchange trading rules and symbol information

Important Notice

The rateLimits field in the response will be removed in future iterations. A new endpoint will be provided to retrieve rate limit information. Please do not rely on this field.

Weight：1
Parameters：
NONE

Response


{
  "timezone": "UTC",
  "brokerFilters": [],
  "symbols": [ // spot symbols
    {
      "filters":[
          {
              "minPrice":"0.01",
              "maxPrice":"100000.00000000",
              "tickSize":"0.01",
              "filterType":"PRICE_FILTER"
          },
          {
              "minQty":"0.0001", // min trade quantity
              "maxQty":"4000", // max trade quantity
              "stepSize":"0.0001",
              "filterType":"LOT_SIZE"
          },
          {
              "minNotional":"10",
              "filterType":"MIN_NOTIONAL"
          },
              {
              "minAmount": "10", // minimum transaction amount
              "maxAmount": "6600000", // maximum trade amount
              "minBuyPrice": "0.01", // minimum buy price
              "filterType": "TRADE_AMOUNT" 
          },
          {
              "maxSellPrice": "999999999", // limit max sell price
              "buyPriceUpRate": "0.1", // maximum sell price
              "sellPriceDownRate": "0.1", // maximum sell price
              "sellPriceDownRate": "0.1", // the maximum sell price of the limit
              "maxEntrustNum": "100000", // the maximum number of orders (contracts)
              "maxConditionNum": "100000", // maximum number of condition orders (contracts)
              "filterType": "LIMIT_TRADING"
          },
          {
              "buyPriceUpRate": "0.1", // Buy cannot be higher than 10% of the marked (contract)/latest (spot) price
              "sellPriceDownRate": "0.1", // Sell cannot be less than 10% of the marked (contract)/latest (spot) price
              "filterType": "MARKET_TRADING"
          },
          {
              "noAllowMarketStartTime": "0", // Market order start time is not allowed 
              "noAllowMarketEndTime": "0", // Do not allow the market order end time
              "limitOrderStartTime": "0", // the start time of a limit order
              "limitOrderEndTime": "0", // Limit order end time
              "limitMinPrice": "0", // the minimum price of a limit order
              "limitMaxPrice": "0", // the maximum price of the limit order
              "filterType": "OPEN_QUOTE"
          }
      ], 
      "exchangeId": "301",
      "symbol": "ETHUSDT",
      "symbolName": "ETHUSDT",
      "status": "TRADING",
      "baseAsset": "ETH",
      "baseAssetName": "ETH",
      "baseAssetPrecision": "0.0001",
      "quoteAsset": "USDT",
      "quoteAssetName": "USDT",
      "quotePrecision": "0.01",
      "icebergAllowed": false,
      "isAggregate": false,
      "allowMargin": true
    }
  ],
  "rateLimits": [ // Note: This field will be removed in future iterations. A new endpoint will be provided to retrieve rate limit information
    {
      "rateLimitType": "REQUEST_WEIGHT",
      "interval": "MINUTE",
      "intervalUnit": 1,
      "limit": 3000
    },
    {
      "rateLimitType": "ORDERS",
      "interval": "SECOND",
      "intervalUnit": 2,
      "limit": 60
    }
  ],
  "options": [],
  "contracts": [ // Futures(contracts) symbols
    {
      "filters":[
          {
              "minPrice":"0.01",
              "maxPrice":"100000.00000000",
              "tickSize":"0.01",
              "filterType":"PRICE_FILTER"
          },
          {
              "minQty":"0.0001", // min trade quantity, token quantity not contracts
              "maxQty":"4000", // max trade quantity, token quantity not contracts
              "stepSize":"0.0001",
              "filterType":"LOT_SIZE"
          },
          {
              "minNotional":"10",
              "filterType":"MIN_NOTIONAL"
          },
              {
              "minAmount": "10", // minimum transaction amount
              "maxAmount": "6600000", // maximum trade amount
              "minBuyPrice": "0.01", // minimum buy price
              "filterType": "TRADE_AMOUNT" 
          },
          {
              "maxSellPrice": "999999999", // limit max sell price
              "buyPriceUpRate": "0.1", // maximum sell price
              "sellPriceDownRate": "0.1", // maximum sell price
              "sellPriceDownRate": "0.1", // the maximum sell price of the limit
              "maxEntrustNum": "100000", // the maximum number of orders (contracts)
              "maxConditionNum": "100000", // maximum number of condition orders (contracts)
              "filterType": "LIMIT_TRADING"
          },
          {
              "buyPriceUpRate": "0.1", // Buy cannot be higher than 10% of the marked (contract)/latest (spot) price
              "sellPriceDownRate": "0.1", // Sell cannot be less than 10% of the marked (contract)/latest (spot) price
              "filterType": "MARKET_TRADING"
          },
          {
              "noAllowMarketStartTime": "0", // Market order start time is not allowed 
              "noAllowMarketEndTime": "0", // Do not allow the market order end time
              "limitOrderStartTime": "0", // the start time of a limit order
              "limitOrderEndTime": "0", // Limit order end time
              "limitMinPrice": "0", // the minimum price of a limit order
              "limitMaxPrice": "0", // the maximum price of the limit order
              "filterType": "OPEN_QUOTE"
          }
      ], 
      "exchangeId": "301",
      "symbol": "BTC-SWAP-USDT",
      "symbolName": "BTC-SWAP-USDTUSDT",
      "status": "TRADING",
      "baseAsset": "BTC-SWAP-USDT",
      "baseAssetPrecision": "1",
      "quoteAsset": "USDT",
      "quoteAssetPrecision": "0.1",
      "icebergAllowed": false,
      "inverse": false,
      "index": "BTCUSDT",
      "marginToken": "USDT",
      "marginPrecision": "0.0001",
      "contractMultiplier": "0.0001",
      "underlying": "BTC",
      "riskLimits": [
        {
          "riskLimitId": "200000133",
          "quantity": "1000000.0",
          "initialMargin": "0.01",
          "maintMargin": "0.005"
        },
        {
          "riskLimitId": "200000134",
          "quantity": "2000000.0",
          "initialMargin": "0.02",
          "maintMargin": "0.01"
        },
        {
          "riskLimitId": "200000135",
          "quantity": "3000000.0",
          "initialMargin": "0.03",
          "maintMargin": "0.015"
        },
        {
          "riskLimitId": "200000136",
          "quantity": "4000000.0",
          "initialMargin": "0.04",
          "maintMargin": "0.02"
        }
      ],
      "categories": ["New", "TradFi"] // Contract categories, English names; empty array when no category, multiple when belongs to multiple categories
    },
    {
      "filters":[
          {
              "minPrice":"0.01",
              "maxPrice":"100000.00000000",
              "tickSize":"0.01",
              "filterType":"PRICE_FILTER"
          },
          {
              "minQty":"0.0001",
              "maxQty":"4000",
              "stepSize":"0.0001",
              "filterType":"LOT_SIZE"
          },
          {
              "minNotional":"10",
              "filterType":"MIN_NOTIONAL"
          },
              {
              "minAmount": "10", // minimum transaction amount
              "maxAmount": "6600000", // maximum trade amount
              "minBuyPrice": "0.01", // minimum buy price
              "filterType": "TRADE_AMOUNT" 
          },
          {
              "maxSellPrice": "999999999", // limit max sell price
              "buyPriceUpRate": "0.1", // maximum sell price
              "sellPriceDownRate": "0.1", // maximum sell price
              "sellPriceDownRate": "0.1", // the maximum sell price of the limit
              "maxEntrustNum": "100000", // the maximum number of orders (contracts)
              "maxConditionNum": "100000", // maximum number of condition orders (contracts)
              "filterType": "LIMIT_TRADING"
          },
          {
              "buyPriceUpRate": "0.1", // Buy cannot be higher than 10% of the marked (contract)/latest (spot) price
              "sellPriceDownRate": "0.1", // Sell cannot be less than 10% of the marked (contract)/latest (spot) price
              "filterType": "MARKET_TRADING"
          },
          {
              "noAllowMarketStartTime": "0", // Market order start time is not allowed 
              "noAllowMarketEndTime": "0", // Do not allow the market order end time
              "limitOrderStartTime": "0", // the start time of a limit order
              "limitOrderEndTime": "0", // Limit order end time
              "limitMinPrice": "0", // the minimum price of a limit order
              "limitMaxPrice": "0", // the maximum price of the limit order
              "filterType": "OPEN_QUOTE"
          }
      ], 
      "exchangeId": "301",
      "symbol": "BTC-SWAP",
      "symbolName": "BTC-SWAP",
      "status": "TRADING",
      "baseAsset": "BTC-SWAP",
      "baseAssetPrecision": "1",
      "quoteAsset": "USDT",
      "quoteAssetPrecision": "0.1",
      "icebergAllowed": false,
      "inverse": true,
      "index": "BTCUSDT",
      "marginToken": "BTC",
      "marginPrecision": "0.00000001",
      "contractMultiplier": "1.0",
      "underlying": "BTC",
      "riskLimits": [
        {
          "riskLimitId": "200000137",
          "quantity": "1000000.0",
          "initialMargin": "0.01",
          "maintMargin": "0.005"
        },
        {
          "riskLimitId": "200000138",
          "quantity": "2000000.0",
          "initialMargin": "0.02",
          "maintMargin": "0.01"
        },
        {
          "riskLimitId": "200000139",
          "quantity": "3000000.0",
          "initialMargin": "0.03",
          "maintMargin": "0.015"
        },
        {
          "riskLimitId": "200000140",
          "quantity": "4000000.0",
          "initialMargin": "0.04",
          "maintMargin": "0.02"
        }
      ],
      "categories": ["New", "TradFi"] // Contract categories, English names; empty array when no category, multiple when belongs to multiple categories
    }
  ],
  "coins": [
    {
      "orgId": "9001",
      "coinId": "ETH",
      "coinName": "ETH",
      "coinFullName (tokenFullName)": "Ethereum",
      "allowWithdraw": true,
      "allowDeposit": true,
      "chainTypes": []
    },
    {
      "orgId": "9001",
      "coinId": "USDT",
      "coinName": "USDT",
      "coinFullName (tokenFullName)": "TetherUS",
      "allowWithdraw": true,
      "allowDeposit": true,
      "chainTypes": [
        {
          "chainType": "ERC20",
          "withdrawFee": "0.1",
          "minWithdrawQuantity": "10",
          "maxWithdrawQuantity": "1000",
          "minDepositQuantity": "1",
          "allowDeposit": true,
          "allowWithdraw": true
        },
        {
          "chainType": "TRC20",
          "withdrawFee": "0.1",
          "minWithdrawQuantity": "10",
          "maxWithdrawQuantity": "1000",
          "allowDeposit": true,
          "allowWithdraw": true
        },
        {
          "chainType": "OMNI",
          "withdrawFee": "0.1",
          "minWithdrawQuantity": "10",
          "maxWithdrawQuantity": "1000",
          "allowDeposit": true,
          "allowWithdraw": true
        }
      ]
    },
    {
      "orgId": "9001",
      "coinId": "BTC",
      "coinName": "BTC",
      "coinFullName": "Bitcoin",
      "allowWithdraw": false,
      "allowDeposit": false,
      "chainTypes": []
    },
    {
      "orgId": "9001",
      "coinId": "UNI",
      "coinName": "UNI",
      "coinFullName": "uniswap",
      "allowWithdraw": false,
      "allowDeposit": false,
      "chainTypes": []
    },
    {
      "orgId": "9001",
      "coinId": "XRP",
      "coinName": "XRP",
      "coinFullName (tokenFullName)": "XRP",
      "allowWithdraw": false,
      "allowDeposit": false,
      "chainTypes": []
    },
    {
      "orgId": "9001",
      "coinId": "EOS",
      "coinName": "EOS1",
      "coinFullName (tokenFullName)": "EOS",
      "allowWithdraw": true,
      "allowDeposit": true,
      "chainTypes": []
    },
    {
      "orgId": "9001",
      "coinId": "JET",
      "coinName": "JET",
      "coinFullName (tokenFullName)": "JET",
      "allowWithdraw": false,
      "allowDeposit": false,
      "chainTypes": []
    }
  ]
}

status Field Description:

For spot trading pairs (pairs in the symbols array), possible values of status:

Status Value<w:t>Description
TRADING<w:t>Trading
ONLINE<w:t>Online (not tradable)
OFFLINE<w:t>Offline (trading pair has been delisted)
API_TRADE_FORBIDDEN<w:t>API trading forbidden (trading via API is prohibited)
For contract trading pairs (pairs in the contracts array), possible values of status:

Status Value<w:t>Description
TRADING<w:t>Trading
ONLINE<w:t>Online (not tradable)
API_TRADE_FORBIDDEN<w:t>API trading forbidden (trading via API is prohibited)
OPEN_FORBIDDEN<w:t>Opening forbidden (opening positions is forbidden, but closing is allowed)
CLOSE_FORBIDDEN<w:t>Closing forbidden (closing positions is forbidden, but opening is allowed)
Order Book
GET /quote/v1/depth
Weight:
Adjusted based on the limit:

Limit<w:t>Weight
5, 10, 20, 50, 100<w:t>1
500<w:t>5
1000<w:t>10
Response：


{
  "t": 1768300458706,//Matching time
  "b": [
    [
      "3.90000000",   // price
      "431.00000000"  // quantity
    ],
    [
      "4.00000000",
      "431.00000000"
    ]
  ],
  "a": [
    [
      "4.00000200",  // price
      "12.00000000"  // quantity
    ],
    [
      "5.10000000",
      "28.00000000"
    ]
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
limit<w:t>INT<w:t>NO<w:t>Default 100;
Notes：If limit=0 is set, a lot of data will be returned.

Merge Depth
GET /quote/v1/depth/merged
Merged deep interface.

Weight：1
Response


{
    "t": 1672035413265,//time
    "b": [//Buy Depth High to Low
        [
            "16851.95",//price
            "0.003321"//quantity
        ],
        [
            "16851.87",
            "0.005456"
        ],
        [
            "16851.47",
            "0.002219"
        ]
    ],
    "a": [//Sell Depth Low to High
        [
            "16870.19",
            "0.003838"
        ],
        [
            "16873.05",
            "0.00361"
        ],
        [
            "16873.06",
            "0.002623"
        ]
    ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
scale<w:t>INT<w:t>NO<w:t>Gears: 0,1,2,3,4,5 For example: 0means gear 1, 1 means gear 2
limit<w:t>INT<w:t>NO
Recent Trades List
GET /quote/v1/trades
Get recent market trades

Weight：1
Response：


[
  {
    "p": "4.00000100",
    "q": "12.00000000",
    "t": 1499865549590,
    "ibm": true  // Transaction direction isBuyerMaker
  }
]
1
2
3
4
5
6
7
8
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
limit<w:t>INT<w:t>NO<w:t>Default 60; Max 60
Kline/Candlestick Data
GET /quote/v1/klines
Kline/candlestick bars for a symbol. Klines are uniquely identified by their open time.

Weight：1
Response：


[
  [
    1499040000000,      // Open time
    "0.01634790",       // Open price
    "0.80000000",       // High price
    "0.01575800",       // Low price
    "0.01577100",       // Close price
    "148976.11427815",  // Volume
    1499644799999,      // Close time
    "2434.19055334",    // Quote asset volume
    308,                //  Number of trades
    "1756.87402397",    // Taker buy base asset volume
    "28.46694368"       // Taker buy quote asset volume
  ]
]
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
interval<w:t>ENUM<w:t>YES<w:t>interval
startTime<w:t>LONG<w:t>NO<w:t>start timestamp
endTime<w:t>LONG<w:t>NO<w:t>en d timestamp
limit<w:t>INT<w:t>NO<w:t>Default 1000; Max 1000
Notes: If startTime and endTime are not sent, only the latest K line will be returned.

Index Price Kline/Candlestick Data
GET /quote/v1/index/klines
Kline/candlestick bars for the index price of a pair.

Response：


{
    "code": 200,
    "data": [
        {
            "t": 1669155300000,//time
            "s": "BTCUSDT",// symbol
            "sn": "BTCUSDT",//symbol name
            "c": "1127.1",//Close price
            "h": "1130.81",//High price
            "l": "1126.17",//Low price
            "o": "1130.8",//Open price
            "v": "0",//Volume
            "st": 1669156800000 //interface response time
        },
        {
            "t": 1669156200000,
            "s": "ETHUSDT",
            "sn": "ETHUSDT",
            "c": "1129.44",
            "h": "1129.54",
            "l": "1127.1",
            "o": "1127.1",
            "v": "0",
            "st": 1669156800000
        }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
interval<w:t>ENUM<w:t>YES<w:t>interval
from<w:t>LONG<w:t>YES<w:t>start timestamp
to<w:t>LONG<w:t>YES<w:t>end timestamp
limit<w:t>INT<w:t>NO<w:t>limit, DEFAULT:2000 MAX:2000
Get Index Price Components
GET /quote/v1/indexPriceComponents
get the index components of one symbol

Response：


{
  "index": "91429.02891304", //Last price of the index
  "edp": "91408.35002101", //last 10 minutes average index price
  "components": [
    {
      "exchange": "BITGET", //Name of the exchange
      "spotPair": "BTCUSDT",//Spot trading pair on the exchange (e.g., BTCUSDT)
      "weight": "1.0" //Weight in the index calculation
    },
    {
      "exchange": "KUCOIN",
      "spotPair": "BTCUSDT",
      "weight": "1.0"
    },
    {
      "exchange": "COINBASE",
      "spotPair": "BTCUSDT",
      "weight": "1.0"
    },
    {
      "exchange": "MEXC",
      "spotPair": "BTCUSDT",
      "weight": "1.0"
    },
    {
      "exchange": "BYBIT",
      "spotPair": "BTCUSDT",
      "weight": "1.0"
    },
    {
      "exchange": "OKEX",
      "spotPair": "BTCUSDT",
      "weight": "1.0"
    },
    {
      "exchange": "BINANCE",
      "spotPair": "BTCUSDT",
      "weight": "1.0"
    }
  ],
  "time": 1768277194000 //Timestamp of the last update in milliseconds
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>Index name, like BTCUSDT
Mark Price Kline/Candlestick Data
GET /quote/v1/markPrice/klines
Kline/candlestick bars for the mark price of a symbol.

Response：


{
    "code": 200,
    "data": [
        {
            "symbol": "BTC-SWAP-USDT",// Symbol
            "time": 1670157900000,// time
            "low": "16991.14096",//Low price
            "open": "16991.78288",//Open price
            "high": "16996.30641",// High prce
            "close": "16996.30641",// Close price
            "volume": "0",// Volume
            "curId": 1670157900000,
            "klineType": "1m", // kline type,such as 1m,5m....
            "change": "0.0008" //(index price-mark price)/mark price
        }
    ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
interval<w:t>ENUM<w:t>YES<w:t>interval
from<w:t>LONG<w:t>YES<w:t>start timestamp
to<w:t>LONG<w:t>YES<w:t>end timestamp
limit<w:t>INT<w:t>NO<w:t>limit,DEFAULT 2000 MAX 2000
Mark Price
GET /quote/v1/markPrice
Returns the mark price. With symbol, the response is a single JSON object for that symbol. Without symbol, the response is a JSON array of all currently available mark prices.

Rate limit: up to 5 requests per second.

With symbol:


{
  "exchangeId": 301,
  "symbolId": "BTC-SWAP-USDT",
  "price": "17042.54471",
  "time": 1670897454000
}
1
2
3
4
5
6
Without symbol (array of objects with the same fields):


[
  {
    "exchangeId": 301,
    "symbolId": "BTC-SWAP-USDT",
    "price": "17042.54471",
    "time": 1670897454000
  }
]
1
2
3
4
5
6
7
8
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>NO<w:t>Symbol; omit to return the full list
Funding Rate
GET /api/v1/futures/fundingRate
Response：


[
    {
        "symbol": "BTC-SWAP-USDT",
        "rate": "0.0018099173553719",
        "period": "8H",
        "nextFundingTime": "1668427200000",
        "interest": "0.0001",
        "fundingRateCap": "0.003",
        "fundingRateFloor": "-0.003"
    }
]
1
2
3
4
5
6
7
8
9
10
11
Field<w:t>Type<w:t>Description
symbol<w:t>STRING<w:t>Symbol
rate<w:t>STRING<w:t>Current funding rate
period<w:t>STRING<w:t>Funding settlement period (e.g. 8H)
nextFundingTime<w:t>STRING<w:t>Next funding settlement time (ms timestamp)
interest<w:t>STRING<w:t>Interest rate (base)
fundingRateCap<w:t>STRING<w:t>Current funding rate cap
fundingRateFloor<w:t>STRING<w:t>Current funding rate floor
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>NO<w:t>symbol
Get Funding Rate History
GET /api/v1/futures/historyFundingRate
Response：


[
  { 
    "id": "3434343434343",
    "symbol": "BTC-SWAP-USDT", // Symbol
    "settleTime": "1570708800000", // Funding rate settlement time
    "settleRate": "0.00321", // Funding rate
    "period": "8H" // Funding rate settlement period
  }
]
1
2
3
4
5
6
7
8
9
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
fromId<w:t>LONG<w:t>NO<w:t>start id
endId<w:t>LONG<w:t>NO<w:t>end id
limit<w:t>INT<w:t>NO<w:t>Default 20 Min 1 Max 1000
Get Open Interest
GET /quote/v1/openInterest
Get the total positions of a certain trading pair on the platform

Response：


{
  "openInterestList": [
    {
      "size": "88059.96", //Total open interest of the platform Specific coins, eg.: ETH in ETHUSDT
      "symbol": "ETH-SWAP-USDT" //Trading pair name
    }
  ]
}
1
2
3
4
5
6
7
8
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
Long/Short Ratio
GET /quote/v1/globalLongShortAccountRatio
Query symbol Long/Short Ratio

Response：


[
  {
    "symbol": "BTC-SWAP-USDT",
    "timeStamp": 1768271400000,
    "longShortRatio": "2.7432", // long/short account num ratio of all traders
    "longAccount": "0.7329", //long account num ratio of all traders
    "shortAccount": "0.2671" // short account num ratio of all traders
  }
]
1
2
3
4
5
6
7
8
9
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
period<w:t>STRING<w:t>YES<w:t>"5m","15m","30m","1h","2h","4h","6h","12h","1d"
limit<w:t>LONG<w:t>NO<w:t>default 30, max 500
startTime<w:t>LONG<w:t>NO
endTime<w:t>LONG<w:t>NO
note：If startTime and endTime are not sent, the most recent data is returned. Only the data of the latest 30 days is availab

Get Insurance fund
GET /api/v1/futures/insuranceBySymbol
query the insurance fund balance of a certain trading pair

Response：


{
  "list": [
    {
      "coin": "USDT", //Coin
      "symbol": "BTC-SWAP-USDT", //contracts symbol
      "value": "4271010.26212436", //USD value
      "updateTime": "1768262400000" //Data updated time (ms)
    },
    {
      "coin": "USDT",
      "symbol": "BTC-SWAP-USDT",
      "value": "4271013.74008353",
      "updateTime": "1768176000000"
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
Data updated time (ms)
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
note：The system returns 14 days of data by default, updated daily at 00:00 UTC.

Get All Risk Limit Configuration List
GET /api/v1/futures/riskLimits
Get all risk limit configuration list for the specified trading pair (only returns non-whitelist risk limits).

Weight：1
Response：


[
  {
    "level": 1, // Risk level, sorted by quantity, starting level is 1
    "quantity": "1000000.0", // Quantity
    "maintainMargin": "0.005", // Maintenance margin rate
    "initialMargin": "0.01", // Initial margin rate
    "maxLeverage": 100 // Maximum leverage
  },
  {
    "level": 2,
    "quantity": "2000000.0",
    "maintainMargin": "0.01",
    "initialMargin": "0.02",
    "maxLeverage": 50
  }
]
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>Trading pair
24hr Ticker Price Change Statistics
GET /quote/v1/contract/ticker/24hr
24 hour rolling window price change statistics. Careful when accessing this with no symbol.

Weight：
1 for a single symbol; 40 when the symbol parameter is omitted

Response：


[
    {
        "t": 1538725500422,   // time
        "a": "1.10000000",    // highest selling price
        "b": "1.00000000",    // highest bid
        "s": "BTC-SWAP-USDT", // symbol 
        "c": "4.00000200",    // latest transaction price
        "o": "99.00000000",   // open price
        "h": "100.00000000",  // high price 
        "l": "0.10000000",    // low price
        "v": "8913.30000000", // Base asset volume
        "qv": "15.30000000",   // otal trade volume (in quote asset)
        "pc": "15.30000000",   // priceChange
        "pcp": "15.30000000"   // priceChangePercent
    }
]
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>NO<w:t>symbol
realtimeInterval<w:t>ENUM<w:t>NO<w:t>24h,1d,1d+8
If the symbol is not sent, tickers for all symbols will be returned in an array.
Symbol Price Ticker
GET /quote/v1/contract/ticker/price
Latest price for a symbol or symbols.

Weight：1
Response：


[
  {
    "s": "BTC-SWAP-USDT",  // Symbol
    "p": "4.00000200"  // Latest price
  }
]
1
2
3
4
5
6
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>NO<w:t>symbol
If the symbol is not sent, tickers for all symbols will be returned in an array.
Symbol Index Price
GET /quote/v1/index
Index price for a symbol or symbols.

Weight：1
Response：


{
    "index":{
        "BTCUSDT":"42999.21"  // index price
    },
    "edp":{
        "BTCUSDT":"43031.36006" // Average of indices over 10 minutes
    }
}
1
2
3
4
5
6
7
8
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>NO<w:t>symbol
If the symbol is not sent, tickers for all symbols will be returned in an array.
Symbol Order Book Ticker
GET /quote/v1/contract/ticker/bookTicker
Best price/qty on the order book for a symbol or symbols.

Weight：1
Response：


[
  {
      "t": 1535975085052,     // Time
      "s": "BTC-SWAP-USDT",     // Symbol         
      "b": "4.00000000",        // bidPrice
      "bq": "431.00000000",     // bidQty
      "a": "4.00000200",        // askPrice
      "aq": "9.00000000"        // askQty
  }
]
1
2
3
4
5
6
7
8
9
10
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>NO<w:t>symbol
If the symbol is not sent, bookTickers for all symbols will be returned in an array.
Last updated: 6/9/26, 1:14 PM

Pager
Previous page
Examples
Next page
Websocket Market Streams
=============================================================================



=============================================================================

=============================================================================
Skip to content



Menu
On this page
Sidebar Navigation
Integration Guide
Introduction

Basic Information

Code Examples

Changelog

Spot
Examples

Wallet Endpoints

Market Data Endpoints

Websocket Market Streams

Spot Account/Trade

Account/Trades (v2)

User Data Streams

Error Codes

USDT-M
Examples

Market Data Endpoints

Websocket Market Streams

Account/Trades Endpoints

Account/Trades (v2)

User Data Streams

Error Codes

Copy Trading
Examples

Leader Endpoints

Follower Endpoints

Websocket Market Streams
The base endpoint is: wss://stream.toobit.com
The URL format for direct access is: wss://#HOST/quote/ws/v1
Live Subscribing/Unsubscribing to streams
The following data can be sent via websocket to implement subscription or unsubscription data stream.
Name<w:t>Value
topic<w:t>realtimes, trade, kline_$interval, depth
event<w:t>sub, cancel, cancel_all
interval<w:t>1m, 5m, 15m, 30m, 1h, 2h, 6h, 12h, 1d, 1w, 1M
Subscribe to a stream Request:

{
  "symbol": "$symbol0, $symbol1",
  "topic": "$topic",
  "event": "sub",
  "params": {
    "limit": "$limit",
    "binary": "false"
  }
}
1
2
3
4
5
6
7
8
9
Unsubscribe to a stream Request:

{
  "symbol": "$symbol0, $symbol1",
  "topic": "$topic",
  "event": "cancel",
  "params": {
    "limit": "$limit",
    "binary": "false"
  }
}
1
2
3
4
5
6
7
8
9
Heartbeat
Every once in a while, the client needs to send a ping frame, and the server will reply with a pong frame, otherwise the server will actively disconnect within 5 minutes.

Request

{
  "ping": 1535975085052
}
1
2
3
Response：


{
  "pong": 1535975085052
}
1
2
3
Latest Contract Price Stream
Push the information of each transaction transaction by transaction. A deal, or the definition of a transaction, is that there is only one taker and one maker trading with each other. After successfully connecting to the server, the server will first push a recent 60 transactions. After this push, each push is a real-time transaction. The variable "v" can be understood as a transaction ID. This variable is globally incremented and unique. For example: Suppose there have been 3 transactions in the past 5 seconds, namely ETH-SWAP-USDT, BTC-SWAP-USDT, DOGE-SWAP-USDT. Their "v" will be consecutive values (112, 113, 114).

Payload


{
    "symbol": "BTC-SWAP-USDT",
    "symbolName": "BTC-SWAP-USDTUSDT",
    "topic": "trade",
    "params": {
        "realtimeInterval": "24h",
        "binary": "false"
    },
    "data": [
        {
            "v": "1291465821801168896", // Volume
            "t": 1668690723096, // time
            "p": "399", // price
            "q": "1", // quantity
            "m": false // true = buy, false = sell
        },
        {
            "v": "1291465842546196481",
            "t": 1668690725569,
            "p": "399",
            "q": "1",
            "m": false
        }
    ],
    "f": true, // is it the first to return
    "sendTime": 1668753154192
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
Request:

{
  "symbol": "$symbol0, $symbol1",// Symbol
  "topic": "trade",
  "event": "sub",
  "params": {
    "binary": false // Whether data returned is in binary format
  }
}
1
2
3
4
5
6
7
8
Mark Price Stream
Contract mark price.

Payload


{
    "symbol": "BTC-SWAP-USDT",
    "symbolName": "BTC-SWAP-USDT",
    "topic": "markPrice",
    "params": {
        "realtimeInterval": "24h"
    },
    "data": [
        {
            "symbol": "BTC-SWAP-USDT",//symbol
            "markPrice": "16792.28",// mark price 
            "time": 1668754084000
        }
    ],
    "f": false,
    "sendTime": 1668754084738
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
Request:

{
  "symbol": "$symbol0, $symbol1", //Symbol
  "topic": "markPrice",
  "event": "sub"
}
1
2
3
4
5
Kline/Candlestick Streams
The K-line stream pushes the update of the requested K-line type (the latest K-line) every second.

Payload


{
    "symbol": "BTC-SWAP-USDT",
    "symbolName": "BTC-SWAP-USDTUSDT",
    "topic": "kline",
    "params": {
        "realtimeInterval": "24h",
        "klineType": "1m",
        "binary": "false"
    },
    "data": [
        {
            "t": 1668753840000,// start timestamp
            "s": "BTC-SWAP-USDT",// symbol
            "sn": "BTC-SWAP-USDTUSDT",// symbol name
            "c": "445",//close price
            "h": "445",//high price
            "l": "445",//low price
            "o": "445",//open price
            "v": "0"// volume
        }
    ],
    "f": true,
    "sendTime": 1668753854576
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
Request:

{
  "symbol": "$symbol0, $symbol1",// symbol
  "topic": "kline_"+$interval,
  "event": "sub",
  "params": {
    "binary": false
  }
}
1
2
3
4
5
6
7
8
K线/Kline/Candlestick chart intervals:
To subscribe to Kline, you need to provide an interval parameter, the shortest is the minute line, and the longest is the monthly line. The following intervals are supported: m -> minutes; h -> hours; d -> days; w -> weeks; M -> months

1m
5m
15m
30m
1h
2h
4h
6h
12h
1d
1w
1M
Individual Symbol Ticker Streams
24-hour complete ticker information refreshed second by symbol.

Payload


{
    "symbol": "BTC-SWAP-USDT",
    "symbolName": "BTC-SWAP-USDTUSDT",
    "topic": "realtimes",
    "params": {
        "realtimeInterval": "24h",
        "binary": "false"
    },
    "data": [
        {
            "t": 1668753480049, //time
            "s": "BTC-SWAP-USDT", //symbol
            "sn": "BTC-SWAP-USDTUSDT", // symbol name
            "c": "445", // close price
            "h": "445", //high price
            "l": "310", //low price
            "o": "311", //open price
            "v": "3747.7597191", // Total traded base asset volume
            "qv": "1426443.9553995", // Total traded quote asset volume
            "m": "0.4309", // margin
            "e": 301 // fixed value
        }
    ],
    "f": true, 
    "sendTime": 1668753481048
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
Request:

{
  "symbol": "$symbol0, $symbol1",// symbol
  "topic": "realtimes",
  "event": "sub",
  "params": {
    "binary": false
  }
}
1
2
3
4
5
6
7
8
All Market Tickers Streams
24hr rolling window ticker statistics for all symbols.

Payload


{
  "topic": "wholeRealTime", //topic
  "params": {
    "realtimeInterval": "24h",
    "binary": "false"
  },
  "data": {
    "e": "24hrTicker", //Event type
    "E": 1768249147338, //Event time
    "s": "ARC_SOL_ONCHAINUSDT", // Symbol
    "o": "0.0474", // Open price
    "h": "0.0522", // High price
    "l": "0.0467", // Low price
    "c": "0.0497", // Last price
    "v": "2299", // Total traded base asset volume
    "qv": "0", // Total traded quote asset volume
    "P": "0.0485", // Price change ratio
    "p": "0.0023", //Price change
    "ltv": "1" //quote volume of the last trade
  },
  "f": false,//is the first time to push
  "sendTime": 1768249147338 //push time
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
Request:

{
  "topic":"wholeRealTime","event": "sub"
}
1
2
3
Symbol Index Price
symbol index price

Payload


{
    "symbol": "BTCUSDT",  // symbol
    "symbolName": "BTCUSDT", // symbolName
    "topic": "index",
    "data": [
        {
            "symbol": "BTCUSDT",  // symbol
            "index": "42992.432", // index price
            "edp": "43000.95379", // average of indices over 10 minutes
            "formula": "OKEX.BTCUSDT*1.0,KUCOIN.BTCUSDT*1.0,BINANCE.BTCUSDT*1.0,BITGET.BTCUSDT*1.0,COINBASE.BTCUSDT*1.0,BYBIT.BTCUSDT*1.0",// weighted average formula
            "time": 1703692663000  // time
        }
    ],
    "f": false,
    "sendTime": 1703692664103
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
Request:

{
  "id":"index",
  "topic":"index",
  "event":"sub",
  "symbol":"BTCUSDT",
  "params": {
    "reduceSerial":true, // less serialization, faster push
    "binary":true,  // compression or not
    "limit":1500  // limit
  }
}
1
2
3
4
5
6
7
8
9
10
11
Partial Book Depth Streams
Payload


{
  "symbol": "BTC-SWAP-USDT",
  "topic": "depth",
  "data": [{
    "s": "BTC-SWAP-USDT", //Symbol
    "t": 1565600357643, //time
    "v": "112801745_18", // Version number _18, where 18 indicates 18-bit precision. Version numbers are not guaranteed to be unique, but data from close dates will definitely be different.
    "b": [ //Bids
      ["11371.49", "0.0014"], //[price, quantity]
      ["11371.12", "0.2"],
      ["11369.97", "0.3523"],
      ["11369.96", "0.5"],
      ["11369.95", "0.0934"],
      ["11369.94", "1.6809"],
      ["11369.6", "0.0047"],
      ["11369.17", "0.3"],
      ["11369.16", "0.2"],
      ["11369.04", "1.3203"]
    ],
    "a": [//Asks
      ["11375.41", "0.0053"], //[price, quantity]
      ["11375.42", "0.0043"],
      ["11375.48", "0.0052"],
      ["11375.58", "0.0541"],
      ["11375.7", "0.0386"],
      ["11375.71", "2"],
      ["11377", "2.0691"],
      ["11377.01", "0.0167"],
      ["11377.12", "1.5"],
      ["11377.61", "0.3"]
    ]
  }],
  "f": true
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
Request:

{
  "symbol": "$symbol0, $symbol1",// symbol
  "topic": "depth",
  "event": "sub",
  "params": {
    "binary": false
  }
}
1
2
3
4
5
6
7
8
Diff. Book Depth Streams
Payload


{
  "symbol": "BTC-SWAP-USDT",
  "topic": "diffDepth",
  "data": [
    {
      "e": 0,
      "t": 1565687625534,
      "v": "115277986_18", //Version number _18, where 18 indicates 18-bit precision. Version numbers are not guaranteed to be unique, but data from close dates will definitely be different.
      "b": [
        ["11316.78", "0.078"],
        ["11313.16", "0.0052"],
        ["11312.12", "0"],
        ["11309.75", "0.0067"],
        ["11309.58", "0"],
        ["11306.14", "0.0073"]
      ],
      "a": [
        ["11318.96", "0.0041"],
        ["11318.99", "0.0017"],
        ["11319.12", "0.0017"],
        ["11319.22", "0.4516"],
        ["11319.23", "0.0934"],
        ["11319.24", "3.0665"]
      ]
    }
  ],
  "f": false
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
Request:

{
  "symbol": "$symbol0, $symbol1",//Symbol
  "topic": "diffDepth",
  "event": "sub",
  "params": {
    "binary": false
  }
}
1
2
3
4
5
6
7
8
Individual Symbol Book Ticker Streams
Payload


{
  "topic": "bookTicker", //topic
  "params": {
    "symbol": "BTC-SWAP-USDT",
    "realtimeInterval": "24h"
  },
  "data": {
    "e": "bookTicker", //event type
    "E": 1768249193064, //event time
    "s": "BTC-SWAP-USDT", // symbol
    "b": "91791.9", // best bid price
    "bq": "41710", // best bid qty
    "a": "92704.1", // best ask price
    "aq": "57121", // best ask qty
    "t": 1768249193006 // transaction time
  },
  "f": false, //is the first time to return
  "sendTime": 1768249193064 //push time
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
Request:

{
  "symbol": "BTC-SWAP-USDT",
  "topic":"bookTicker",
  "event": "sub"
}
1
2
3
4
5
All Book Tickers Stream
descrpption：Pushes any update to the best bid or ask's price or quantity in real-time for all symbols.

Payload


{
  "topic": "wholeBookTicker",//topic
  "params": {
    "realtimeInterval": "24h"
  },
  "data": {
    "e": "wholeBookTicker",// event type
    "E": 1768249218139,// event time
    "s": "ETH-SWAP-USDT",// symbol
    "b": "4325",// best bid price
    "bq": "405",// best bid qty
    "a": "4330",// best ask price
    "aq": "310",// best ask qty
    "t": 1768249218057 // transaction time
  },
  "f": false, //is the first time to return
  "sendTime": 1768249218139 //push time
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
Request:

{
  "topic":"wholeBookTicker","event": "sub"
}
1
2
3
Push the changing part of the order book (if any) every second. In incremental depth information, the quantity is not necessarily equal to the quantity corresponding to the price. If the quantity=0, it means that the price in the last push is no longer available. If the quantity>0, the quantity at this time is the quantity corresponding to the updated price Assume that there is such an item in the returned data we received: ["0.00181860", "155.92000000"]// price, quantity If the next returned data contains: ["0.00181860", "12.3"] This means that the quantity corresponding to this price has changed, and the changed quantity has been updated If the next returned data contains: ["0.00181860", "0"] This means that the quantity corresponding to this price has disappeared and will be deleted in the client.

Last updated: 2/7/26, 4:52 AM

Pager
Previous page
Market Data Endpoints
Next page
Account/Trades Endpoints

=============================================================================
Account/Trades Endpoints
Query Sub-account (USER_DATA)
GET /api/v1/subAccount/list
Weight：5
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
userId<w:t>LONG<w:t>NO<w:t>Sub-user userId
email<w:t>String<w:t>NO<w:t>Sub-user email
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response：


[
    {
        "userId": "879141111", // Sub-user userId
        "email": "aaa@rpbsho.com", // Sub-user email
        "remark": "", // Sub-user remark
        "accountList": [ // All accounts
            {
                "accountId": "1795119090857208832", // Account id
                "userId": "879145609", // userId
                "accountType": "MAIN" // Account type
            },
            {
                "accountId": "1795119090857208834",
                "userId": "879145609",
                "accountType": "FUTURES"
            }
        ]
    },
    {
        "userId": "935651111",
        "email": "qwdqwd123_na5626@08rrkf.com",
        "remark": "",
        "accountList": [
            {
                "accountId": "1974746191561298944",
                "userId": "935650120",
                "accountType": "MAIN"
            },
            {
                "accountId": "1974746191561298945",
                "userId": "935650120",
                "accountType": "FUTURES"
            }
        ]
    }
]
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
accountType Description:

MAIN: Spot
FUTURES: U-margined Contract
COPY_TRADING: Copy Trading Account
New Future Account Transfer
POST /api/v1/subAccount/transfer
Supported transfer operations:

Parent account operation Transfer from parent spot account to any sub-account spot account, U-position contract account.
Transfer between parent account Spot account and U-position contract account.
Parent account operation Transfer of any sub-account Spot account, U-contract account to parent account Spot account
Parent account operation Transfer between spot account and U-contract account of a particular sub-account
Sub-user operation Transfer from the current sub-account spot account to the parent account spot account and `U-contract account
Sub-user operation Transfer between the current sub-user's Spot account and `U-contract account
Execute the transfer between the spot account and the contract account

Weight：1
Response：


{
    "code": 200, // 200 = success
    "msg": "success" // response message
}
1
2
3
4
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
fromUid<w:t>LONG<w:t>YES<w:t>from uid
toUid<w:t>LONG<w:t>YES<w:t>to uid
fromAccountType<w:t>String<w:t>YES<w:t>from account type
toAccountType<w:t>String<w:t>YES<w:t>to account type
coin<w:t>String<w:t>YES<w:t>token id (e.g. USDT)
quantity<w:t>DECIMAL<w:t>YES<w:t>transfer quantity
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
accountType：

MAIN: spot account
FUTURES: U-contract account
FUTURES_USDC: USDC-M Futures account
COPY_TRADING: copy trading leader account
Get Future Account Transaction History List (USER_DATA)
GET /api/v1/account/balanceFlow
Obtain the history of fund transfers between the spot account and the contract account.

Weight：5
Response：


[
  {
    "id": "539870570957903104",
    "accountId": "122216245228131",
    "coin": "BTC",
    "coinId": "BTC",
    "coinName": "BTC",
    "flowTypeValue": 51,
    "flowType": "USER_ACCOUNT_TRANSFER",
    "flowName": "Transfer",
    "change": "-12.5",
    "total": "379.624059937852365",
    "created": "1579093587214"
  },
  {
    "id": "536072393645448960",
    "accountId": "122216245228131",
    "coin": "USDT",
    "coinId": "USDT",
    "coinName": "USDT",
    "flowTypeValue": 7,
    "flowType": "AIRDROP",
    "flowName": "Airdrop",
    "change": "-2000",
    "total": "918662.0917630848",
    "created": "1578640809195"
  }
]
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
accountType<w:t>INT<w:t>NO<w:t>account_type corresponding to the account, 1: Spot account, 3: Contract account
coin<w:t>STRING<w:t>NO<w:t>coin
flowType<w:t>INT<w:t>NO<w:t>transfer：51
fromId<w:t>LONG<w:t>NO<w:t>from id
endId<w:t>LONG<w:t>NO<w:t>end id
startTime<w:t>LONG<w:t>NO<w:t>start timestamp
endTime<w:t>LONG<w:t>NO<w:t>end timestamp
limit<w:t>INT<w:t>NO<w:t>Default20 Min 1 Max 1000
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
timestamp<w:t>LONG<w:t>YES<w:t>Timestamp
Get account balance flow (API v2) (USER_DATA)
GET /api/v2/account/balance-flow
Same business data as v1, with normalized request/response. Successful responses use {"code":200,"msg":"success","data":[...]}.

Weight：5
Response (each item in data):


{
  "id": "539870570957903104",
  "accountType": "MAIN",
  "coin": "BTC",
  "symbol": "BTCUSDT",
  "flowType": "USER_ACCOUNT_TRANSFER",
  "flowName": "Transfer",
  "change": "-12.5",
  "total": "379.624059937852365",
  "created": 1579093587214
}
1
2
3
4
5
6
7
8
9
10
11
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
accountType<w:t>STRING<w:t>NO<w:t>MAIN or FUTURES (default MAIN)
coin<w:t>STRING<w:t>NO<w:t>token id
flowType<w:t>STRING<w:t>NO<w:t>flow type enum name (same as flowType in the response, e.g. USER_ACCOUNT_TRANSFER)
fromId<w:t>LONG<w:t>NO<w:t>from id
endId<w:t>LONG<w:t>NO<w:t>end id
startTime<w:t>LONG<w:t>NO<w:t>start timestamp
endTime<w:t>LONG<w:t>NO<w:t>end timestamp
limit<w:t>INT<w:t>NO<w:t>default 20, min 1, max 1000
category<w:t>ENUM<w:t>NO<w:t>not used in v2; reserved
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
v1 GET /api/v1/account/balanceFlow is unchanged.

Change Margin Type (TRADE)
POST /api/v1/futures/marginType
Change the user's margin mode on the specified symbol contract: isolated margin or cross margin.

Weight：1
Response：


{
    "code":200, 
    "symbolId":"BTC-SWAP-USDT", //symbol
    "marginType":"CROSS" // CROSS ISOLATED
}
1
2
3
4
5
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
marginType<w:t>ENUM<w:t>YES<w:t>CROSS ISOLATED
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
timestamp<w:t>LONG<w:t>YES<w:t>Timestamp
Change Initial Leverage (TRADE)
POST /api/v1/futures/leverage
Adjust the user's opening leverage in the specified symbol contract.

Weight：1
Response:

{
  "code": 200,
  "symbolId": "BTC-SWAP-USDT",
  "leverage": "20"
}
1
2
3
4
5
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
leverage<w:t>INT<w:t>YES<w:t>leverage
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
Get the leverage multiple and position mode (USER_DATA)
GET /api/v1/futures/accountLeverage
Obtain the leverage multiples and position types of all contract trading pairs of the user. This API requires your request to be signed.

Weight：5
Response：


[
    {
        "symbolId":"BTC-SWAP-USDT", //symbol
        "leverage":"20",  // leverage
        "marginType":"CROSS" // CROSS;ISOLATED
    }
]
1
2
3
4
5
6
7
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
U-margined futures (v2) is documented in Account & Trades (v2) (separate page with per-endpoint navigation).

New Order (TRADE)
POST /api/v1/futures/order

Weight：1
Response：


{
    "time": "1668418485058", // time
    "updateTime": "1668418485058", 
    "orderId": "1289182123551455488", 
    "clientOrderId": "test1115", 
    "symbol": "BTC-SWAP-USDT", // symbol
    "price": "19000", // price
    "leverage": "2", // leverage
    "origQty": "10", // quantity
    "executedQty": "0", //Executed Quantity
    "avgPrice": "0", //average  price
    "marginLocked": "9.5", //The margin locked for this order.
    "type": "LIMIT", // type（LIMIT and STOP）
    "side": "BUY_OPEN", // side（BUY_OPEN、SELL_OPEN、BUY_CLOSE、SELL_CLOSE）
    "timeInForce": "GTC", // Time in Force
    "status": "NEW", //NEW、PARTIALLY_FILLED、FILLED、CANCELED、REJECTED
    "priceType": "INPUT", //INPUT、MARKET
    "contractMultiplier": "0.001" //Contract multiplier
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
side<w:t>ENUM<w:t>YES<w:t>BUY_OPEN、SELL_OPEN、BUY_CLOSE、SELL_CLOSE
type<w:t>ENUM<w:t>YES<w:t>LIMIT or STOP
quantity<w:t>LONG<w:t>YES<w:t>Numbers of orders (volume)
valueQuantity<w:t>LONG<w:t>NO<w:t>Order value quantity (USDT). For example, purchasing 2 BTC at a price of 1000 USDT: Order value = 2 × 1000 = 2000 USDT When both valueQuantity and quantity are specified, quantity takes precedence.
price<w:t>DECIMAL<w:t>NO<w:t>LIMIT&INPUT Mandatory need
priceType<w:t>ENUM<w:t>NO<w:t>INPUT、MARKET
stopPrice<w:t>DECIMAL<w:t>NO<w:t>type = STOP order Mandatory need
timeInForce<w:t>ENUM<w:t>NO<w:t>For LIMIT orders only. Values: GTC, FOK, IOC, POST_ONLY.
newClientOrderId<w:t>STRING<w:t>YES<w:t>A unique id among open orders. The ID of the order, defined by the user.
takeProfit<w:t>STRING<w:t>NO<w:t>Take profit price
tpTriggerBy<w:t>ENUM<w:t>NO<w:t>The price type to trigger take profit:MARK_PRICE, CONTRACT_PRICE. Default CONTRACT_PRICE
tpLimitPrice<w:t>STRING<w:t>NO<w:t>The limit order price when take profit price is triggered. Only works when tpOrderType=LIMIT
tpOrderType<w:t>ENUM<w:t>NO<w:t>The order type when take profit is triggered.MARKET(default), LIMIT.
stopLoss<w:t>STRING<w:t>NO<w:t>Stop loss price,
slTriggerBy<w:t>ENUM<w:t>NO<w:t>The price type to trigger take profit:MARK_PRICE, CONTRACT_PRICE. Default CONTRACT_PRICE
slLimitPrice<w:t>STRING<w:t>NO<w:t>The limit order price when take profit price is triggered. Only works when slOrderType=LIMI
slOrderType<w:t>ENUM<w:t>NO<w:t>The order type when take profit is triggered.MARKET(default), LIMIT.
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Order Side :
BUY_OPEN Open a long buy order to open a position to buy
BUY_CLOSE Close Buy Order Close Buy
SELL_OPEN Open a short sell order to open a position to sell
SELL_CLOSE Flat long sell order, close position and sell
Price Type:
INPUT The system will match the order with the price you entered.
MARKET Orders will be matched at the latest transaction price * (1 ± 5%).
Place Multiple Orders (TRADE)
POST /api/v1/futures/batchOrders
A maximum of 10 orders at a time, must be the same symbol.

Weight: 2
USDT-M Futures. Example:

curl  -H "Content-Type:application/json" 
-H "X-BB-APIKEY: 3jIF0QWOFAA64MnaFJz1pMvVFNaLyMThHUvhii1eyYBw4saPs9ocLasp45pqeGRs" 
-X POST -d '[   
   {   
      "newClientOrderId": "pl2023010712345678900",   
      "symbol": "BTC-SWAP-USDT",   
      "side": "BUY_OPEN",   
      "type": "LIMIT",   
      "price": 16500,   
      "quantity": 10,   
      "priceType": "INPUT"   
   },   
   {  
       "newClientOrderId": "pl2023010712345678901",   
       "symbol": "BTC-SWAP-USDT",   
       "side": "BUY_OPEN",   
       "type": "LIMIT",   
       "price": 16000,   
       "quantity": 10,   
       "priceType": "INPUT"   
   } ]' '#HOST/api/v1/futures/batchOrders?timestamp=1673062952473&signature=f746cebecf9cf53601d2ab69b2f88f426a1c93a5f7bcc8bbdc5a2ce95c3fa976'
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
USDC-M Futures. Example:

curl  -H "Content-Type:application/json" 
-H "X-BB-APIKEY: 3jIF0QWOFAA64MnaFJz1pMvVFNaLyMThHUvhii1eyYBw4saPs9ocLasp45pqeGRs" 
-X POST -d '[   
   {   
      "newClientOrderId": "pl2023010712345678900",   
      "symbol": "BTC-SWAP-USDC",   
      "side": "BUY_OPEN",   
      "type": "LIMIT",   
      "price": 16500,   
      "quantity": 10,   
      "priceType": "INPUT"   
   },   
   {  
       "newClientOrderId": "pl2023010712345678901",   
       "symbol": "BTC-SWAP-USDC",   
       "side": "BUY_OPEN",   
       "type": "LIMIT",   
       "price": 16000,   
       "quantity": 10,   
       "priceType": "INPUT"   
   } ]' '#HOST/api/v1/futures/batchOrders?category=USDC&timestamp=1673062952473&signature=f746cebecf9cf53601d2ab69b2f88f426a1c93a5f7bcc8bbdc5a2ce95c3fa976'
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
Response：


{
    "code": 200, //success
    "result": [
         {
            "code": 200, //success
            "order": {
                    "time": "1673062993867", //time
                    "updateTime": "1673062993867", 
                    "orderId": "1328143087352970240", 
                    "clientOrderId": "pl2023010712345678900", 
                    "symbol": "BTC-SWAP-USDT",
                    "price": "16500",//price
                    "leverage": "0",//leverage
                    "origQty": "10", //quantity
                    "executedQty": "0", //Executed Quantity
                    "avgPrice": "0", //average  price
                    "marginLocked": "0", //The margin locked for this order.
                    "type": "LIMIT", // type（LIMIT and STOP）
                    "side": "BUY_OPEN", // side（BUY_OPEN、SELL_OPEN、BUY_CLOSE、SELL_CLOSE）
                    "timeInForce": "GTC", // Time in Force
                    "status": "NEW", //status（NEW、PARTIALLY_FILLED、FILLED、CANCELED、REJECTED）
                    "priceType": "INPUT"  //price type（INPUT、MARKET）
                    }    
        }, 
        {
                "code": -1131, //fail
                "msg": "Balance insufficient " //reason
        }
   ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
LIST<w:t>YES<w:t>RequestBody parameters
timestamp<w:t>LONG<w:t>YES
recvWindow<w:t>LONG<w:t>NO
The batchOrders in RequestBody should fill in the order parameters in list of JSON format

Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES
side<w:t>ENUM<w:t>YES<w:t>sideBUY_OPEN、SELL_OPEN、BUY_CLOSE、SELL_CLOSE
type<w:t>ENUM<w:t>YES<w:t>typeLIMIT or STOP
quantity<w:t>LONG<w:t>YES<w:t>Numbers of orders (volume)
valueQuantity<w:t>LONG<w:t>NO<w:t>Order value quantity (USDT). For example, purchasing 2 BTC at a price of 1000 USDT: Order value = 2 × 1000 = 2000 USDT When both valueQuantity and quantity are specified, quantity takes precedence.
price<w:t>DECIMAL<w:t>NO<w:t>price (LIMIT&INPUT)订单 Mandatory need
priceType<w:t>ENUM<w:t>NO<w:t>price typeINPUT、MARKET
timeInForce<w:t>ENUM<w:t>NO<w:t>For LIMIT orders only. Values: GTC, FOK, IOC, POST_ONLY.
newClientOrderId<w:t>STRING<w:t>YES<w:t>A unique id among open orders. The ID of the order, defined by the user.
Notes：

For market order, you need to set type to LIMIT and set priceType to MARKET. You can obtain the contract price and quantity precision configuration information at the brokerInfo endpoint.
If your balance does not meet the margin requirements (initial margin + opening fee + closing fee), there will be an insufficient balance (insufficient balance) error return.
Query History Orders (USER_DATA)
GET /api/v1/futures/historyOrders
Weight：5
Response：


[
  {
    "time": "1570760254539", //create tiem
    "updateTime": "1570760254539", 
    "orderId": "469965509788581888", 
    "clientOrderId": "1570760253946",  //User defined order ID
    "symbol": "BTC-SWAP-USDT", 
    "price": "8502.34", 
    "leverage": "20", 
    "origQty": "222", // quantity
    "executedQty": "0", // Executed Quantity
    "avgPrice": "0", // avg price
    "marginLocked": "0.00130552", // The margin locked for this order.
    "type": "LIMIT", 
    "side": "BUY_OPEN", 
    "timeInForce": "GTC", // Time in Force
    "status": "CANCELED", 
    "priceType": "INPUT" 
  }
]
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>NO<w:t>symbol
orderId<w:t>LONG<w:t>NO<w:t>order id
type<w:t>ENUM<w:t>NO<w:t>DefaultLINIT LIMIT or STOP
startTime<w:t>LONG<w:t>NO<w:t>start timestamp. Default value three days ago
endTime<w:t>LONG<w:t>NO<w:t>end timestamp
limit<w:t>INT<w:t>NO<w:t>Default20 Min 1 Max 1000
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Notes：

If orderId is sent, all orders < orderId will be returned. If not, the latest order will be returned.
Futures Account Balance (USER_DATA)
GET /api/v1/futures/balance
Weight：5
Response：


[
     {
        "coin": "USDT",
        "balance": "999999999999.982",
        "availableBalance": "1899999999978.4995",
        "positionMargin": "11.9825",
        "orderMargin": "9.5",
        "crossUnRealizedPnl": "10.01",
        "coupon": "100.5"
    }
]
1
2
3
4
5
6
7
8
9
10
11
Parameters
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Modify Isolated Position Margin (TRADE)
POST /api/v1/futures/positionMargin
Adjust the isolated margin funds for positions in isolated margin mode.

Weight：1
Response：


{
    "code":200,  // 200 = success
    "msg":"success",  // response message
    "symbol":"BTC-SWAP-USDT", 
    "margin":15,  // Number of Margin
    "timestamp":1541161088303 // timestamp
}
1
2
3
4
5
6
7
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
side<w:t>ENUM<w:t>YES<w:t>LONG or SHORT
amount<w:t>DECIMAL<w:t>YES<w:t>Increase (positive value) or decrease (negative value) the amount of margin. Please note that this quantity refers to the underlying pricing asset of the contract (that is, the underlying of the contract settlement)
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
Account Trade List (USER_DATA)
GET /api/v1/futures/userTrades
Get trade history for a specific trading pair.

Weight：5
Response:

[
    {
        "time": "1668425281370", //create time
        "id": "1289239136943831296", //Trade Id
        "orderId": "1289239134670518528", 
        "symbol": "BTC-SWAP-USDT", 
        "price": "24000",
        "qty": "9", //quantity
        "commissionAsset": "USDT", 
        "commission": "0.0162", 
        "makerRebate": "0", 
        "type": "LIMIT", 
        "isMaker": false, // isMaker
        "side": "BUY_OPEN", //BUY_OPEN、SELL_OPEN、BUY_CLOSE、SELL_CLOSE
        "realizedPnl": "0",
        "ticketId": "1185465136943458745" // ticketId
    }
]
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
startTime<w:t>LONG<w:t>NO<w:t>start timestamp
endTime<w:t>LONG<w:t>NO<w:t>end timestamp
limit<w:t>INT<w:t>NO<w:t>Default20 Min 1 Max 1000
fromId<w:t>LONG<w:t>NO<w:t>Start from TradeId (used to query transaction orders)
toId<w:t>LONG<w:t>NO<w:t>To the end of TradeId (used to query transaction orders)
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
Get Futures Account Transaction History List (USER_DATA)
GET /api/v1/futures/balanceFlow
Weight：5
Response：


[
    {
        "id": "539870570957903104",
        "accountId": "122216245228131",
        "coin": "BTC",
        "coinId": "BTC",
        "coinName": "BTC",
        "symbol": "BTC-SWAP-USDT", // symbol name
        "symbolId": "BTC-SWAP-USDT",
        "flowTypeValue": 51, 
        "flowType": "USER_ACCOUNT_TRANSFER", 
        "flowName": "Transfer",
        "change": "-12.5", 
        "total": "379.624059937852365",
        "created": "1579093587214"
    }
]
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>NO<w:t>coin
flowType<w:t>INT<w:t>NO<w:t>flow type
fromId<w:t>LONG<w:t>NO<w:t>from id
endId<w:t>LONG<w:t>NO<w:t>end id
startTime<w:t>LONG<w:t>NO<w:t>start timestamp
endTime<w:t>LONG<w:t>NO<w:t>end timestamp
limit<w:t>INT<w:t>NO<w:t>limit
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
flowType enum

Description<w:t>flowType value
Fee<w:t>10
Fund Fee<w:t>32
Realized PNL<w:t>28
Force liquidation<w:t>700
ADL<w:t>701
Apply Download File (USER_DATA)
POST /api/v1/account/download/apply
Apply to download historical order or funding flow files. This endpoint requires request signature.

Weight：1000
Response：


{
    "id": 1000, // Download record ID
    "createTime": 1579093587214, // Creation timestamp
    "status": "INIT", // Status: Fixed as INIT (initialization), indicating download application has been created
    "downloadType": "ORDER", // Download type: ORDER (historical orders)、FUNDING (funding flow)
    "symbol": "BTC-SWAP-USDT" // Trading pair, empty string means all
}
1
2
3
4
5
6
7
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
downloadType<w:t>STRING<w:t>YES<w:t>Download type:ORDER (historical orders)、FUNDING (funding flow)
category<w:t>STRING<w:t>NO<w:t>Business type:USDT (default)、USDC
startTime<w:t>LONG<w:t>NO<w:t>Start timestamp (milliseconds), default last 7 days
endTime<w:t>LONG<w:t>NO<w:t>End timestamp (milliseconds), default last 7 days
symbol<w:t>STRING<w:t>NO<w:t>Trading pair, default empty string (all)
timestamp<w:t>LONG<w:t>YES<w:t>Timestamp
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Notes：

The status returned by this endpoint is fixed as INIT (initialization), indicating download application has been created
To query download processing status, please use /api/v1/account/download/detail endpoint
If both startTime and endTime are not provided, default to last 7 days of data
If endTime is specified but startTime is not, startTime will be endTime-7 days
If startTime is specified but endTime is not, endTime will be startTime+7 days
Timestamps will be converted to UTC+0 date 0:00 timestamp for calculation
Only one file can be applied for download at a time
Download application count is shared with frontend requests (including web pages, etc.). Once the monthly limit is exceeded, download applications will be unavailable
Query Download Record Detail (USER_DATA)
GET /api/v1/account/download/detail
Query detailed information of download records, including download links. This endpoint requires request signature.

Weight：10
Response：


{
    "id": 1000, // Download record ID
    "createTime": 1579093587214, // Creation timestamp
    "downloadType": "ORDER", // Download type: ORDER (historical orders)、FUNDING (funding flow)
    "startTime": 1579007187214, // Start timestamp
    "endTime": 1579093587214, // End timestamp
    "symbol": "BTC-SWAP-USDT", // Trading pair
    "status": "SUCCESS", // Status: INIT (initialization)、SUCCESS (success)、FAIL (failure)、EXPIRED (expired)
    "downloadLink": "https://example.com/download/file.xlsx" // Download link (only returned when status is SUCCESS and not expired)
}
1
2
3
4
5
6
7
8
9
10
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
id<w:t>LONG<w:t>YES<w:t>Download record ID
timestamp<w:t>LONG<w:t>YES<w:t>Timestamp
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
status Status Description：

Status Value<w:t>Description
INIT<w:t>Initialization status (when download record is just created)
SUCCESS<w:t>Success status (file has been generated and uploaded successfully)
FAIL<w:t>Failure status (file generation or upload failed)
EXPIRED<w:t>Expired status (download link has expired)
Notes：

The status returned by this endpoint may be INIT, SUCCESS, FAIL, or EXPIRED, indicating the current status of download processing
downloadLink is only returned when status is SUCCESS and not expired
Within 7 days after the download record is created, you can obtain downloadLink through this endpoint; after 7 days, when requesting this endpoint again, the status will become EXPIRED and downloadLink will not be returned
User Trade Fee Rate (USER_DATA)
GET /api/v1/futures/commissionRate
Weight：5
Response：


{
    "openMakerFee": "0.000006", //The trade fee rate for opening pending orders
    "openTakerFee": "0.0001", //The trade fee rate for open position taker
    "closeMakerFee": "0.0002", //The trade fee rate for closing pending orders
    "closeTakerFee": "0.0004" //The trade fee rate for closing a taker order
}
1
2
3
4
5
6
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>symbol
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
Today Pnl (USER_DATA)
GET /api/v1/futures/todayPnl
Weight：5
Response：


{
    "dayProfit": "100", // UTC+0 time zone
    "dayProfitRate": "0.01" // UTC+0 time zone
}
1
2
3
4
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
Last updated: 5/26/26, 6:46 AM

Account & Trades (v2)
REST API v2 for USDT-M / USDC-M under /api/v2/futures. Paths use kebab-case. For spot / shared account v2 (e.g. balance flow on /api/v2/account), see Account & Trades (v2).

Overview
Successful responses use:


{ "code": 200, "msg": "success", "data": { } }
1
code = 200 on success; errors use negative codes (see Error codes).
Lists wrap rows in data as a JSON array (e.g. open orders, trades). Batch new order returns an array of { "code", "order" } per item.
See Basic information for SIGNED and JSON request body (v2) (same page).
Wire format (JSON): Integer timestamps and ids that are 64-bit in the system are sent as strings in JSON (not unquoted numbers). Null fields are usually omitted from the body (you will not see "field": null for most optional keys). Optional fields such as stopPrice or triggerBy only appear in the response when they have a value.
Enum parameters (reference)
Allowed values for common string enums in requests/responses. Each field below has the same allowed values on every route where it appears.

Parameter<w:t>Allowed values
category<w:t>USDT (USDT-M), USDC (USDC-M)
side<w:t>BUY, SELL
positionSide<w:t>LONG, SHORT
type<w:t>Regular order: LIMIT limit order, MARKET market order
Plan order: STOP converts to limit order on trigger, STOP_MARKET converts to market order on trigger
Update plan order body: STOP plan orders, STOP_PROFIT_LOSS TP/SL orders
stopCategory<w:t>STOP plan orders, STOP_PROFIT_LOSS TP/SL orders
timeInForce<w:t>GTC, FOK, IOC, POST_ONLY
triggerBy / tpTriggerBy / slTriggerBy<w:t>CONTRACT_PRICE, MARK_PRICE
tpOrderType / slOrderType<w:t>MARKET, LIMIT
stopOrderType<w:t>TAKE_PROFIT, STOP_LOSS
stopType<w:t>FIXED_STOP, TRAILING_STOP
fallbackType<w:t>RATE, PRICE
New regular order (TRADE)
POST /api/v2/futures/order
Weight：1
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>Contract symbol id
side<w:t>STRING<w:t>YES<w:t>BUY or SELL
positionSide<w:t>STRING<w:t>YES<w:t>LONG or SHORT
type<w:t>STRING<w:t>YES<w:t>LIMIT or MARKET
newClientOrderId<w:t>STRING<w:t>YES<w:t>Client order id
quantity<w:t>DECIMAL<w:t>NO<w:t>Order quantity (unit: contracts); at least one of quantity / valueQuantity must be non-zero
valueQuantity<w:t>DECIMAL<w:t>NO<w:t>USDT notional; at least one of quantity / valueQuantity must be non-zero
price<w:t>DECIMAL<w:t>NO<w:t>Required when type = LIMIT; omit for MARKET
timeInForce<w:t>STRING<w:t>NO<w:t>One of GTC, FOK, IOC, POST_ONLY. Default GTC.
takeProfit<w:t>STRING<w:t>NO<w:t>Take-profit price
tpTriggerBy<w:t>STRING<w:t>NO<w:t>Price type used to trigger take-profit: CONTRACT_PRICE, MARK_PRICE
tpLimitPrice<w:t>STRING<w:t>NO<w:t>Limit price after take-profit is triggered (when tpOrderType = LIMIT)
tpOrderType<w:t>STRING<w:t>NO<w:t>Order type after take-profit is triggered: MARKET, LIMIT
stopLoss<w:t>STRING<w:t>NO<w:t>Stop-loss price
slTriggerBy<w:t>STRING<w:t>NO<w:t>Price type used to trigger stop-loss: CONTRACT_PRICE, MARK_PRICE
slLimitPrice<w:t>STRING<w:t>NO<w:t>Limit price after stop-loss is triggered (when slOrderType = LIMIT)
slOrderType<w:t>STRING<w:t>NO<w:t>Order type after stop-loss is triggered: MARKET, LIMIT
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response

{
  "code": 200,
  "msg": "success",
  "data": {
    "time": "1668418485058",
    "updateTime": "1668418485058",
    "orderId": "1289182123551455488",
    "clientOrderId": "test1115",
    "symbol": "BTC-SWAP-USDT",
    "price": "19000",
    "leverage": "2",
    "origQty": "10",
    "executedQty": "0",
    "avgPrice": "0",
    "marginLocked": "9.5",
    "type": "LIMIT",
    "side": "BUY",
    "positionSide": "LONG",
    "timeInForce": "GTC",
    "status": "NEW",
    "contractMultiplier": "0.001"
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
Batch new orders (JSON) (TRADE)
POST /api/v2/futures/batch-orders
Weight：2
Content-Type: application/json — request body is a JSON array of order objects. For signing details, see JSON Request Body Signing Examples (API v2).

Query parameters (signed)
Name<w:t>Type<w:t>Mandatory<w:t>Description
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>required for SIGNED
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Request body (JSON array) — each element
Each object carries the same business fields as a single New regular order; semantics match that endpoint’s table.

Name<w:t>Type<w:t>Mandatory<w:t>Description
newClientOrderId<w:t>STRING<w:t>YES<w:t>Client order id
symbol<w:t>STRING<w:t>YES<w:t>Contract symbol id
side<w:t>STRING<w:t>YES<w:t>BUY or SELL
positionSide<w:t>STRING<w:t>YES<w:t>LONG or SHORT
type<w:t>STRING<w:t>YES<w:t>LIMIT or MARKET
quantity<w:t>DECIMAL<w:t>NO<w:t>Per element quantity (unit: contracts); at least one of quantity / valueQuantity must be non-zero
valueQuantity<w:t>DECIMAL<w:t>NO<w:t>USDT notional; at least one of quantity / valueQuantity must be non-zero
price<w:t>DECIMAL<w:t>NO<w:t>Required per element when type = LIMIT; defaults to 0 if omitted
timeInForce<w:t>STRING<w:t>NO<w:t>One of GTC, FOK, IOC, POST_ONLY; per element defaults to GTC if omitted
Response
data is an array of { code, order }; failed legs return order = null, successful legs return an order object.


{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "code": 200,
      "order": {
        "time": "1668418485058",
        "updateTime": "1668418485058",
        "orderId": "1289182123551455488",
        "clientOrderId": "c1",
        "symbol": "BTC-SWAP-USDT",
        "price": "19000",
        "leverage": "2",
        "origQty": "10",
        "executedQty": "0",
        "avgPrice": "0",
        "marginLocked": "9.5",
        "type": "LIMIT",
        "side": "BUY",
        "positionSide": "LONG",
        "timeInForce": "GTC",
        "status": "NEW",
        "contractMultiplier": "0.001"
      }
    },
    {
      "code": -2011,
      "order": null
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
Update regular order (TRADE)
POST /api/v2/futures/order/update
Weight：2
Parameters
LIMIT orders only — amend price/size per the parameter table.

Name<w:t>Type<w:t>Mandatory<w:t>Description
orderId<w:t>LONG<w:t>NO<w:t>Mutually exclusive with origClientOrderId; pass one to identify the order
origClientOrderId<w:t>STRING<w:t>NO<w:t>Mutually exclusive with orderId; client id of the order to update
newClientOrderId<w:t>STRING<w:t>NO<w:t>New client id; default generated if omitted
quantity<w:t>DECIMAL<w:t>NO<w:t>New quantity (optional, unit: contracts)
valueQuantity<w:t>DECIMAL<w:t>NO<w:t>New value quantity; default 0
price<w:t>DECIMAL<w:t>NO<w:t>New price; default 0
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response

{
  "code": 200,
  "msg": "success",
  "data": {
    "time": "1767952682388",
    "updateTime": "1767952682388",
    "orderId": "2124135487564299264",
    "clientOrderId": "1767952681690",
    "symbol": "ETH-SWAP-USDT",
    "price": "4000",
    "leverage": "20",
    "origQty": "1",
    "executedQty": "0",
    "avgPrice": "0",
    "marginLocked": "2",
    "type": "LIMIT",
    "side": "BUY",
    "positionSide": "LONG",
    "timeInForce": "GTC",
    "status": "NEW",
    "contractMultiplier": "0.01"
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
Cancel one regular order (TRADE)
DELETE /api/v2/futures/order
Weight：1
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
orderId<w:t>LONG<w:t>NO<w:t>Mutually exclusive with origClientOrderId; pass one to cancel
origClientOrderId<w:t>STRING<w:t>NO<w:t>Mutually exclusive with orderId
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response

{
  "code": 200,
  "msg": "success",
  "data": {
    "time": "1668418485058",
    "updateTime": "1668418490000",
    "orderId": "1289182123551455488",
    "clientOrderId": "test1115",
    "symbol": "BTC-SWAP-USDT",
    "price": "19000",
    "leverage": "2",
    "origQty": "10",
    "executedQty": "0",
    "avgPrice": "0",
    "marginLocked": "0",
    "type": "LIMIT",
    "side": "BUY",
    "positionSide": "LONG",
    "timeInForce": "GTC",
    "status": "CANCELED",
    "contractMultiplier": "0.001"
  }
}
Batch cancel regular orders (TRADE)
DELETE /api/v2/futures/batch-orders
Weight：3
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>Comma-separated contract symbol ids
side<w:t>STRING<w:t>NO<w:t>Optional BUY or SELL; omit = no side filter. No positionSide on this route.
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response
data is always null (no order payload, no string enums on this route).


{
  "code": 200,
  "msg": "success",
  "data": null
}
1
2
3
4
5
Get one regular order (USER_DATA)
GET /api/v2/futures/order
Weight：1
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
orderId<w:t>LONG<w:t>NO<w:t>Mutually exclusive with origClientOrderId; pass one to query
origClientOrderId<w:t>STRING<w:t>NO<w:t>Mutually exclusive with orderId
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response

{
  "code": 200,
  "msg": "success",
  "data": {
    "time": "1668418485058",
    "updateTime": "1668418485058",
    "orderId": "1289182123551455488",
    "clientOrderId": "test1115",
    "symbol": "BTC-SWAP-USDT",
    "price": "19000",
    "leverage": "2",
    "origQty": "10",
    "executedQty": "0",
    "avgPrice": "0",
    "marginLocked": "9.5",
    "type": "LIMIT",
    "side": "BUY",
    "positionSide": "LONG",
    "timeInForce": "GTC",
    "status": "NEW",
    "contractMultiplier": "0.001"
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
Open regular orders (USER_DATA)
GET /api/v2/futures/open-orders
Weight：1
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>NO<w:t>Filter by symbol id; empty = all
orderId<w:t>LONG<w:t>NO<w:t>Cursor
limit<w:t>INT<w:t>NO<w:t>default 20, min 1, max 1000
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response

{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "time": "1668418485058",
      "updateTime": "1668418485058",
      "orderId": "1289182123551455488",
      "clientOrderId": "test1115",
      "symbol": "BTC-SWAP-USDT",
      "price": "19000",
      "leverage": "2",
      "origQty": "10",
      "executedQty": "0",
      "avgPrice": "0",
      "marginLocked": "9.5",
      "type": "LIMIT",
      "side": "BUY",
      "positionSide": "LONG",
      "timeInForce": "GTC",
      "status": "NEW",
      "contractMultiplier": "0.001"
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
History regular orders (USER_DATA)
GET /api/v2/futures/history-orders
Weight：5
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>NO<w:t>Filter by symbol id; empty = all
orderId<w:t>LONG<w:t>NO<w:t>Cursor; default 0
startTime<w:t>LONG<w:t>NO<w:t>Start (ms); default rolling window if <= 0
endTime<w:t>LONG<w:t>NO<w:t>End (ms)
limit<w:t>INT<w:t>NO<w:t>default 20, min 1, max 1000
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response

{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "time": "1668418485058",
      "updateTime": "1668418485058",
      "orderId": "1289182123551455488",
      "clientOrderId": "test1115",
      "symbol": "BTC-SWAP-USDT",
      "price": "19000",
      "leverage": "2",
      "origQty": "10",
      "executedQty": "0",
      "avgPrice": "0",
      "marginLocked": "9.5",
      "type": "LIMIT",
      "side": "BUY",
      "positionSide": "LONG",
      "timeInForce": "GTC",
      "status": "NEW",
      "contractMultiplier": "0.001"
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
User trades (USER_DATA)
GET /api/v2/futures/user-trades
Weight：5
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>Contract symbol id
fromId<w:t>LONG<w:t>NO<w:t>default 0
toId<w:t>LONG<w:t>NO<w:t>default 0
startTime<w:t>LONG<w:t>NO<w:t>Start (ms)
endTime<w:t>LONG<w:t>NO<w:t>End (ms)
limit<w:t>INT<w:t>NO<w:t>default 20, min 1, max 1000
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response

{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "time": "1668419000000",
      "createdTime": "1668419000100",
      "id": "9876543210",
      "orderId": "1289182123551455488",
      "matchOrderId": "1289182123551456000",
      "matchAccountId": "10001",
      "accountId": "122216245228131",
      "symbol": "BTC-SWAP-USDT",
      "price": "19000",
      "qty": "1",
      "commissionAsset": "USDT",
      "commission": "0.01",
      "makerRebate": "0",
      "type": "LIMIT",
      "side": "BUY",
      "positionSide": "LONG",
      "realizedPnl": "0",
      "ticketId": "t1",
      "isMaker": true,
      "matchOrderStrategy": 0
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
New plan order (TRADE)
POST /api/v2/futures/algo-order
Weight：1
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>Contract symbol id
side<w:t>STRING<w:t>YES<w:t>BUY or SELL
positionSide<w:t>STRING<w:t>YES<w:t>LONG or SHORT
type<w:t>STRING<w:t>YES<w:t>STOP or STOP_MARKET
stopPrice<w:t>DECIMAL<w:t>YES<w:t>Trigger price
newClientOrderId<w:t>STRING<w:t>YES<w:t>Client order id
quantity<w:t>DECIMAL<w:t>NO<w:t>Order quantity (unit: contracts); at least one of quantity / valueQuantity must be non-zero
valueQuantity<w:t>DECIMAL<w:t>NO<w:t>USDT notional; at least one of quantity / valueQuantity must be non-zero
price<w:t>DECIMAL<w:t>NO<w:t>Required when type = STOP (limit price after trigger); omit for STOP_MARKET
timeInForce<w:t>STRING<w:t>NO<w:t>One of GTC, FOK, IOC, POST_ONLY; default GTC if omitted
triggerBy<w:t>STRING<w:t>NO<w:t>Trigger price type: CONTRACT_PRICE (default), MARK_PRICE
takeProfit<w:t>STRING<w:t>NO<w:t>Take-profit price
tpTriggerBy<w:t>STRING<w:t>NO<w:t>Price type used to trigger take-profit: CONTRACT_PRICE, MARK_PRICE
tpLimitPrice<w:t>STRING<w:t>NO<w:t>Limit price after take-profit is triggered (when tpOrderType = LIMIT)
tpOrderType<w:t>STRING<w:t>NO<w:t>Order type after take-profit is triggered: MARKET, LIMIT
stopLoss<w:t>STRING<w:t>NO<w:t>Stop-loss price
slTriggerBy<w:t>STRING<w:t>NO<w:t>Price type used to trigger stop-loss: CONTRACT_PRICE, MARK_PRICE
slLimitPrice<w:t>STRING<w:t>NO<w:t>Limit price after stop-loss is triggered (when slOrderType = LIMIT)
slOrderType<w:t>STRING<w:t>NO<w:t>Order type after stop-loss is triggered: MARKET, LIMIT
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response
Example — plan order (STOP / STOP_MARKET):


{
  "code": 200,
  "msg": "success",
  "data": {
    "time": "1767952799216",
    "updateTime": "1767952799216",
    "orderId": "2124136467689134848",
    "clientOrderId": "1767952799112",
    "symbol": "BTC-SWAP-USDT",
    "price": "0",
    "leverage": "20",
    "origQty": "2",
    "executedQty": "0",
    "avgPrice": "0",
    "marginLocked": "10",
    "type": "STOP_MARKET",
    "side": "BUY",
    "positionSide": "LONG",
    "timeInForce": "GTC",
    "status": "ORDER_NEW",
    "contractMultiplier": "0.001",
    "stopPrice": "95000",
    "triggerBy": "CONTRACT_PRICE"
  }
}
Update plan order (TRADE)
POST /api/v2/futures/algo-order/update
Weight：2
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
type<w:t>STRING<w:t>YES<w:t>STOP (plan-order row) or STOP_PROFIT_LOSS (TP/SL row)
orderId<w:t>LONG<w:t>NO<w:t>Mutually exclusive with origClientOrderId; pass one to locate the row to amend
origClientOrderId<w:t>STRING<w:t>NO<w:t>Mutually exclusive with orderId; client id of the row to amend
newClientOrderId<w:t>STRING<w:t>NO<w:t>New client id; default generated if omitted
quantity<w:t>DECIMAL<w:t>NO<w:t>New quantity (unit: contracts)
valueQuantity<w:t>DECIMAL<w:t>NO<w:t>default 0
price<w:t>DECIMAL<w:t>NO<w:t>default 0
stopPrice<w:t>DECIMAL<w:t>NO<w:t>Trigger price; default 0
triggerBy<w:t>STRING<w:t>NO<w:t>CONTRACT_PRICE or MARK_PRICE. Empty / omitted keeps the order’s original trigger type.
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response
The returned object reflects the order family chosen by the request body's type: plan family returns STOP / STOP_MARKET, TP/SL family returns STOP_PROFIT_LOSS / STOP_PROFIT_LOSS_MARKET. TP/SL rows may include additional enum fields stopOrderType, stopType, and fallbackType (for trailing scenarios), plus related fields such as activePrice, fallbackQuantity, activeStatus, etc.

Example — plan family:


{
  "code": 200,
  "msg": "success",
  "data": {
    "time": "1767952799216",
    "updateTime": "1767952800000",
    "orderId": "2124136467689134848",
    "clientOrderId": "1767952799112",
    "symbol": "BTC-SWAP-USDT",
    "price": "96000",
    "leverage": "20",
    "origQty": "2",
    "executedQty": "0",
    "avgPrice": "0",
    "marginLocked": "10",
    "type": "STOP",
    "side": "BUY",
    "positionSide": "LONG",
    "timeInForce": "GTC",
    "status": "ORDER_NEW",
    "contractMultiplier": "0.001",
    "stopPrice": "95000",
    "triggerBy": "CONTRACT_PRICE"
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
Example — TP/SL family:


{
  "code": 200,
  "msg": "success",
  "data": {
    "time": "1767952801000",
    "updateTime": "1767952802000",
    "orderId": "2124136467689135000",
    "clientOrderId": "1767952800001",
    "symbol": "BTC-SWAP-USDT",
    "price": "100000",
    "leverage": "20",
    "origQty": "1",
    "executedQty": "0",
    "avgPrice": "0",
    "marginLocked": "5",
    "type": "STOP_PROFIT_LOSS",
    "side": "SELL",
    "positionSide": "LONG",
    "timeInForce": "GTC",
    "status": "ORDER_NEW",
    "contractMultiplier": "0.001",
    "stopPrice": "99000",
    "triggerBy": "CONTRACT_PRICE",
    "stopOrderType": "TAKE_PROFIT",
    "stopType": "FIXED_STOP"
  }
}
Get one plan order (USER_DATA)
GET /api/v2/futures/algo-order
Weight：1
Plan and TP/SL rows resolve by id only.

Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
orderId<w:t>LONG<w:t>NO<w:t>Mutually exclusive with origClientOrderId; pass one to query
origClientOrderId<w:t>STRING<w:t>NO<w:t>Mutually exclusive with orderId
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response
data is a single plan or TP/SL order:

type:
STOP — plan order, limit fill after trigger;
STOP_MARKET — plan order, market fill after trigger;
STOP_PROFIT_LOSS — TP/SL condition, limit after trigger;
STOP_PROFIT_LOSS_MARKET — TP/SL condition, market after trigger.
When type is STOP_PROFIT_LOSS or STOP_PROFIT_LOSS_MARKET, the row may include additional enum fields stopOrderType and stopType.
For trailing scenarios, the row may also include fallbackType, activePrice, fallbackQuantity, activeStatus, etc., when applicable.
Example — plan order (STOP / STOP_MARKET):


{
  "code": 200,
  "msg": "success",
  "data": {
    "time": "1767952799216",
    "updateTime": "1767952800000",
    "orderId": "2124136467689134848",
    "clientOrderId": "1767952799112",
    "symbol": "BTC-SWAP-USDT",
    "price": "0",
    "leverage": "20",
    "origQty": "2",
    "executedQty": "0",
    "avgPrice": "0",
    "marginLocked": "10",
    "type": "STOP",
    "side": "BUY",
    "positionSide": "LONG",
    "timeInForce": "GTC",
    "status": "ORDER_NEW",
    "contractMultiplier": "0.001",
    "stopPrice": "96000",
    "triggerBy": "CONTRACT_PRICE"
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
Example — TP/SL limit (STOP_PROFIT_LOSS, take-profit):


{
  "code": 200,
  "msg": "success",
  "data": {
    "time": "1767952801000",
    "updateTime": "1767952802000",
    "orderId": "2124136467689135000",
    "clientOrderId": "tp-001",
    "symbol": "BTC-SWAP-USDT",
    "price": "100000",
    "leverage": "20",
    "origQty": "1",
    "executedQty": "0",
    "avgPrice": "0",
    "marginLocked": "5",
    "type": "STOP_PROFIT_LOSS",
    "side": "SELL",
    "positionSide": "LONG",
    "timeInForce": "GTC",
    "status": "ORDER_NEW",
    "contractMultiplier": "0.001",
    "stopPrice": "99000",
    "triggerBy": "MARK_PRICE",
    "stopOrderType": "TAKE_PROFIT",
    "stopType": "FIXED_STOP"
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
Example — TP/SL market (STOP_PROFIT_LOSS_MARKET, stop-loss):


{
  "code": 200,
  "msg": "success",
  "data": {
    "time": "1767952803000",
    "updateTime": "1767952803000",
    "orderId": "2124136467689135001",
    "clientOrderId": "sl-mkt-001",
    "symbol": "BTC-SWAP-USDT",
    "price": "0",
    "leverage": "20",
    "origQty": "1",
    "executedQty": "0",
    "avgPrice": "0",
    "marginLocked": "5",
    "type": "STOP_PROFIT_LOSS_MARKET",
    "side": "SELL",
    "positionSide": "LONG",
    "timeInForce": "GTC",
    "status": "ORDER_NEW",
    "contractMultiplier": "0.001",
    "stopPrice": "92000",
    "triggerBy": "CONTRACT_PRICE",
    "stopOrderType": "STOP_LOSS",
    "stopType": "FIXED_STOP"
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
Example — trailing stop-loss (TRAILING_STOP, optional activePrice / fallback* when applicable):


{
  "code": 200,
  "msg": "success",
  "data": {
    "time": "1767952804000",
    "updateTime": "1767952804000",
    "orderId": "2124136467689135002",
    "clientOrderId": "trail-001",
    "symbol": "BTC-SWAP-USDT",
    "price": "0",
    "leverage": "20",
    "origQty": "1",
    "executedQty": "0",
    "avgPrice": "0",
    "marginLocked": "5",
    "type": "STOP_PROFIT_LOSS",
    "side": "SELL",
    "positionSide": "LONG",
    "timeInForce": "GTC",
    "status": "ORDER_NEW",
    "contractMultiplier": "0.001",
    "stopPrice": "0",
    "triggerBy": "CONTRACT_PRICE",
    "stopOrderType": "STOP_LOSS",
    "stopType": "TRAILING_STOP",
    "activePrice": "95000",
    "fallbackType": "RATE",
    "fallbackQuantity": "0.01",
    "activeStatus": 0
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
Cancel one plan order (TRADE)
DELETE /api/v2/futures/algo-order
Cancels a single plan or TP/SL row by id.

Weight：1
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
orderId<w:t>LONG<w:t>NO<w:t>Mutually exclusive with origClientOrderId; pass one to cancel
origClientOrderId<w:t>STRING<w:t>NO<w:t>Mutually exclusive with orderId
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response
data is the canceled order's final snapshot (plan or TP/SL):

type: same set as Get one plan order → Response — STOP, STOP_MARKET, STOP_PROFIT_LOSS, STOP_PROFIT_LOSS_MARKET.
TP/SL rows also carry stopOrderType (TAKE_PROFIT, STOP_LOSS) and stopType (FIXED_STOP, TRAILING_STOP); trailing rows may include activePrice, fallbackType (RATE, PRICE), etc., when applicable.
Example — plan canceled:


{
  "code": 200,
  "msg": "success",
  "data": {
    "time": "1767952799216",
    "updateTime": "1767952805000",
    "orderId": "2124136467689134848",
    "clientOrderId": "1767952799112",
    "symbol": "BTC-SWAP-USDT",
    "price": "0",
    "leverage": "20",
    "origQty": "2",
    "executedQty": "0",
    "avgPrice": "0",
    "marginLocked": "10",
    "type": "STOP",
    "side": "BUY",
    "positionSide": "LONG",
    "timeInForce": "GTC",
    "status": "ORDER_CANCELED",
    "contractMultiplier": "0.001",
    "stopPrice": "96000",
    "triggerBy": "CONTRACT_PRICE"
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
Example — TP/SL canceled:


{
  "code": 200,
  "msg": "success",
  "data": {
    "time": "1767952801000",
    "updateTime": "1767952805000",
    "orderId": "2124136467689135000",
    "clientOrderId": "tp-001",
    "symbol": "BTC-SWAP-USDT",
    "price": "100000",
    "leverage": "20",
    "origQty": "1",
    "executedQty": "0",
    "avgPrice": "0",
    "marginLocked": "5",
    "type": "STOP_PROFIT_LOSS",
    "side": "SELL",
    "positionSide": "LONG",
    "timeInForce": "GTC",
    "status": "ORDER_CANCELED",
    "contractMultiplier": "0.001",
    "stopPrice": "99000",
    "triggerBy": "MARK_PRICE",
    "stopOrderType": "TAKE_PROFIT",
    "stopType": "FIXED_STOP"
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
Open plan orders (USER_DATA)
GET /api/v2/futures/open-algo-orders
Weight：1
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>NO<w:t>Filter; empty = all
orderId<w:t>LONG<w:t>NO<w:t>Cursor
stopCategory<w:t>STRING<w:t>NO<w:t>STOP (plan orders only) or STOP_PROFIT_LOSS (TP/SL only); if omitted, results are plan STOP only (excludes TP/SL)
limit<w:t>INT<w:t>NO<w:t>default 20, min 1, max 1000
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response
data is an array of plan / TP-SL order rows:

Per-row type: same four values and meanings as Get one plan order → Response — STOP, STOP_MARKET, STOP_PROFIT_LOSS, STOP_PROFIT_LOSS_MARKET. Which rows appear is determined by request stopCategory (it filters the row set only; it does not change per-row enum semantics).
TP/SL rows also carry stopOrderType (TAKE_PROFIT, STOP_LOSS) and stopType (FIXED_STOP, TRAILING_STOP); trailing rows may include activePrice, fallbackType (RATE, PRICE), fallbackQuantity, activeStatus, etc., when applicable.

{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "time": "1767952799216",
      "updateTime": "1767952799216",
      "orderId": "2124136467689134848",
      "clientOrderId": "1767952799112",
      "symbol": "BTC-SWAP-USDT",
      "price": "0",
      "leverage": "20",
      "origQty": "2",
      "executedQty": "0",
      "avgPrice": "0",
      "marginLocked": "10",
      "type": "STOP_MARKET",
      "side": "BUY",
      "positionSide": "LONG",
      "timeInForce": "GTC",
      "status": "ORDER_NEW",
      "contractMultiplier": "0.001",
      "stopPrice": "95000",
      "triggerBy": "CONTRACT_PRICE"
    },
    {
      "time": "1767952801000",
      "updateTime": "1767952802000",
      "orderId": "2124136467689135000",
      "clientOrderId": "tp-001",
      "symbol": "BTC-SWAP-USDT",
      "price": "100000",
      "leverage": "20",
      "origQty": "1",
      "executedQty": "0",
      "avgPrice": "0",
      "marginLocked": "5",
      "type": "STOP_PROFIT_LOSS",
      "side": "SELL",
      "positionSide": "LONG",
      "timeInForce": "GTC",
      "status": "ORDER_NEW",
      "contractMultiplier": "0.001",
      "stopPrice": "99000",
      "triggerBy": "MARK_PRICE",
      "stopOrderType": "TAKE_PROFIT",
      "stopType": "FIXED_STOP"
    },
    {
      "time": "1767952803000",
      "updateTime": "1767952803000",
      "orderId": "2124136467689135001",
      "clientOrderId": "sl-mkt-001",
      "symbol": "BTC-SWAP-USDT",
      "price": "0",
      "leverage": "20",
      "origQty": "1",
      "executedQty": "0",
      "avgPrice": "0",
      "marginLocked": "5",
      "type": "STOP_PROFIT_LOSS_MARKET",
      "side": "SELL",
      "positionSide": "LONG",
      "timeInForce": "GTC",
      "status": "ORDER_NEW",
      "contractMultiplier": "0.001",
      "stopPrice": "92000",
      "triggerBy": "CONTRACT_PRICE",
      "stopOrderType": "STOP_LOSS",
      "stopType": "FIXED_STOP"
    },
    {
      "time": "1767952804000",
      "updateTime": "1767952804000",
      "orderId": "2124136467689135002",
      "clientOrderId": "trail-001",
      "symbol": "BTC-SWAP-USDT",
      "price": "0",
      "leverage": "20",
      "origQty": "1",
      "executedQty": "0",
      "avgPrice": "0",
      "marginLocked": "5",
      "type": "STOP_PROFIT_LOSS",
      "side": "SELL",
      "positionSide": "LONG",
      "timeInForce": "GTC",
      "status": "ORDER_NEW",
      "contractMultiplier": "0.001",
      "stopPrice": "0",
      "triggerBy": "CONTRACT_PRICE",
      "stopOrderType": "STOP_LOSS",
      "stopType": "TRAILING_STOP",
      "activePrice": "95000",
      "fallbackType": "RATE",
      "fallbackQuantity": "0.01",
      "activeStatus": 0
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
62
63
64
65
66
67
68
69
70
71
72
73
74
75
76
77
78
79
80
81
82
83
84
85
86
87
88
89
90
91
92
93
94
95
96
97
98
99
100
History plan orders (USER_DATA)
GET /api/v2/futures/history-algo-orders
Weight：5
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>NO<w:t>Filter; empty = all
orderId<w:t>LONG<w:t>NO<w:t>default 0
stopCategory<w:t>STRING<w:t>NO<w:t>STOP (plan orders only) or STOP_PROFIT_LOSS (TP/SL only); if omitted, results are plan STOP only (excludes TP/SL)
startTime<w:t>LONG<w:t>NO<w:t>Start (ms); default rolling window if <= 0
endTime<w:t>LONG<w:t>NO<w:t>End (ms)
limit<w:t>INT<w:t>NO<w:t>default 20, min 1, max 1000
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response
data is an array of plan / TP-SL order rows:

Per-row type: same four values and meanings as Get one plan order → Response — STOP, STOP_MARKET, STOP_PROFIT_LOSS, STOP_PROFIT_LOSS_MARKET. Which rows appear is determined by request stopCategory (it filters the row set only; it does not change per-row enum semantics).
TP/SL rows also carry stopOrderType (TAKE_PROFIT, STOP_LOSS) and stopType (FIXED_STOP, TRAILING_STOP); trailing rows may include activePrice, fallbackType (RATE, PRICE), fallbackQuantity, activeStatus, etc., when applicable.

{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "time": "1767952799216",
      "updateTime": "1767952799216",
      "orderId": "2124136467689134848",
      "clientOrderId": "1767952799112",
      "symbol": "BTC-SWAP-USDT",
      "price": "0",
      "leverage": "20",
      "origQty": "2",
      "executedQty": "0",
      "avgPrice": "0",
      "marginLocked": "10",
      "type": "STOP_MARKET",
      "side": "BUY",
      "positionSide": "LONG",
      "timeInForce": "GTC",
      "status": "ORDER_NEW",
      "contractMultiplier": "0.001",
      "stopPrice": "95000",
      "triggerBy": "CONTRACT_PRICE"
    },
    {
      "time": "1767952801000",
      "updateTime": "1767952802000",
      "orderId": "2124136467689135000",
      "clientOrderId": "tp-001",
      "symbol": "BTC-SWAP-USDT",
      "price": "100000",
      "leverage": "20",
      "origQty": "1",
      "executedQty": "0",
      "avgPrice": "0",
      "marginLocked": "5",
      "type": "STOP_PROFIT_LOSS",
      "side": "SELL",
      "positionSide": "LONG",
      "timeInForce": "GTC",
      "status": "ORDER_NEW",
      "contractMultiplier": "0.001",
      "stopPrice": "99000",
      "triggerBy": "MARK_PRICE",
      "stopOrderType": "TAKE_PROFIT",
      "stopType": "FIXED_STOP"
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
Batch cancel plan orders (TRADE)
DELETE /api/v2/futures/batch-cancel-algo-orders
Weight：3
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>Comma-separated symbol ids
stopCategory<w:t>STRING<w:t>YES<w:t>Required: STOP (cancel plan orders for the symbol) or STOP_PROFIT_LOSS (cancel TP/SL rows for the symbol)
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response
data is always null (no order payload, no string enums on this route).


{
  "code": 200,
  "msg": "success",
  "data": null
}
1
2
3
4
5
Change leverage (TRADE)
POST /api/v2/futures/leverage
Weight：1
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
symbol<w:t>STRING<w:t>YES<w:t>Contract symbol id
leverage<w:t>STRING<w:t>YES<w:t>Target leverage (string in request)
category<w:t>STRING<w:t>NO<w:t>USDT-M: USDT, USDC-M: USDC; default USDT
timestamp<w:t>LONG<w:t>YES<w:t>—
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Response
data reflects the new leverage setting; no string-enum fields (leverage is numeric).


{
  "code": 200,
  "msg": "success",
  "data": {
    "symbolId": "BTC-SWAP-USDT",
    "leverage": 20
  }
}
1
2
3
4
5
6
7
8
Last updated: 5/13/26, 7:27 PM


Skip to content



Menu
On this page
Sidebar Navigation
Integration Guide
Introduction

Basic Information

Code Examples

Changelog

Spot
Examples

Wallet Endpoints

Market Data Endpoints

Websocket Market Streams

Spot Account/Trade

Account/Trades (v2)

User Data Streams

Error Codes

USDT-M
Examples

Market Data Endpoints

Websocket Market Streams

Account/Trades Endpoints

Account/Trades (v2)

User Data Streams

Error Codes

Copy Trading
Examples

Leader Endpoints

Follower Endpoints

User Data Streams
The base API endpoint is : https://api.toobit.com
A User Data Stream listenKey is valid for 60 minutes after creation.
Doing a PUT on a listenKey will extend its validity for 60 minutes.
Doing a DELETE on a listenKey will close the stream and invalidate the listenKey .
Doing a POST on an account with an active listenKey will return the currently active listenKey and extend its validity for 60 minutes.
The base websocket endpoint is: wss://stream.toobit.com
User feeds are accessible via /api/v1/ws/<listenKey> (e.g. wss://#HOST/api/v1/ws/<listenKey>)
User feed payloads are not guaranteed to be up during busy times; make sure to order updates with E
Start User Data Stream (USER_STREAM)
POST /api/v1/listenKey
Start a new user data stream. The stream will close after 60 minutes unless a keepalive is sent.

Weight： 1
Response：


{
  "listenKey": "1A9LWJjuMwKWYP4QQPw34GRm8gz3x5AephXSuqcDef1RnzoBVhEeGE963CoS1Sgj"
}
1
2
3
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Keepalive User Data Stream (USER_STREAM)
PUT /api/v1/listenKey
Keepalive a user data stream to prevent a time out. User data streams will close after 60 minutes. It's recommended to send a ping about every 60 minutes.

Weight： 1
Response：


{}
1
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
listenKey<w:t>STRING<w:t>YES<w:t>listenKey
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
Close User Data Stream (USER_STREAM)
DELETE /api/v1/listenKey
Weight： 1
Response：


{}
1
Parameters
Name<w:t>Type<w:t>Mandatory<w:t>Description
listenKey<w:t>STRING<w:t>YES<w:t>listenKey
category<w:t>ENUM<w:t>NO<w:t>USDC-M Futures=USDC, Default=USDT-M Futures.
timestamp<w:t>LONG<w:t>YES<w:t>timestamp
recvWindow<w:t>LONG<w:t>NO<w:t>recv window
User Data Stream Expired
/api/v1/ws/
Response


{
  "eventTime": 1767536100360,//event time
  "eventType": "listenKeyWillExpire",//event type
  "listenKey": "zUeuthxEYbqupygpYQKPTgDemAQWXJdrpzVhmVOSKSDUzMWzIAVgPgYbDLuxBpNu"//listenkey
}
1
2
3
4
5
push notifications will begin 5 minutes before the expiration date, and will be sent every minute.
Event: Balance
The event type of the account update event is fixed to outboundContractAccountInfo

Payload


[
  {
    "e": "outboundContractAccountInfo",                // event type
    "E": 1564745798939,                   // event time
    "T": true ,                  // Can trade 
    "W": true ,                  // Can withdraw 
    "D": true ,                  // Can deposit 
    "B": [                        // Balances changed 
      {
        "a": "LTC",               // Asset 
        "f": "17366.18538083",    // Free amount 
        "l": "0.00000000"         // Locked amount 
      }
    ]
  }
]
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
When the account information changes, this event will be pushed:
This event will only be pushed when there is a change in account information
Event: Position Update
Position Payload


[
    {
        "e": "outboundContractPositionInfo",                // Event type 
        "E": "1668693440976",             // Event time 
        "A": "1270447370291795457",      // account id
        "s": "BTC-SWAP-USDT",             // Symbol 
        "S": "LONG",                      // side 
        "p": "441.0",                     // avg price
        "P": "1291488620385157122",       // total position
        "a": "1000",                      // Available positions
        "f": "1291488620167835136",       // liquidation price
        "m": "18.2",                      // Position Margin
        "r": "44",                        // Realized profit and loss
        "mt": "CROSS",                     // Position type
        "rr": "89",                       // riskRate Account risk rate reaches 100 to trigger forced liquidation
        "up": "12",                      // unrealizedPnL 
        "pr": "0.003",                  //  Profit rate of current position
        "pv": "123",                    //  Position value (USDT)
        "v": "10"                     // leverage
    }
]
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
position information: push only when there is a change in the symbol position.
The field mt represents the position type CROSS cross margin; ISOLATED isolated margin
Event: Order
This type of event will be pushed when a new order is created, an order has a new deal, or a new state change.

Order Payload


[
  {
    "e": "contractExecutionReport",        // Event type 
    "E": 1499405658658,            // Event time 
    "s": "BTC-SWAP-USDT",          // Symbol 
    "c": 1000087761,               // Client order ID 
    "C": true,                     // Is close order 
    "S": "BUY",                    // Side 
    "o": "LIMIT",                  // Order type 
    "f": "GTC",                    // Time in force 
    "q": "1.00000000",             // Order quantity （contracts)
    "p": "0.10264410",             // Order price 
    "pt": "MARKET",                // price type  INPUT: user input price.  MARKET: market price
    "X": "NEW",                    // Current order status 
    "i": 4293153,                  // Order ID 
    "l": "0.00000000",             // Last executed quantity （contracts)
    "z": "0.00000000",             // Cumulative filled quantity （contracts)
    "L": "0.00000000",             // Last executed price 
    "n": "0",                      // Commission amount 
    "N": null,                     // Commission asset 
    "u": true,                     // Is the trade normal, ignore for now 
    "w": true,                     // Is the order working Stops will have
    "m": false,                    // Is this trade the maker side
    "mt": "CROSS",                 // Position type
    "O": 1499405658657,            // Order creation time 
    "Z": "0.00000000",             // Cumulative quote asset transacted quantity 
    "v": "20",                     // leverage 
    "U": 1499405658658,            // update order time
    "rp": "-4.3058"                // Clos Order Cumulative realisedPnl
  }
]
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
The average price can be found by dividing Z by z
The field mt represents the position type CROSS cross margin; ISOLATED isolated margin
Side
BUY
SELL
Order Type
MARKET
LIMIT
STOP_LIMIT Plan entrusted
Price Type
INPUT user input price
MARKET market price
Order Status
NEW

PARTIALLY_FILLED

FILLED

CANCELED

PENDING_CANCEL

REJECTED

Time in force
GTC
IOC
FOK
Plan order or stop loss order status
ORDER_NEW
ORDER_FILLED
ORDER_REJECTED
ORDER_CANCELED
ORDER_FAILED
Take profit and stop loss type
STOP_LONG_PROFIT Long position take profit
STOP_LONG_LOSS Long position stop loss
STOP_SHORT_PROFIT Plan entrustment-short position take profit
STOP_SHORT_LOSS Plan order - short position stop loss
Event: Trade Update
Will push when there is a deal

Trade Payload


[
    {
        "e": "ticketInfo",                // Event type 
        "E": "1668693440976",             // Event time 
        "s": "BTC-SWAP-USDT",             // Symbol 
        "q": "0.205",                     // quantity 
        "t": "1668693440899",             // time 
        "p": "441.0",                     // price 
        "T": "1291488620385157122",       // ticketId
        "o": "1291488620167835136",       // orderId 
        "c": "1668693440093",             // clientOrderId 
        "a": "1286424214388204801",       // accountId 
        "m": false,                       // isMaker 
        "S": "SELL"                       // side  
    }
]
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
TP/SL Order
All planned orders will be pushed to you, and stop-loss and take-profit orders will be filtered based on the value of planOrderType.

Payload


{
  "eventType": "planExecutionReport",//event type
  "time": "1767521501840",//order created time
  "orderId": "2120518483020142848",//order id
  "accountId": "1752238453238626818",//account id
  "brokerUserId": "4910055547259955197",//user id
  "clientOrderId": "1767521500131",//User order ID (subscribed by the user when placing an order via API; generated by the system when placing an order on the page).
  "symbolId": "BTC-SWAP-USDT",// symbol id
  "symbolName": "BTCUSDT",//symbol name
  "baseTokenId": "BTC-SWAP-USDT",//baseTokenId
  "baseTokenName": "BTC-SWAP-USDT",
  "quoteTokenId": "USDT",//quote token
  "quoteTokenName": "USDT",//quote token name
  "price": "0",//Order price
  "origQty": "10",//order quantity
  "type": "STOP",//order type-STOP Plan commission（fixed value）
  "planOrderType": "STOP_SHORT_PROFIT",//plan order type STOP_LONG_PROFIT, STOP_LONG_LOSS,STOP_SHORT_PROFIT, STOP_SHORT_LOSS, STOP_COMMON
  "side": "BUY_CLOSE",//BUY_OPEN SELL_OPEN BUY_CLOSE SELL_CLOSE
  "status": "ORDER_NEW",//ORDER_NEW -wait to trigger，ORDER_FILLED -triggered ORDER_REJECTED -trigger failed ORDER_CANCELED -canceled ORDER_FAILED  ORDER_NOT_EFFECTIVE -SP or SL doesn't take effect
  "triggerPrice": "91446",//trigger price
  "quotePrice": "91493.1",//quote token price
  "executedOrderId": "0",//There will be a value after triggering.
  "executedPrice": "0",//There will be a value after triggering.
  "executedQty": "0",//There will be a value after triggering.
  "updateTime": "1767521529483",
  "priceType": "MARKET_PRICE",//INPUT MARKET_PRICE
  "quotePriceType": 0,//Trigger price type: 0 - Latest price, 1 - Index price, 2 - Mark price
  "leverage": "10",
  "spOrderId": "2120518483020142848",//Take Profit Order ID
  "slOrderId": "0",//Stop Loss Order ID
  "openOrdinaryOrderId": "2120518481434695937",//Common order ID
  "openOrderId": "0",//Opening order ID: not 0 in split position mode, 0 in combined position mode.
  "triggerType": 0,//0 fixed trigger, 1 moving trigger
  "activePrice": "0",//Trailing stop-loss/take-profit activation price (value only applies when activated)
  "fallType": 0,//Trailing stop-loss/take-profit trigger price pullback type: 0 percentage, 1 spread
  "fallQuantity": "0",//The value is always 0, so stop-loss and take-profit orders are not used.
  "activeStatus": 0,//Trailing stop-loss and take-profit activation status: 0 Not activated, 1 Activated
  "triggerDelay": 0,//Trigger delay (seconds)
  "marginType": "CROSS",//Position type CROSS，ISOLATED
  "isGuaranteedPrice": 0,//Is the price guaranteed? 1 Yes, 0 No
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
Last updated: 2/7/26, 4:52 AM

Pager
Previous page
Account/Trades (v2)
Next page
Error Codes

Skip to content



Menu
On this page
Sidebar Navigation
Integration Guide
Introduction

Basic Information

Code Examples

Changelog

Spot
Examples

Wallet Endpoints

Market Data Endpoints

Websocket Market Streams

Spot Account/Trade

Account/Trades (v2)

User Data Streams

Error Codes

USDT-M
Examples

Market Data Endpoints

Websocket Market Streams

Account/Trades Endpoints

Account/Trades (v2)

User Data Streams

Error Codes

Copy Trading
Examples

Leader Endpoints

Follower Endpoints

Error Codes
Errors consist of two parts: an error code and a message. Codes are universal, but messages can vary.

The error JSON payload


{
  "code": -1121,
  "msg": "Invalid symbol."
}
1
2
3
4
10xx - General Server or Network issues
-1000 UNKNOWN
An unknown error occurred while processing the request.
-1001 DISCONNECTED
Internal error; unable to process your request. Please try again.
-1002 UNAUTHORIZED
You are not authorized to execute this request.
-1003 TOO_MANY_REQUESTS
Too many requests queued.
Too much request weight used; current limit is %s request weight per %s. Please use WebSocket Streams for live updates to avoid polling the API.
Way too much request weight used; IP banned until %s. Please use WebSocket Streams for live updates to avoid bans.
-1005 NO_PERMISSION
No Permission
-1006 UNEXPECTED_RESP
An unexpected response was received from the message bus. Execution status unknown.
-1007 TIMEOUT
Timeout waiting for response from backend server. Send status unknown; execution status unknown.
-1014 UNKNOWN_ORDER_COMPOSITION
Unsupported order combination.
-1015 TOO_MANY_ORDERS
Reach the rate limit .Please slow down your request speed.
Too many new orders.
Too many new orders; current limit is %s orders per %s.
-1016 SERVICE_SHUTTING_DOWN
This service is no longer available.
-1020 UNSUPPORTED_OPERATION
This operation is not supported.
-1021 INVALID_TIMESTAMP
Timestamp for this request is outside of the recvWindow.
Timestamp for this request was 1000ms ahead of the server's time.
Please check the difference between your local time and server time .
-1022 INVALID_SIGNATURE
Signature for this request is not valid.
-1023 BIND_IP_WHITE_LIST_FIRST
Please set IP whitelist before using API
-1031 FEATURE_SUSPENDED
The feature has been suspended
11xx - 2xxx Request issues
-1100 ILLEGAL_CHARS
Illegal characters found in a parameter.
Illegal characters found in parameter '%s'; legal range is '%s'.
-1101 TOO_MANY_PARAMETERS
Too many parameters sent for this endpoint.
Too many parameters; expected '%s' and received '%s'.
Duplicate values for a parameter detected.
-1102 MANDATORY_PARAM_EMPTY_OR_MALFORMED
A mandatory parameter was not sent, was empty/null, or malformed.
Mandatory parameter '%s' was not sent, was empty/null, or malformed.
Param '%s' or '%s' must be sent, but both were empty/null!
-1103 UNKNOWN_PARAM
An unknown parameter was sent.
In BBEx Open Api , each request requires at least one parameter. {Timestamp}.
-1104 UNREAD_PARAMETERS
Not all sent parameters were read.
Not all sent parameters were read; read '%s' parameter(s) but was sent '%s'.
-1105 PARAM_EMPTY
A parameter was empty.
Parameter '%s' was empty.
-1106 PARAM_NOT_REQUIRED
A parameter was sent when not required.
Parameter '%s' sent when not required.
-1107 API_KEY_EMPTY
The accessKey is missing from the request header or parameters, or the accessKey is not in the correct format.
-1111 BAD_PRECISION
Precision is over the maximum defined for this asset.
-1112 NO_DEPTH
No orders on book for symbol.
-1114 TIF_NOT_REQUIRED
TimeInForce parameter sent when not required.
-1115 INVALID_TIF
Invalid timeInForce.
In the current version, this parameter is either empty or GTC.
-1116 INVALID_ORDER_TYPE
Invalid orderType.
In the current version , ORDER_TYPE values is LIMIT or MARKET.
-1117 INVALID_SIDE
Invalid side.
ORDER_SIDE values is BUY or SELL
-1118 EMPTY_NEW_CL_ORD_ID
New client order ID was empty.
-1119 EMPTY_ORG_CL_ORD_ID
Original client order ID was empty.
-1120 BAD_INTERVAL
Invalid interval.
-1121 BAD_SYMBOL
Invalid symbol.
-1125 INVALID_LISTEN_KEY
This listenKey does not exist.
-1127 MORE_THAN_XX_HOURS
Lookup interval is too big.
More than %s hours between startTime and endTime.
-1128 OPTIONAL_PARAMS_BAD_COMBO
Combination of optional parameters invalid.
-1129 ORDER_DOWNLOAD_TIME_RANGE_EXCEED_ONE_YEAR
The time range cannot exceed one year.
-1130 INVALID_PARAMETER
Invalid data sent for a parameter.
Data sent for paramter '%s' is not valid.
-1131 INSUFFICIENT_BALANCE
Balance insufficient
-1132 ORDER_PRICE_TOO_HIGH
Order price too high.
-1133 ORDER_PRICE_TOO_SMALL
Order price lower than the minimum,please check general broker info.
-1134 ORDER_PRICE_PRECISION_TOO_LONG
Order price decimal too long,please check general broker info.
-1135 ORDER_QUANTITY_TOO_BIG
Order quantity too large.
-1136 ORDER_QUANTITY_TOO_SMALL
Order quantity lower than the minimum.
-1137 ORDER_QUANTITY_PRECISION_TOO_LONG
Order quantity decimal too long.
-1138 ORDER_PRICE_WAVE_EXCEED
Order price exceeds permissible range.
-1139 ORDER_HAS_FILLED
Order has been filled.
-1140 ORDER_AMOUNT_TOO_SMALL
Transaction amount lower than the minimum.
-1141 ORDER_DUPLICATED
Duplicate clientOrderId
-1142 ORDER_CANCELLED
Order has been canceled
-1143 ORDER_NOT_FOUND_ON_ORDER_BOOK
Cannot be found on order book
-1144 ORDER_LOCKED
Order has been locked
-1145 ORDER_NOT_SUPPORT_CANCELLATION
This order type does not support cancellation
-1146 ORDER_CREATION_TIMEOUT
Order creation timeout
-1147 ORDER_CANCELLATION_TIMEOUT
Order cancellation timeout
-1148 ORDER_AMOUNT_PRECISION_TOO_LONG
Market order amount decimal too long
-1149 CREATE_ORDER_FAILED
Create order failed
-1150 CANCEL_ORDER_FAILED
Cancel order failed
-1151 SYMBOL_PROHIBIT_ORDER
The trading pair is not open yet
-1153 USER_NOT_EXIST
User not exist
-1156 ORDER_QUANTITY_INVALID
Order quantity invalid
-1157 SYMBOL_API_TRADING_NOT_AVAILABLE
The trading pair is not available for api trading
-1158 CREATE_LIMIT_MAKER_ORDER_FAILED
create limit maker order failed
-1161 REDUCE_MARGIN_FORBIDDEN
Reduce margin forbidden
-1164 ERROR_AUTO_ADD_MARGIN
Auto add margin error
-1165 INVALID_STOP_TYPE
Invalid stopType.
-1166 INVALID_CALLBACK_TYPE
Invalid callbackType.
-1170 FINANCE_ACCOUNT_EXIST
finance account exist.
-1171 ACCOUNT_NOT_EXIST
account not exist.
-1172 BALANCE_TRANSFER_FAILED
Balance transfer failed.
-1181 WITHDRAW_NOT_ALLOW
Currently not allowed to withdraw.
-1182 DEPOSIT_NOT_ALLOW
Currently not allowed to deposit.
-1193 ORDER_COUNT_LIMIT
Create order count limit
-1194 MARKET_ORDER_FORBIDDEN
Create market order forbidden
-1195 LIMIT_ORDER_PRICE_TOO_SMALL
Create limit order price too small
-1196 LIMIT_ORDER_PRICE_TOO_BIG
Create limit order price too big
-1197 LIMIT_ORDER_BUY_PRICE_TOO_BIG
Create limit order buy price too big
-1198 LIMIT_ORDER_SELL_PRICE_TOO_SMALL
Create limit order sell price too small
-1199 ORDER_BUY_QUANTITY_TOO_SMALL
Create order buy quantity too small
-1200 ORDER_BUY_QUANTITY_TOO_BIG
Create order buy quantity too big
-1201 LIMIT_ORDER_SELL_PRICE_TOO_BIG
Create limit order sell price too big
-1202 ORDER_SELL_QUANTITY_TOO_SMALL
Create order sell quantity too small
-1203 ORDER_SELL_QUANTITY_TOO_BIG
Create order sell quantity too big
-1204 NOT_AUTHORIZED_ACCOUNT
account not authorized
-1205 SAME_ACCOUNT_NOT_TRANSFER
same account not transfer
-1206 ORDER_AMOUNT_TOO_BIG
Transaction amount bigger than the max.
-1207 PLAN_ORDER_COUNT_LIMIT
planOrder count limit.
-1208 STOP_PROFIT_LOSS_ORDER_COUNT_LIMIT
stopProfitLoss order count limit.
-1209 STOP_PROFIT_LOSS_POSITION_TOTAL_LIMIT
stopProfitLoss order position limit.
-1210 DYNAMIC_STOP_PROFIT_LONG_FALL_QUANTITY_HIGH
dynamic stop profit long fallQuantity high.
-1211 DYNAMIC_STOP_PROFIT_LONG_ACTIVE_PRICE_LOW
dynamic stop profit activePrice low.
-1212 DYNAMIC_STOP_PROFIT_SHORT_ACTIVE_PRICE_HIGH
dynamic stop profit activePrice high.
-1213 ACCOUNT_SYMBOL_NOT_MATCH
Account symbol does not match
-1214 ORDER_FUTURES_TRADE_BAN_OPEN
No opening trades
-1215 ORDER_FUTURES_TRADE_BAN_CLOSE
No closing trades
-1216 TRANSFER_LIMIT_FAILED
Trigger transfer limit failed
-1217 STOP_ORDER_BUY_PRICE_TOO_BIG
Create stop order buy price too big
-1300 DUPLICATED_TRANSFER_ID
Duplicate transferId
-2010 NEW_ORDER_REJECTED
New order rejected
-2011 CANCEL_REJECTED
Cancel order rejected
-2013 NO_SUCH_ORDER
Order does not exist.
-2014 BAD_API_KEY_FMT
API-key format invalid.
-2015 REJECTED_MBX_KEY
Invalid API-key, IP, or permissions for action.
-2016 NO_TRADING_WINDOW
No trading window could be found for the symbol. Try ticker/24hrs instead.
-2017 API_KEY_EXPIRED
The API key has expired. Please update your API key immediately.
-2018 API_KEY_SUSPENDED
API triggered risk control restrictions have been suspended, if you have any questions, please contact support@toobit.com.
3xxx - Filters and other Issues
-3000 OPTION_NOT_EXIST
Option not exist.
-3001 OPTION_HAS_EXPIRED
The option has expired.
-3002 OPTION_ORDER_POSITION_LIMIT
Order failed: position exceeded limit
-3050 CREATE_API_KEY_EXCEED_LIMIT
The ApiKey corresponding to the account already exists
-3051 SUB_USER_TOTAL_ASSETS_EXCEEDING
The sub-user has assets are not allowed to be deleted
-3052 SUB_USER_ID_ERROR
sub-user id error
-3101 OPEN_MARGIN_ACCOUNT_ERROR
Open margin account error
-3102 GET_MARGIN_SAFETY_ERROR
Get margin safety error
-3103 RISK_IS_NOT_EXIT
Risk config is not exit
-3105 MARGIN_TOKEN_NOT_BORROW
Token can not borrow
-3107 MARGIN_TOKEN_NOT_WITHDRAW
Token can not withdraw
-3108 GET_AVAIL_WITHDRAW_ERROR
Get token avail withdraw error
-3109 MARGIN_WITHDRAW_ERROR
Margin withdraw failed
-3110 MARGIN_AVAIL_WITHDRAW_NOT_ENOUGH_FAILED
Margin avail withdraw not enough failed
-3116 REPAY_ERROR
Repay fail
-3117 GET_MARGIN_ALL_POSITION_ERROR
Get margin all position fail
-3120 GET_REPAY_ORDER_ERROR
Get repay order fail
-3124 POSITION_AND_ORDER_DATA_ERROR
Position and order data error
-3125 POSITION_SIZE_CANNOT_MEET_TARGET_LEVERAGE_ERROR
Position size cannot meet target leverage
-3126 ADJUST_LEVERAGE_FAIL
Adjust leverage fail
-3127 ADJUST_LEVERAGE_TIMEOUT
Adjust leverage timeout
-3128 ADJUST_MARGIN_TYPE_CHECK_FAILED
The margin mode cannot be changed while you have an open order/position
-3129 CONE_FUTURES_CHANGE_POSITION_TYPE_ERROR
Cone futures change position type error
-3130 ORDER_REJECT_FUTURES_ORDER_MARGIN_INSUFFICIENT
Order margin insufficient
-3131 LEVERAGE_REDUCTION_IS_NOT_SUPPORTED
Leverage reduction is not supported in Isolated Margin Mode with open positions.
-3132 ORDER_FUTURES_LEVERAGE_INVALID
Maximum allowed leverage reached, please lower your leverage.
-3133 LEVERAGE_OPEN_ORDERS_EXCEEDS_THE_LIMIT
The number of open orders exceeds the limit.
-3136 QUICK_SYMBOL_ACTIVITY_LIMIT_BUY_IOC_ONLY
Quick symbol activity only limit/buy/ioc order is supported
-3137 OPEN_COUNTDOWN_NOT_OVER
Open countdown is not over
-3138 OPEN_ACTIVITY_PRE_HOLD_HANDLING
Open activity pre_hold is handling
-3139 OPEN_ACTIVITY_MAX_AMOUNT_LIMIT
Open activity max amount limit
-3140 OPEN_ACTIVITY_MIN_AMOUNT_LIMIT
Open activity min amount limit
-3141 ORDER_SPL_ERR_LONG_STOP_PROFIT_PRICE
Invalid long stop profit price.
-3142 ORDER_SPL_ERR_LONG_STOP_LOSS_PRICE
Invalid long stop loss price.
-3143 ORDER_SPL_ERR_SHORT_STOP_PROFIT_PRICE
Invalid short stop profit price.
-3144 ORDER_SPL_ERR_SHORT_STOP_LOSS_PRICE
Invalid short stop loss price.
-3145 NO_POSITION
No position, Please confirm your position direction.
-3147 PREVIOUS_TRANSFER_IS_BEING_PROCESSED
previous transfer is being processed. please try again later.
-3148 POSITION_MAX_FUTURES_RISK_LIMIT
create order exceeds max futures risk limit.
-3149 REDUCE_MARGIN_INVALID
The reduction in margin is unlawful.
-3150 MARGIN_ADJUSTMENT_IS_NOT_SUPPORTED_FOR_CROSS
cross position margin adjustments are not supported.
-3151 SEPARATE_POSITION_MODE_NOT_SUPPORTED
Separate position mode is not supported.
-3152 SEPARATE_POSITION_WITH_WRONG_MODE
Separate-position mismatch: position mode must be SEPARATE.
-3153 WHOLE_POSITION_WITH_WRONG_MODE
Whole-position mismatch: position mode must be WHOLE.
Last updated: 6/8/26, 11:55 AM

Pager
Previous page
User Data Streams
Next page
Examples
