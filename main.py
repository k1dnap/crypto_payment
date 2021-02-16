# https://flask.palletsprojects.com/en/1.1.x/api/#flask.Request
from flask import Flask, request, jsonify, abort, render_template

from cryptoChecker import CryptoChecker

cch = CryptoChecker()



app = Flask(__name__, static_url_path='/static')

# wallets
@app.route('/wallets/get')
def getWallets():
    wallets = cch.wallets.filter()
    return jsonify(wallets)

@app.route('/wallets/delete')
def deleteWallet():
    wallet_adr = request.args.get("wallet_adr")
    if wallet_adr:
        wallets = deleteWallet(wallet_adr)
    return jsonify(wallets)

@app.route('/wallets/create')
def createWallets():
    wallet_adr = request.args.get("wallet_adr")
    wallet_type = request.args.get("wallet_type")
    if wallet_adr and wallet_type:
        wallets = addWallet(wallet_adr, wallet_type)
    return jsonify(wallets)

# transactions

if __name__ == '__main__':
    port = 8001
    print(f'cryptochecker is running at port {port}')
    app.run(port=port,debug=True)