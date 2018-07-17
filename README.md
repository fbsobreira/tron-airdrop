# AIRDROP for TRON System

This script check the list of all representatives, and collect info of their voters. Then air drop an amount of a token to the voter address.

## System requirements
* python
* mongodb


### Create and Active a python Virtualenv 
```bash
virtualenv -p python3 env-airdrop
source env-airdrop/bin/activate
```

#### install requirements
```bash
pip install -r requirements.txt
```

# Example transfer 
```bash
python run.py --address=TUEZSdKsoDHQMeZwihtdoBiN46zxhGWYdH --token=Perogies --amount=1
```

#### CryptoChain