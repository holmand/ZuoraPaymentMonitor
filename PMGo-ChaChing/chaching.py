from __future__ import print_function
from future.standard_library import install_aliases
install_aliases()

import json
import os
import requests
import datetime

from functools import wraps
from flask import Flask, render_template, request, make_response

from collections import OrderedDict
from operator import itemgetter


app = Flask(__name__)

headers = {'content-type':'application/json', 'apiAccessKeyId': 'USERNAME','apiSecretAccessKey': 'PASSWORD'}
payrun_accounts_dic = {}
api_accounts_dic = {}


@app.route('/hello-world')
def hello_world():
    return 'Cha-Ching!'

@app.route('/')
def query():
    print("Processing...")

    url = 'https://rest.zuora.com/v1/action/query'
    effective_date = datetime.datetime.now().strftime("%Y-%m-%d")
    query = "select CreatedDate, AccountId, Source, Amount, RefundAmount from Payment where Status='Processed' and EffectiveDate='" + effective_date + "' "
    print(query)
    data = { "queryString" : query }

    # Query Zuora to get the Payments for today
    r = requests.post(url, data=json.dumps(data), headers=headers)

    # For each record returned, go get the Account
    zuoraResponse = r.json()
    records = zuoraResponse['records']
    length = len(records)

    payrunTotal = 0
    payrunCount = 0
    apiTotal = 0
    apiCount = 0
    play_sound = False

    for i in records:
        accountid = i['AccountId']
        amount = int(i['Amount'])
        refund = int(i['RefundAmount'])
        source = i['Source']
        created_date = i['CreatedDate']
        totalPayment = amount - refund

        if source == "PaymentRun":
            payrunTotal = payrunTotal + totalPayment
            payrunCount += 1
        else:
            apiTotal = apiTotal + totalPayment
            apiCount += 1


        # TODO: Don't make call if we don't have an AccountId
        if accountid in payrun_accounts_dic:
            print("Returned from PayRun cache: " + payrun_accounts_dic[accountid]['name'])
        elif accountid in api_accounts_dic:
            print("Returned from API cache: " + api_accounts_dic[accountid]['name'])
        else:
            # There is a new Customer, so let's play a sound.
            play_sound = True
            # Call Zuora to get Customer
            account = getcustomer(accountid)
            # Cache the account info
            account_basic = {
                "id" : accountid,
                "customer_id" : account['basicInfo']['CustomerId__c'],
                "name" : account['basicInfo']['name'],
                "amount" : totalPayment,
                "refund" : refund,
                "source" : source,
                "created_date" : created_date
                }
            if source == "PaymentRun":
                payrun_accounts_dic[accountid] = account_basic
            else:
                api_accounts_dic[accountid] = account_basic

    grandTotal = apiTotal + payrunTotal
    return render_template('index.html', play_sound=play_sound, totalCount=length, payrunCount=payrunCount, apiCount=apiCount, grandTotal=grandTotal, payrunTotal=payrunTotal, apiTotal=apiTotal, payrun_accounts_dic=payrun_accounts_dic, api_accounts_dic=api_accounts_dic)

def getcustomer(accountid):
    # TODO: Don't make call if we don't have an AccountId
    print("Calling Zuora for info on: " + accountid)
    url = 'https://rest.zuora.com/v1/accounts/' + accountid

    # Query Zuora to get the AccountId
    accountResponse = requests.get(url, headers=headers)

    # TODO: Should do some checking to make sure we got something
    account = accountResponse.json()

    return account


if __name__ == '__main__':
    app.run(debug = True)
