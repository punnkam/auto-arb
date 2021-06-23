import logging
import glob
import os

def setup(pref = 'default'):
    pref += '.txt'
    names = [x[14:] for x in glob.glob('config/config*')]
    if pref not in names:
        print('\nFile cannot be found\n')
        return
    else:
        print('Setting config to', pref)
        pref = 'config/config_' + pref

    try:
        f = open(pref, 'r')
        mydict = {}
        mydict['exchange'] = f.readline()[:-1]
        mydict['apikey'] = f.readline()[:-1]
        mydict['apisecret'] = f.readline()[:-1]
        mydict['size'] = f.readline()[:-1]
        mydict['maintoken'] = f.readline()[:-1]
        mydict['fundinghigh'] = f.readline()[:-1]
        mydict['fundinglow'] = f.readline()[:-1]
        mydict['maxleverage'] = f.readline()[:-1]
        f.close()
    except:
        print('Error: File could not be opened')
    return mydict

def print_conf_list():
    for name in glob.glob('config/config*'):
        print(name[14:len(name)-4])


