# Purpose of the project
- First of all, I'd like to give all the users opportunity to integrate crypto payment to their services
## Usage

# traditional as a service
- add an api key using `service name`, using some method?
- install requests, flask, tinydb
- run tests if neccesary?
- run python main.py
- add wallets to use
- use!
# alternative as a libary for own backend
- copy the `cryptoChecker.py`
- install requests, tinydb
- `from cryptoChecker import CryptoChecker` in your project
- add an api key using `service name`, using some method?
- watch the examples in the original `main.py`


## CryptoPayment
description of the class


# 

- thx blockchair for their API

## todo

# major
- add timechecker to the cryptopayment class, so if the time on the machine is incorrect, it's going to be syncronised through some 3rd party api
<!-- - add a function which will collect all the transactions from the wallet and then tells which transaction was tethered with the payment system or not -->
- complete tests // check the blockchair api by user
<!-- - check the difference in time between the blockchair and the local time? // UTC everywhere -->
<!-- - gitnoire -->
<!-- - deploy -->
- cch.syncWalletAndActiveTransactions # update last checked time put it in the end of function, it's in the beginning for now due it'll prevent the script from checking the wallet twice at the same time
- if the 2 transactions from the same wallet are called at the same time, second one need to wait till the first call will be finished, then check if the transaction status
- add some temp and some limits to it(1000 records for example) to it, so it'll reduce the amount of database calls and increase perfomance in total
- check the transactions on the wallet remove
- add a limit for requests per second/minute/hour for blockchair api, so the service won't be spammed 
- add a `bool show_logs = True` to crypto payment class, someone needs them, someone is not?
- remove transactions manually?
- get the info about finished transactions, active transactions, for debug
- test with real wallets and transactions


# minor
- add checker for the cryptowallets numbers, so users couldn't input the incorrect wallet numbers + checker for the existance of the wallet?
- add an ochered' for checking the transactions, let's say user would like to check the transaction at 14:14, but the payment hasn't been succeed, it's gonna be added to an ochered', so it'll be checked later at ~14:19, ~14:24, ~14:29
- frontend
- allow user to choose custom NoSQL database instead of tinydb
- notifications via webhooks

# future plans
- use some native method instad of using 3rd party api for checking the transactions, it'll add an ability to create custom wallets to proceed the transactions
- more currencies
