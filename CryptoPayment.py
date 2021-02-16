# https://tinydb.readthedocs.io/en/latest/usage.html#tables
# https://tinydb.readthedocs.io/en/latest/api.html
import time
import random
import json
import requests
from datetime import datetime

from tinydb import TinyDB, where
from tinydb.operations import delete, add, set

# requests

WALLET_AVAILABLE_TYPES = ['litecoin', 'dogecoin', 'dashcoin']

def convert(crypto_type, currency_units = None, protocol_units = None):
    # btc/ ltc in satoshi, 1 btc = 100,000,000 satoshi 
    # eth is in wei, 1 ether = 1,000,000,000,000,000,000 wei (1018).
    # which is (amount * 1000000000)?
    # doge is (amount * 1)
    if not currency_units and not protocol_units: raise ValueError('no arguments passed')

    SPECEIAL_CURRENCIES = ['eth', 'dogecoin']
    
    if currency_units:
        if crypto_type == 'dogecoin':
            protocol_units = currency_units * 1
        elif crypto_type == 'eth':
            protocol_units = currency_units * 1000000000000000000
        else:
            protocol_units = currency_units * 100000000
        if protocol_units % 1 != 0: raise ValueError(f'{currency_units} is an incorrect number when trying to convert {crypto_type}, protocol units must become an integer after multiplying')
        return int(protocol_units)
    else:
        if crypto_type == 'dogecoin':
            currency_units = protocol_units / 1
        elif crypto_type == 'eth':
            currency_units = protocol_units / 1000000000000000000
        else:
            currency_units = protocol_units /  100000000 
        return currency_units

class CryptoPayment():
    def __init__(self, transaction_time_limit = 3600, wallet_refresh_time = 5, test=False, shuffle_walletes_on_new_transaction = False):
        '''
        desc
        '''
        if test is not True:      
            db = TinyDB('./CryptoChecker_db.json')
            self.checker = BlockchairApi()

        else:
            self.test_status = True
            db = TinyDB('./test_CryptoChecker_db.json')
            self.checker = FakeBlockchairApi(self)
        
        self.wallets = db.table('wallets')
        self.active_transactions = db.table('active_transactions')
        self.finished_transactions = db.table('finished_transactions')

        self.shuffle_walletes_on_new_transaction = shuffle_walletes_on_new_transaction # if you want to use random wallets instead of using the first added wallet 
        self.creating_transactions = False # used to prevent duplicates in newTransaction()
        self.wallet_refresh_time = wallet_refresh_time
    # clearDB
    def clearDB(self):
        '''
        removes all the objects from the database
        '''
        self.wallets.truncate()
        self.active_transactions.truncate()
        self.finished_transactions.truncate()
    # wallets
    def addWallet(self, wallet_adr=None, wallet_type=None):
        '''
        accepts the wallet_adr and the wallet_type

        returns the pk of if it was created successfully
        '''
        if not wallet_adr or not wallet_type: raise 'either wallet_adress or wallet_type is not specified'
        # check if wallet already exists in system
        if wallet_type not in WALLET_AVAILABLE_TYPES:
            print(f'unavailable wallet type {wallet_type}, WALLET_AVAILABLE_TYPES does not includes this type of wallet')
            raise f'unavailable wallet type {wallet_type}'
        if_already_exists = self.wallets.search( (where('wallet_adr') == wallet_adr))
        if len(if_already_exists) > 0: 
            print(f'wallet ${wallet_type}: ${wallet_adr}  already exists')
            raise ValueError(f'wallet ${wallet_type}: ${wallet_adr}  already exists')

        self.checker.checkIfWalletExists(wallet_adr, wallet_type)
        obj = {}
        obj['wallet_adr'] = wallet_adr
        obj['wallet_type'] = wallet_type
        obj['created_time'] = datetime.utcnow().timestamp()
        obj['last_checked_time'] = datetime.utcnow().timestamp()
        pk = self.wallets.insert(obj)
        self.wallets.update(set('pk', pk), doc_ids = [pk])
        print(f"wallet ${wallet_type} ${wallet_adr} was added, pk ${pk}")
        return pk
    
    def deleteWallet(self, wallet_adr=None):
        '''
        deletes the wallet and the active/finished? transactions

        accepts the adress of the wallet

        returns 1 on success
        '''
        if not wallet_adr: raise 'wallet adress is not specified'
        #delete wallet itself
        num_of_wallets = self.wallets.remove( (where('wallet_adr') == wallet_adr))

        #delete all active transactions
        num_of_transactions = self.active_transactions.remove( (where('wallet_adr') == wallet_adr) )

        #return 1, or error code on error(if wallet wasn't exist in the system)
        print(f'wallet ${wallet_adr} was deleted ${num_of_wallets} wallets,\ndeleted ${len(num_of_transactions)} active transactions')
        
        return 1
    
    def showWallets(self, wallet_type=None):
        '''
        accepts the wallet type as argument to fgilter the wallets by it's groups

        returns the wallets registred in system by this moment
        '''
        if wallet_type is None:
            wallets = self.wallets.all()
        else:
            wallets = self.wallets.search( where('wallet_type') == wallet_type)
        return wallets

    def syncWalletAndActiveTransactions(self, wallet, pk = None):
        '''
        checks the current wallet historical transactions and makes some active transactions as finished

        accepts wallet as a dict // document in future
        
        returns transaction_status is pk is passed
        '''
        

        # update last checked time 
        self.wallets.update(set('last_checked_time', datetime.utcnow().timestamp()), doc_ids = [wallet['pk']])

        # get the transactions from wallet
        transactions = self.checker.getHistoricalTransactions(wallet['wallet_adr'], wallet['wallet_type'])
        # sort the transactions which were created before the first active transaction
        active_transactions = self.active_transactions.search(where('wallet_adr') == wallet['wallet_adr'])
        lowerst_creation_date = min([transaction['created_time'] for transaction in active_transactions])
        transactions = list(filter(lambda transaction: transaction['timestamp'] > lowerst_creation_date, transactions ))
        # sort transactions with negative balance change
        transactions = list(filter(lambda transaction: transaction['balance_change'] > 0, transactions))
        #syncronise the transactions
        for transaction in active_transactions:
            # get the transactions with similar amount
            similar_transactions = list(filter(lambda historical_transaction: historical_transaction['balance_change'] == transaction['protocol_units'] ,transactions))
            # filter the transactions which were proceed before the transactions were created
            similar_transactions = list(filter(lambda historical_transaction: historical_transaction['timestamp'] > transaction['created_time'], similar_transactions))
            if len(similar_transactions) > 0:
                first_similar_transaction = similar_transactions[0]
                transaction['hash'] = first_similar_transaction['hash']
                transaction['finished'] = True
                transaction['original_pk'] = transaction['pk']
                transaction['created_time'] = datetime.utcnow().timestamp()
                pk = self.finished_transactions.insert(transaction)
                self.finished_transactions.update(set('pk', pk), doc_ids = [pk])
                self.active_transactions.remove(doc_ids=[transaction['pk']])
        return 1
    
    # transactions
    def deleteExpiredActiveTransactions(self):
        '''
        used to delete the expired transactions        
        '''        
        # get all the active transactions
        # for each transaction
        # if transaction time is more than 60*2 minutes
        # delete

        return 1
 
    def newTransaction(self, wallet_type=None, amount=None):
        '''
        ! need to be rewritten after `done = False`

        used to generate a new transaction for replenish

        accepts the wallet_type and the amount 

        returns the {transaction_pk, wallet, amount} of if the transaction was created successfully
        '''
        if not wallet_type or not amount: raise 'either wallet_type or amount is not specified'

        # use it once in 60 seconds, otherwise it's gonna spam it till death
        self.deleteExpiredActiveTransactions()
        while self.creating_transactions:
            time.sleep(0.05)
        self.creating_transactions = True

        active_transactions = self.active_transactions.search( (where('wallet_type') == wallet_type) )
        
        wallets = self.wallets.search( (where('wallet_type') == wallet_type) )
        if self.shuffle_walletes_on_new_transaction:
            random.shuffle(wallets)
        
        protocol_units = convert(wallet_type, amount)
        expected_protocol_units = protocol_units

        done = False

        while not done:
            wallet_to_use = None
            wallet_found = False
            for wallet in wallets:
                is_active = len(list(filter( lambda x: x['protocol_units'] == protocol_units and x['wallet_adr'] == wallet['wallet_adr'], active_transactions)))
                if is_active > 0: continue
                wallet_to_use = wallet
                wallet_found = True
            if wallet_found:
                # additional checks, because data may be changed

                # add transaction to transactions
                wallet_adr = wallet_to_use['wallet_adr']
                obj = {'wallet_adr': wallet_adr}
                obj['original_currency_units'] = amount # currency_units passed to the function
                obj['expected_protocol_units'] = expected_protocol_units # expected_protocol_units
                obj['protocol_units'] = protocol_units # actual protocol_units
                obj['currency_units'] = convert(crypto_type=wallet_type, protocol_units=protocol_units) # currency_units user needs to send in case of replenish
                obj['created_time'] = datetime.utcnow().timestamp()
                obj['wallet_type'] = wallet_type
                obj['finished'] = False

                pk = self.active_transactions.insert(obj)
                self.active_transactions.update(set('pk', pk), doc_ids = [pk])
                done = True
            else: 
                protocol_units += 1
        self.creating_transactions = False
        return {"pk": pk, "wallet_adr": wallet_adr, "currency_units": obj['currency_units']}

    def deleteTransaction(self, pk = None):
        '''
        deletes the active/finished? transactions

        accepts the pk of the transactions

        returns 1 on success
        '''
        if not pk: raise f'pk is not specified'
        self.active_transactions.remove( (where('pk') == pk) )
        print(f'transaction ${pk} was deleted successfully')

        return 1
    
    def showActiveTransactions(self, wallet_type=None):
        '''
        optional wallet_type
        
        if wallet_type is not presented, will return all the active transactions
        '''
        if not wallet_type:
            transactions = self.active_transactions.all()
        else:
            transactions = self.active_transactions.search( where('wallet_type') == wallet_type)
        return transactions

    def checkActiveTransaction(self, pk):
        '''
        checks the transaction

        accepts the pk of the transaction

        returns True if the transaction was succesful
        returns False if the transaction wasn't proceed
        '''
        # if the transaction was already completed
        transaction = self.finished_transactions.get(where('original_pk') == pk)
        if transaction is not None: return True
        # else
        transaction = self.active_transactions.get(doc_id=pk)
        if not transaction: raise ValueError(f'transaction {pk} wasnt found in the list of the active transactions, maybe it was expired')
        wallet = self.wallets.get( (where('wallet_adr') == transaction['wallet_adr'] ))
        need_to_recheck = datetime.utcnow().timestamp() - wallet['last_checked_time'] > self.wallet_refresh_time
        if need_to_recheck:
            self.syncWalletAndActiveTransactions(wallet = wallet, pk = pk)
        
        transaction_finished = self.finished_transactions.get(where('original_pk') == pk)
        if transaction_finished is not None: return True
        else: return False

    def showTetheredTransactions(self, wallet_address, wallet_type):
        '''
        accepts wallet_address and wallet type
        
        returns an array of historical transactions which looks like original one
        '''

        historical_transactions = self.checker.getHistoricalTransactions(wallet_address, wallet_type)  
        finished_transactions = self.finished_transactions.search(where('wallet_adr') == wallet_address)
        for historical_transaction in historical_transactions:
            tethered_transactions = list(filter(lambda transaction: transaction['hash'] == historical_transaction['hash'], finished_transactions))
            if tethered_transactions == []:
                historical_transaction['tethered_transaction'] = []
                continue
            historical_transaction['tethered_transaction'] = [obj['original_pk'] for obj in tethered_transactions]
        return historical_transactions

'''
transactions sample, also, the time will be converted to epochs,
so the original reply contains time as string "2021-02-05 11:51:28", script also adds "timestamp": 1612498449.0
litecoin sample transactions:
[
    {
        block_id: 1995470,
        hash: "eee2225117251ab3bd61d92e49e9ad380e87feb35e5f006ac978cd130b7b7bc8",
        time: "2021-02-05 11:51:28",
        balance_change: 13380294961448,
        timestamp: 1612498449.0
    }, 
    {
        block_id: 1995479, 
        hash: "9dff60a8414b8e21e75d190dce755631ed993917bc68cf4c0ad52d981e9519d5", 
        time: "2021-02-05 12:14:09", 
        balance_change: -13380294961448,
        timestamp: 1612498449.0
    }
]        

'''


class BlockchairApi():


    def __init__(self):
        pass

    def getHistoricalTransactions(self, wallet_address, wallet_type, transaction_count_limit = 100, transaction_time_limit = None):
        '''
        

        returns an array of transactions according to the parameters
        '''
        wallet_map = {
            'ethereum': 'ethereum',
            'bitcoin': 'bitcoin',
            'dogecoin': 'dogecoin',
            'litecoin': 'litecoin',
            'dashcoin': 'dash',
            'bitcoin_cash':'bitcoin-cash'
        }
        symbol = wallet_map[wallet_type]
        url = f'https://api.blockchair.com/{ symbol }/dashboards/address/{ wallet_address }'
        if symbol != 'ethereum':
            url +='?transaction_details=true'
        r = requests.get(url)
        response = r.json()

        transactions = response['data'][wallet_address]['transactions']
        for transaction in transactions:
            time_string = transaction['time']
            transaction['timestamp'] = datetime.fromisoformat(time_string).timestamp()
        return transactions

    def checkIfWalletExists(self, wallet_address, wallet_type):
        '''
        checks if the wallet exists in the blockchain, returns true or false
        '''
        pass
class FakeBlockchairApi():
    def __init__(self, cch):
        self.iter_num = 0
        self.cch = cch
        self.test_transactions = []
    def getHistoricalTransactions(self, wallet_address, wallet_type, transaction_count_limit = 100, transaction_time_limit = None):
        '''
        

        returns an array of transactions according to the parameters
        '''

        active_transactions = self.cch.active_transactions.search(where('wallet_adr') == wallet_address)
        transactions = []
        # first iteration, all of them are unappropriate
        if self.iter_num == 0:
            # generates random transactions where some of them fit the amount for currently active transactions#
            # but were created before the active transaction was created
            for transaction in active_transactions:
                obj = {
                    'block_id': 1995470+transaction['pk'],
                    'hash': f"eee2225117251ab3bd61d92e49e9ad380e87feb35e5f006ac978cd130b7b7{transaction['pk']}",
                    'time': "2021-02-05 11:51:28",
                    'balance_change': transaction['protocol_units'],
                    'timestamp': transaction['created_time'] - random.randint(100,1000),
                    'original_transaction_pk' : -transaction['pk'],
                    'wallet_address': wallet_address
                }
                transactions.append(obj)
                self.test_transactions.append(obj)
        # second iteration, all of them looks like real
        # in addition one is 'accidentally sent' transaction
        elif self.iter_num == 1:
            #appends the previous transactions
            for transaction in self.test_transactions: 
                if transaction['wallet_address'] == wallet_address: 
                    transactions.append(transaction) 
            # generates transactions which will make all the active transactions as finished!
            for transaction in active_transactions:
                obj = {
                    'block_id': 1995470+transaction['pk']+100,
                    'hash': f"eee2225117251ab3bd61d92e49e9ad380e87feb35e5f006ac978cd130b7b7{transaction['pk']+100}",
                    'time': "2021-02-05 11:51:28",
                    'balance_change': transaction['protocol_units'],
                    'timestamp': transaction['created_time'] + 1,
                    'original_transaction_pk' : transaction['pk'], 
                    'wallet_address': wallet_address
                }
                transactions.append(obj)
                self.test_transactions.append(obj)
            # and 1 accidental transaction in case if somebody is going to send money to the wallet
            obj = obj.copy()
            obj['timestamp'] += 2
            obj['block_id'] += 1
            obj['hash'] += 'fake_one'
            obj['original_transaction_pk'] += 1
            transactions.append(obj)
            self.test_transactions.append(obj)
        # return all the previous transactions as nothing happened before
        else:
            for transaction in self.test_transactions: 
                if transaction['wallet_address'] == wallet_address: 
                    transactions.append(transaction) 
        self.iter_num += 1
        return transactions
    def checkIfWalletExists(self, wallet_address, wallet_type):
        '''
        checks if the wallet exists in the blockchain, returns true or false
        '''
        return True