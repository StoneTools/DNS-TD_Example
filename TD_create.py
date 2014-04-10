#!/usr/bin/env python

import sys
from dynect.DynectDNS import DynectRest
import ConfigParser
import json

#function to read API credentials from file
def get_creds() :
    try:
        #initialize config parser
        config = ConfigParser.ConfigParser()
        config.read('config.cfg')
        #stash in dict
        creds = {
            'customer_name' : config.get('login','cn'),
            'user_name' : config.get('login','un'),
            'password' : config.get('login','pw'),
        }
        return creds    
    except:
        #raise exception is config read fails
        raise

#read API credentials from file
try:
    creds = get_creds()
except:
    sys.exit('Unable to open configuation file: config.cfg')


#create Dyn Traffic Managment interface
dyn_iface = DynectRest()

# Log in
response = dyn_iface.execute('/Session/', 'POST', creds)
if response['status'] != 'success':
    sys.exit("Unable to Login to DynECT DNS API.  Please check credentials in config.cfg")

#some variable about location of TD (example2.dsfexample.com)
zone = 'dsfexample.com'
node = 'example2'

#create new DSF
argum = { 
    #name of the service
    'label' : 'exampleTD',
    #location of the FQDN
    'nodes' : [ { 
        'zone' : zone,
        'fqdn' : node + '.' + zone
        } , ],
    }

response = dyn_iface.execute('/DSF/','POST', argum)

#At this point the service exists in a very basic state but has not been published
#Additional information could of been configured in the initial call to flesh it out more
#We  capture the service ID to do further work against it
dsf_id = response['data']['service_id']

#create a ruleset
argum = {
    #user defined name for label
    'label' : 'CatchAll',
    #setting criteria type to always will match all requests
    'criteria_type' : 'always',
    #ordering handles in what order rulesets are used to decide
    #lower number indexs will be used first
    'ordering' : '100',
    'response_pools' : [{ 'failover' : '10.10.10.10', }],
    }

response = dyn_iface.execute('/DSFRuleset/' + dsf_id, 'POST', argum )
#capture the ruleset ID
dsf_ruleid1 = response['data']['dsf_ruleset_id']

#create a second ruleset
argum = {
    #user defined name for label
    'label' : 'Dispersed',
    #setting criteria type to use geop rules
    'criteria_type' : 'geoip',
    'criteria' : {
        'geoip' : {
            #regions are two digit codes covering large areas
            'region' : [ 12 ],
            #countries are two uppercase letter codes
            'country' : [ 'FR' , 'DE' ],
            #provinces are two lower case letter codes
            'province' : [ 'nh', 'ns' ],
            #please see docs for more information on codes
            }
        },
    'ordering' : '1',
    }

response = dyn_iface.execute('/DSFRuleset/' + dsf_id, 'POST', argum )
dsf_ruleid2 = response['data']['dsf_ruleset_id']

#create a response pool
argum = {
    #user defined name for label
    'label' : 'DataCenter1',
    #automation relates to how pool behaves based on monitoring state
    'automation' : 'auto', 
    #join the pool to a ruleset
    'dsf_ruleset_id' : dsf_ruleid2,
    }
response = dyn_iface.execute('/DSFResponsePool/' + dsf_id, 'POST', argum)
dsf_poolid1 = response['data']['dsf_response_pool_id']


#create a second response pool
argum = {
    #user defined name for label
    'label' : 'DataCenter2',
    'automation' : 'auto', 
    'dsf_ruleset_id' : dsf_ruleid2,
    }

response = dyn_iface.execute('/DSFResponsePool/' + dsf_id, 'POST', argum)
dsf_poolid2 = response['data']['dsf_response_pool_id']

#add monitoring details
argum ={
    'label' : 'monitor1',
    'protocol' : 'HTTP',
    'probe_interval' : '60',
    'retries' : '2',
    'response_count' : '2',
    'active' : 'Y',
    'options' : {
        'port' : '80',
        'host' : 'host.dsfexample.com',
        'expected' : 'dsf',
        }
    }

response = dyn_iface.execute( '/DSFMonitor/', 'POST', argum )
#capture the monitor ID
dsf_monid = response['data']['dsf_monitor_id']

#add an A reccord record pool to the second response pool
argum = {
    #response pool we want it added to
    'dsf_response_pool_id' : dsf_poolid2,
    #user defined label
    'label' : 'PoolA',
    #class of the records being added
    'rdata_class' : 'A',
    'ttl' : '30',
    #automation determins how records react on monitoring results
    'automation' : 'auto',
    #serve count serves multipe records per request
    'serve_count' : '2',
    'dsf_monitor_id' : dsf_monid,
    'records' : [
        {
            #user deifne label
            'label' : 'A1',
            'automation' : 'auto',
            #master line encapsulates rdata for simple records
            'master_line' : '10.1.1.1',
            },
        {
            'label' : 'A2',
            'automation' : 'auto',
            'master_line' : '10.2.2.2',
            },
        {
            'label' : 'A3',
            'automation' : 'auto',
            'master_line' : '10.3.3.3',
            },
        ]
    }

response = dyn_iface.execute( '/DSFRecordSet/' + dsf_id, 'POST', argum )

#add an AAAA reccord record pool to the second response pool
argum = { 
    'dsf_response_pool_id' : dsf_poolid2,
    'label' : 'PoolAAAA',
    'rdata_class' : 'AAAA',
    'ttl' : '30',
    'automation' : 'auto',
    'dsf_monitor_id' : dsf_monid,
    'records' : [
        {
            'label' : 'AAAA1',
            'automation' : 'auto',
            'master_line' : '10::10',
            },
        ]
    }

response = dyn_iface.execute( '/DSFRecordSet/' + dsf_id, 'POST', argum )

#add an MX reccord record pool to the second response pool
argum = { 
    'dsf_response_pool_id' : dsf_poolid2,
    'label' : 'PoolMX',
    'rdata_class' : 'MX',
    'ttl' : '3600',
    'records' : [
        {
            'label' : 'MX1',
            #more complex records can be more explicitly defined
            'rdata' : {
                'mx_rdata' : {
                    'exchange' : 'mail1.dsfexample.com',
                    'preference' : '20',
                    }
                }
            },
        {
            'label' : 'MX2',
            'rdata' : {
                'mx_rdata' : {
                    'exchange' : 'mail2.dsfexample.com',
                    'preference' : '70',
                    }
                }
            }
        ]
    }

response = dyn_iface.execute( '/DSFRecordSet/' + dsf_id, 'POST', argum )




#publish the service with all changes
#changes are not live until the service is published
#publish can be called as an option in nearly any service call
argum = { 'publish' : 'Y' }
response = dyn_iface.execute( '/DSF/' + dsf_id, 'PUT', argum )
if ( response['status'] == 'success' ):
    print "Published"
else:
    print "Publish failed"

# Log out, to be polite
dyn_iface.execute('/Session/', 'DELETE')
