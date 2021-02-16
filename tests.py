from CryptoPayment import CryptoPayment, convert
from tinydb import TinyDB, where
import time
import threading

if __name__ == '__main__':
    cch = CryptoPayment(test=True)
    cch.clearDB()    
    cch.wallet_refresh_time = 0
    test_wallet_type = 'litecoin'

    test_results = {
        'creating_wallets': None,
        'deleting_wallets': None,
        'creating_transactions': None,
        'deleting_transactions': None,
        'checking_transactions': None,
        'display_tethered_transactions': None

    }
    # user may add wallets to the system
    wallet_list = ['0x1231kasd', '0x231231skdasd', '0x1231kasdcxzcas234']
    for wallet in wallet_list:
        try:
            cch.addWallet(wallet, test_wallet_type)
        except:
            pass
    

    test_wallet_list = cch.showWallets()
    if len(wallet_list) == len(test_wallet_list):
        print('!!creates wallets as usual')
        test_results['creating_wallets'] = True
    else:
        print(f'!#!expected to get {len(wallet_list)} instead of {len(test_wallet_list)}')
        test_results['creating_wallets'] = False

    # new transaction check
    workers_list = []
    for t in range(2):
        for i in range(3):
            worker = threading.Thread(target=cch.newTransaction, args=(test_wallet_type, 1.0242134))
            worker.start()
            workers_list.append(worker)
    for worker in workers_list:
        worker.join()

    transactions = cch.active_transactions.all()
    transactions_failures = 0
    for transaction in transactions:
        if len(list(filter( lambda x: x['protocol_units'] == transaction['protocol_units'] and x['wallet_adr'] == transaction['wallet_adr'], transactions))) != 1:
            print('number of transactions are not equal to 1')
            transactions_failures+=1
    
    if transactions_failures == 0:
        print('!!transactions are creating succesfully')
        test_results['creating_transactions'] = True
    else:
        print('!#!some troubles happend on creating transactions')
        test_results['creating_transactions'] = False

    # transactions may be aborted
    previous_amount_of_transactions = len(transactions)
    cch.deleteTransaction(transactions[0]['pk'])
    transactions = cch.active_transactions.all()
    if previous_amount_of_transactions > len(transactions):
        print('!!removes transactions as usual')
        test_results['deleting_transactions'] = True
    else:
        print('!!got an error while was removing transactions')
        test_results['deleting_transactions'] = False

    #user may remove wallets from the system
    cch.deleteWallet(wallet_list[0])
    test_wallet_list = cch.showWallets()
    if len(wallet_list) == len(test_wallet_list)+1:
        print('!!removes wallets as usual')
        test_results['deleting_wallets'] = True

    else:
        print(f'expected to get {len(wallet_list)} instead of {len(test_wallet_list)+1}')
        test_results['deleting_wallets'] = False

    #check transaction
    transaction = cch.active_transactions.all()[0]
    result1 = cch.checkActiveTransaction(transaction['pk'])
    time.sleep(1)
    if len( cch.finished_transactions.search(where('wallet_adr') == transaction['wallet_adr']) ) != 0:
        print(f'some of the transactions were marked as finished, none of the transactions supposed to be finished')
    # check if any of the current transaction is finished
    result2 = cch.checkActiveTransaction(transaction['pk'])
    if result1 is False and result2 is True:
        print(f'!!checking transaction test passed')
    else:
        print(f'!#!checking transaction test failed')
    time.sleep(2)

    # add a new transaction
    test_protocol_units = convert(test_wallet_type, protocol_units=cch.checker.test_transactions[-1]['balance_change'])
    test_new_transaction = cch.newTransaction(test_wallet_type, test_protocol_units)
    # check it, must be false
    transaction_result = cch.checkActiveTransaction(test_new_transaction['pk'])
    
    
    # showTetheredTransactions
    results = cch.showTetheredTransactions(test_new_transaction['wallet_adr'],test_wallet_type)
    if len(list(filter(lambda transaction: transaction['tethered_transaction'] != [], results))) > 0:
        print(f'showTetheredTransactions seems to be working as usual')
    else:
        print(f'showTetheredTransactions seems to have some troubles')

    # erase db
    cch.clearDB()    
    print('tests finished')
    print(test_results)

# test_transaction = {"currency":"usdt", 'amount': 100.00}
# test_transaction2 = {"currency":"usdt", 'amount': 102.00}
# test_results = []
# for i in range(12):
#     test_results.append(registerReplenish(test_transaction) )
# for i in range(14):
#     test_results.append(registerReplenish(test_transaction2) )
# for i in test_results:
#     print(i)

# deleteWallet(wallet_adr='', wallet_type=''):
