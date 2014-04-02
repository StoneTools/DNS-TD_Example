#!/usr/bin/env python

import sys
from dynect.DynectDNS import DynectRest
import ConfigParser

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

#this is an inefficient lookup, much faster to use labels or other details
#for demonstration purposes
def get_dsf_byfqdn( dyn_iface, fqdn ):
    response = dyn_iface.execute('/DSF/','GET')
    for uri in response['data']:
        dsf = dyn_iface.execute( uri, 'GET')
        for node_dict in dsf['data']['nodes']:
            if node_dict['fqdn'] == fqdn:
                return uri
    return 0

#read API credentials from file
try:
    creds = get_creds()
except:
    sys.exit('Unable to open configuation file: config.cfg')

dyn_iface = DynectRest()
# Log in
response = dyn_iface.execute('/Session/', 'POST', creds)
if response['status'] != 'success':
    sys.exit("Unable to Login to DynECT DNS API.  Please check credentials in config.cfg")

#obtain parent uri for DSF service by FQDN
#also possible to get DSF directly by label
dsf_uri = get_dsf_byfqdn( dyn_iface, 'example.dsfexample.com' ) 
#get full description of service using URI
dsf_desc = dyn_iface.execute(dsf_uri, 'GET')

#grab IDs from service description
#can be used later to direclty access service or other URIs
dsf_id = dsf_desc['data']['service_id']

#at this point we could look at rulesets->response pools->records by parsing the DSF object
#instead we will use paramaters to enumerate specific records for demonstration purposes
#this example would find all A records with rdata 123.45.67.89 and update them to 98.76.54.32
argum = { 'master_line' : '123.45.67.89' }
rec_uris = dyn_iface.execute('/DSFRecord/' + dsf_id, 'GET', argum)

argum = { 'rdata' : { 'a_rdata' : { 'address' : '98.76.54.32' } } }
for rec_uri in rec_uris['data']:
    update = dyn_iface.execute(rec_uri, 'PUT', argum)

#publish changes
argum = { 'publish' : 'Y' }
publish = dyn_iface.execute( '/DSF/' + dsf_id, 'PUT', argum)

# Log out, to be polite
dyn_iface.execute('/Session/', 'DELETE')
