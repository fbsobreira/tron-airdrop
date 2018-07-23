import sys
import re
import os
import codecs # UniCode support
from pymongo import MongoClient
from math import ceil
import requests
from time import sleep
import logging
import argparse
from datetime import datetime
from pprint import pprint
import getpass

import terminal_banner
from colorama import init
init(strip=not sys.stdout.isatty()) # strip colors if stdout is redirected
from termcolor import cprint 
from pyfiglet import figlet_format

# start loggin
logging.basicConfig(format='%(asctime)s %(message)s',level=logging.ERROR)
# MongoDB connection
client = MongoClient()
print("Connected to MongoDB successfully!")
# Database
db = client['tron-airdrop']

API_URL = os.environ.get('API_URL')
if API_URL is None:
    API_URL = 'https://api.tronscan.org'

parser = argparse.ArgumentParser()
parser.add_argument('--address',
                    dest='address', help='Adress from')
parser.add_argument('--token',
                    dest='token', help='Token to send')

parser.add_argument('--amount',
                    dest='amount', help='Amount To Token')


cprint(figlet_format('     TRON     ', font='starwars'),
       'white', 'on_red', attrs=['bold'])

cprint(figlet_format('AIRDROP', font='starwars'),
       'white', 'on_red', attrs=['bold'])

# Print iterations progress
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = '\r')
    # Print New Line on Complete
    if iteration == total: 
        print()    

if __name__ == "__main__":
    args = parser.parse_args()
    if (args.address is None or args.token is None):
        logging.error('Please try: python run.py --address=ADDRESS --token=TOKENNAME')
        logging.error('App closed...')
        sys.exit(0)
    if (args.amount is None):
        args.amount=1
    else:
        args.amount = int(args.amount)

    # get list of witness
    resultWitnesses = requests.get(API_URL+"/api/witness").json()

    # ToSend DB
    #db['tosend'].remove()
    tosend = db['tosend']
    # Get voters and send
    for W in resultWitnesses:
        start = 0
        limit = 100
        print('Get voters from: '+W['address'])
        voters = requests.get(API_URL+"/api/vote", params={'limit': 0, 'candidate': W['address']}).json()
        
        totalVotes = voters['total'] 
        pages = ceil(totalVotes/limit)

        for pos in range(0, pages):
            voters = requests.get(API_URL+"/api/vote", params={'limit': limit, 'start': pos*limit, 'candidate': W['address']}).json()
            for item in voters["data"]: 
                tosend.insert_one(item)
       
        sleep(1)            
    
    # get account info
    resultBalance = requests.get(API_URL+"/api/account/"+args.address).json()
   
    bw = resultBalance['bandwidth']['freeNetRemaining']+resultBalance['bandwidth']['netRemaining']
    for b in resultBalance['balances']:
        if b['name']==args.token:
            balance = b['balance']
            break
    if balance==0:
        logging.error('No balance found!')
        logging.error('App closed...')
        sys.exit(0)

    
    # total sending
    sendto = tosend.find().distinct("voterAddress")
    totalSending = len(sendto)*args.amount

    info_text = "Your have {:,.0f} {},\nand is sending {:,.0f} {}.\nYour BW is {:,.0f},\nAnd it is estimated {:,.0f}BW".format(
        balance,args.token,totalSending,args.token,bw,len(sendto)*200)
    print(terminal_banner.Banner(info_text))
    if totalSending>balance:
        print('Only the first {} will receive.'.format(ceil(balance/args.amount)))
    
    wd = input("Do you confirm this operation? (Y/n)")
    if wd!= "y":
        logging.error('User did not confirm!')
        logging.error('App closed...')
        sys.exit(0)
    PK=getpass.getpass(prompt='Please enter your private key:')
    # get 
    
    sentto = db['sentto']
    l = len(sendto)
    if totalSending>balance:
        l = ceil(balance/args.amount)
    printProgressBar(0, l, prefix = 'Sending...:', suffix = 'Complete', length = 50)
    i=1
    cerror=0
    for s in sendto:
        data = {"broadcast": True, "key": PK, "contract": {"amount": args.amount, 
            "ownerAddress": args.address, "toAddress": s, "assetName": args.token}
        }
        try:
            result = requests.post(API_URL+"/api/transaction-builder/contract/transferasset", json=data).json()
            if (result["result"]["code"]=="SUCCESS"):
                record = {
                    "from": args.address,
                    "to": s,
                    "amount": args.amount,
                    "token": args.token,
                    "hash": result["transaction"]["hash"],
                    "update": datetime.utcnow()
                }
                sentto.insert(record)
                sendto.remove(s)
        except ValueError:
            cerror += 1
            logging.error("Oops!  Error sending.  Try again...")
        printProgressBar(i, l, prefix = 'Sending...:', suffix = 'Complete', length = 50)
        i = i +1
        if i>l:
            break
    
    print("All done!")
    if cerror>0:
        print("System fail to send {} transactions, try again.".format(cerror))

   
logging.info('App closed...')
