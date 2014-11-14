#!/usr/bin/env python

import sys
import os
import dateutil.parser
import dateutil.tz
import datetime

import pymongo

import requests

import girder
from girder.utility import server, model_importer


TimeZoneStr = '''-12 Y
-11 X NUT SST
-10 W CKT HAST HST TAHT TKT
-9 V AKST GAMT GIT HADT HNY
-8 U AKDT CIST HAY HNP PST PT
-7 T HAP HNR MST PDT
-6 S CST EAST GALT HAR HNC MDT
-5 R CDT COT EASST ECT EST ET HAC HNE PET
-4 Q AST BOT CLT COST EDT FKT GYT HAE HNA PYT
-3 P ADT ART BRT CLST FKST GFT HAA PMST PYST SRT UYT WGT
-2 O BRST FNT PMDT UYST WGST
-1 N AZOT CVT EGT
0 Z EGST GMT UTC WET WT
1 A CET DFT WAT WEDT WEST
2 B CAT CEDT CEST EET SAST WAST
3 C EAT EEDT EEST IDT MSK
4 D AMT AZT GET GST KUYT MSD MUT RET SAMT SCT
5 E AMST AQTT AZST HMT MAWT MVT PKT TFT TJT TMT UZT YEKT
6 F ALMT BIOT BTT IOT KGT NOVT OMST YEKST
7 G CXT DAVT HOVT ICT KRAT NOVST OMSST THA WIB
8 H ACT AWST BDT BNT CAST HKT IRKT KRAST MYT PHT SGT ULAT WITA WST
9 I AWDT IRKST JST KST PWT TLT WDT WIT YAKT
10 K AEST ChST PGT VLAT YAKST YAPT
11 L AEDT LHDT MAGT NCT PONT SBT VLAST VUT
12 M ANAST ANAT FJT GILT MAGST MHT NZST PETST PETT TVT WFT
13 FJST NZDT
11.5 NFT
10.5 ACDT LHST
9.5 ACST
6.5 CCT MMT
5.75 NPT
5.5 SLT
4.5 AFT IRDT
3.5 IRST
-2.5 HAT NDT
-3.5 HNT NST NT
-4.5 HLV VET
-9.5 MART MIT'''
TimeZoneDict = {}

def getTimeZoneDict():
    """
    Timezones are often stored as abreviations such as EST.  These are
    ambiguous, but should still be handled.  See
    http://stackoverflow.com/questions/1703546
    :returns: a dictionary that can be passed to dateutil.parser.parse.
    """
    if not len(TimeZoneDict):
        for tz_descr in map(str.split, TimeZoneStr.split('\n')):
            tz_offset = int(float(tz_descr[0]) * 3600)
            for tz_code in tz_descr[1:]:
                TimeZoneDict[tz_code] = tz_offset
    return TimeZoneDict


def loadConfig():
    # return server config and healthmap authentication
    apikey = os.environ.get('HEALTHMAP_APIKEY')
    if apikey is None:
        raise Exception("HEALTHMAP_APIKEY is not set.")
    config = {
        'girderUsername': 'grits',
        'girderCollectionName': 'healthmap',
        'healthMapRoot': 'http://healthmap.org/HMapi.php',
        'healthMapDayFMT': '%Y-%m-%d',
        'allAlertsFolder': 'allAlerts',
    }
    config['healthMapApiKey'] = apikey
    return config


def loadHMap(config, day):
    # load healthMap alerts from the web api
    oneDay = datetime.timedelta(1)
    params = {
        'auth': config['healthMapApiKey'],
        'striphtml': '1',
        'sdate': day.strftime(config['healthMapDayFMT']),
        'edate': (day + oneDay).strftime(config['healthMapDayFMT'])
    }

    response = requests.get(config['healthMapRoot'], params=params)
    if not response.ok:
        raise Exception('Error requesting health map data.')

    # flatten the records
    records = response.json()
    allAlerts = []
    if not records:
        return allAlerts
    for record in records:
        n = 0
        alerts = record.pop('alerts')
        for alert in alerts:
            alert.update(record)
            id = '%s%04i' % (idFromURL(alert['link']), n)
            alert['id'] = id
            allAlerts.append(alert)
            # always use zero-index now.  The trailing zeros are unnecessary
            # but keep more data with the previous loading method
            # n = n + 1
    return allAlerts


def idFromURL(url):
    # parse the healthmap id from the link url
    l = url.split('?')
    id = l[1].split('&')[0]
    return int(id)


def filterAlert(alert):
    # do any per alert data filtering here
    try:
        alert['rating'] = int(float(alert['rating']['rating']))
    except Exception:
        alert['rating'] = -1
    alert['date'] = dateutil.parser.parse(alert['formatted_date'],
                                          tzinfos=getTimeZoneDict())
    alert['updated'] = datetime.datetime.now()
    try:
        alert['lat'] = float(alert['lat'])
        alert['lng'] = float(alert['lng'])
    except ValueError:
        alert['lat'] = None
        alert['lng'] = None

    return alert


def girderSearch(m, query):
    return list(m.find(query))


def setupGirder():
    server.setup()
    model = model_importer.ModelImporter()
    models = {
        'collection': model.model('collection'),
        'folder': model.model('folder'),
        'item': model.model('item'),
        'user': model.model('user')
    }
    return models


def main(*args):
    # open config file
    config = loadConfig()

    # initialize girder models
    model = setupGirder()

    # get user id
    response = girderSearch(model['user'], {'login': config['girderUsername']})
    if len(response) == 0:
        raise Exception("User '%s' does not exist" % config['girderUsername'])
    user = response[0]

    # get collection ID
    response = girderSearch(
        model['collection'],
        {'name': config['girderCollectionName']}
    )
    if len(response) > 0:
        collection = response[0]
    else:
        raise Exception("Could not find healthmap collection.")

    # get the folder containing all of the alerts
    response = girderSearch(model['folder'], {'name': config['allAlertsFolder'],
                                              'parentCollection': 'collection',
                                              'parentId': collection['_id']})
    if len(response) > 0:
        folder = response[0]
    else:
        raise Exception("Could not find healthmap folder.")

    # get the date range to download, defaults to the last 1 day
    if len(args) >= 1:
        # arg 1 start day
        start = dateutil.parser.parse(args[0])
    else:
        start = datetime.datetime.now() - datetime.timedelta(1)
    if len(args) >= 2:
        end = dateutil.parser.parse(args[1])
    else:
        end = start + datetime.timedelta(1)

    nAdded = 0
    nUpdated = 0
    nIdentical = 0
    nDeleted = 0

    # loop through all days in the range
    while start < end:
        print 'Downloading data from %s...' % start.strftime('%Y-%m-%d')
        alerts = loadHMap(config, start)
        print 'Received %i alerts, adding to girder...' % len(alerts)

        # loop through all alerts in the response
        for alert in alerts:
            if not 'place_id' in alert:
                continue
            # process the data
            alert = filterAlert(alert)
            meta = {
                'date': alert.get('date'),
                'feed': alert.get('feed'),
                'link': alert.get('original_url', alert.get('link')),
                'description': alert.get('descr', '')
            }
            place = {
                'latitude': alert.get('lat'),
                'longitude': alert.get('lng'),
                'country': alert.get('country'),
                'disease': alert.get('disease'),
                'rating': alert.get('rating'),
                'species': alert.get('species_name'),
                'diseases': alert.get('diseases'),
                'place_id': alert['place_id']
            }
            desc = alert.get('summary', alert.get('summary_en', ''))
            if desc is None or desc.strip() == '':
                if alert.get('summary_en', ''):
                    desc = alert.get('summary_en', '')
            if desc is None or desc.strip() == '':
                for key in alert:
                    if key.startswith('summary_') and alert[key] and alert[key].strip():
                        desc = alert[key]
                        break
            if desc is None or desc.strip() == '':
                desc = alert['id']
            desc = desc.strip()

            # check if the item already exists
            items = girderSearch(model['item'], {
                'name': str(alert['id']),
                'folderId': folder['_id']
            })
            difference = False

            # delete old items that used a non-zero index.  If the item didn't
            # already exist, rename the first of these to
            # an old ite
            oldItems = girderSearch(model['item'], {
                'name': {'$regex': '^%s(?!0000$)....$' % (
                         str(alert['id'])[:-4], )},
                'folderId': folder['_id']
            })
            if len(oldItems) and not len(items):
                items = [oldItems[0]]
                items[0]['name'] = alert['id']
                items[0]['lowerName'] = items[0]['name'].lower()
                oldItems = oldItems[1:]
                difference = True
            for item in oldItems:
                model['item'].remove(item)
                nDeleted += 1

            if len(items) > 1:
                print >> sys.stderr, \
                    'WARNING: multiple items with the same name exist'

                # delete the items with this name, which should be unique
                for item in items[1:]:
                    model['item'].remove(item)

            if len(items) > 0:
                # update item
                item = items[0]
                if not 'meta' in item:
                    item['meta'] = {}
                if 'date' in item['meta']:
                    item['meta']['date'] = item['meta']['date'].replace(
                        tzinfo=dateutil.tz.tzutc())
                if item['description'] != desc:
                    difference = True
                for key in meta:
                    if item['meta'].get(key, None) != meta[key]:
                        difference = True
                places = {placeIter['place_id']: placeIter for placeIter in
                          item['meta'].get('places', [])}
                if alert['place_id'] not in places:
                    difference = True
                if (not difference and places[alert['place_id']] != place):
                    difference = True
                if alert['place_id'] == item['meta'].get('place_id', None):
                    for key in place:
                        if item['meta'].get(key, None) != place[key]:
                            difference = True
                if not difference:
                    nIdentical += 1
                    continue
                item['description'] = desc
                nUpdated += 1
            else:
                # create the item
                item = model['item'].createItem(
                    str(alert['id']),
                    user,
                    folder,
                    description=desc
                )
                nAdded += 1
                places = {}
            item['meta'] = item.get('meta', {})
            places[alert['place_id']] = place
            item['meta']['places'] = places.values()
            minPlaceId = str(min([int(placeId) for placeId in places]))
            if minPlaceId == alert['place_id']:
                item['meta']['place_id'] = alert['place_id']
                meta.update(place)
            # add/update metadata
            item['meta'].update(meta)
            model['item'].save(item, validate=False)

        start = start + datetime.timedelta(1)
    print 'Added %i new items' % nAdded
    print 'Updated %i old items' % nUpdated
    print '%i identical old items' % nIdentical
    if nDeleted:
        print 'Deleted %i items' % nDeleted

if __name__ == '__main__':
    import sys
    now = datetime.datetime.now()
    fmt = '%Y-%m-%d'
    if len(sys.argv) < 2 or sys.argv[1] == '--day':
        yesterday = now - datetime.timedelta(1)
        args = [yesterday, now]
        args = [a.strftime(fmt) for a in args]
    elif sys.argv[1] == '--twoday':
        yesterday = now - datetime.timedelta(2)
        args = [yesterday, now]
        args = [a.strftime(fmt) for a in args]
    elif sys.argv[1] == '--full':
        start = datetime.datetime(now.year - 2, now.month, now.day)
        args = [start, now]
        args = [a.strftime(fmt) for a in args]
    elif sys.argv[1] == '--month':
        start = now - datetime.timedelta(days=31)
        args = [start, now]
        args = [a.strftime(fmt) for a in args]
    else:
        args = sys.argv[1:]
    main(*args)
