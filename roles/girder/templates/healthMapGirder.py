#!/usr/bin/env python

import datetime
import dateutil.parser
import dateutil.tz
import os
import pymongo
import requests
import socket
import sys

import girder
from girder.utility import server, model_importer

PlacesListName = 'events'

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
        raise Exception('HEALTHMAP_APIKEY is not set.')
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
    """
    Load healthMap alerts from the web api.  The HealthMap API returns a json
    list of records.  Each record contains place information, including a
    place_id value, and a list of alerts.  Some alerts are in multiple place
    records.  Although these alerts have the same link ID, they can have
    different diseases and specie information.
      We move the place information from the record set into each alert, and
    combine all alerts into a single list.  We also compute a name for the
    alert, which is the HealthMap link ID followed by '0000'.

    :param config: a dictionary with API access information
    :param day: the day to retreive.  Only one day is retrieved at a time.
    :returns: a single list of all retrieved alerts.
    """
    oneDay = datetime.timedelta(1)
    params = {
        'auth': config['healthMapApiKey'],
        'striphtml': '1',
        'sdate': day.strftime(config['healthMapDayFMT']),
        'edate': (day + oneDay).strftime(config['healthMapDayFMT'])
    }

    try:
        response = requests.get(config['healthMapRoot'], params=params,
                                timeout=120)
    except (requests.Timeout, socket.timeout):
        print 'Error requesting health map data: timed out'
        sys.exit(0)
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


def girderSearch(m, query, **kwargs):
    return list(m.find(query, **kwargs))


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


def loadAlerts(config, model, user, folder, start, end):
    """
    Load all alerts for a given date range.  After loading the alerts, check if
    we can detect that any alert information has gone away and remove it.

    :param config: information on HealthMap API access.
    :param model: a dictionary of girder model references.
    :param user: the girder user that owns the alert records.
    :param folder: the girder folder where alerts are stored.
    :param start: the starting date (inclusive) for the alert query.
    :param end: the ending date (exclusive) for the alert query.
    """

    nAdded = 0
    nUpdated = 0
    nIdentical = 0
    nDeleted = 0

    processedIds = {}
    oldStart = start
    oldIdPlaces = {}

    # loop through all days in the range
    while start < end:
        print 'Downloading data from %s...' % start.strftime('%Y-%m-%d')
        alerts = loadHMap(config, start)
        print 'Received %i alerts, adding to girder...' % len(alerts)

        # loop through all alerts in the response
        for alert in alerts:
            action, alertDeleted = loadOneAlert(
                model, user, folder, start, processedIds, oldIdPlaces, alert)
            nDeleted += alertDeleted
            if action == 'added':
                nAdded += 1
            elif action == 'updated':
                nUpdated += 1
            elif action == 'identical':
                nIdentical += 1

        start = start + datetime.timedelta(1)
        if not len(alerts):
            oldStart = start

    nUpdated += removeMissingAlerts(model, processedIds, oldIdPlaces, oldStart,
                                    folder)

    print 'Added %i new items' % nAdded
    print 'Updated %i old items' % nUpdated
    print '%i identical old items' % nIdentical
    if nDeleted:
        print 'Deleted %i items' % nDeleted


def loadOneAlert(model, user, folder, currentDate, processedIds, oldIdPlaces,
                 alert):
    """
    Process a single alert record from the HealthMap query, adding it to the
    girder database.  If the alert already exists in the database, it is
    updated.
      The HealthMAP API can return the same alert (based on link ID) multiple
    times.  When this happens, the records always differ in place_id, and may
    differ in other parameters, such as disease(s) and specie.  We store a
    single record in girder for any HealthMap link ID.  When there are multiple
    instances of that alert, we store the information in a list within the
    metadata (named based on PlacesListName).
      In order to maintain compatibility with code that was written before
    this, one HealthMap record is also stored in the main meta array.
    Arbitrarily, whichever record has the lowest place_id is selected for this
    (by picking a specific record for the main meta array, the database is
    stable regardless of the order it is loaded).

    :param model: a dictionary of girder model references.
    :param user: the girder user that owns the alert records.
    :param folder: the girder folder where alerts are stored.
    :param currentDate: the day for the HealthMap query.  Used in tracking when
                        alerts have been removed.
    :param processedIds: a dictionary which is updated with alerts we process.
                         The keys are the names of the alerts, and the values
                         are dictionaries of place_ids that we processed for
                         that alert.
    :param oldIdPlaces: a dictionary which is updated with alerts we examined
                        in the girder database.  The keys are the names of the
                        alerts, and the values are dictionaries of place_ids
                        that were in the database.
    :param alert: the alert record.  This is the record from the HealthMap API
                  with the place information combined into the dictionary.
    :returns: action: one of 'added', 'updated', 'identical' or None indicating
                      if this alert is new, was already in the database and had
                      to be changed, had no new information, or failed basic
                      validation.
    :returns: nDeleted: if the alert was in the database multiple times (due to
                        legacy data loading methods), this is the number of
                        records that were deleted.
    """
    nDeleted = 0
    action = None
    # process the data
    alert = filterAlert(alert)
    if not 'place_id' in alert:
        print('WARNING: alert without a place_id.  This alert will be '
              'skipped.  Alert ID: %s' % alert.get('id', ''))
        return action, nDeleted
    if alert['id'] not in processedIds:
        processedIds[alert['id']] = {'firstDay': currentDate}
    if alert['place_id'] in processedIds:
        print('WARNING: duplicate place_id %s in alert %s.' % (
              alert['place_id'], alert['id']))
    processedIds[alert['id']][alert['place_id']] = alert.get('country')
    processedIds[alert['id']]['lastDay'] = currentDate

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
        'diseases': alert.get('diseases', [alert.get('disease')]),
        'place_name': alert.get('placename'),
        'place_id': alert['place_id']
    }
    # Only add these keys if they are present and not false-like
    for key in ('geonameid', ):
        if alert.get(key):
            place[key] = alert[key]
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
        'name': {'$regex': '^%s(?!0000$)....$' % (str(alert['id'])[:-4], )},
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
        print >> sys.stderr, 'WARNING: multiple items with the same name exist'

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
        places = getPlacesDict(item)
        # Verify that places are not duplicated or missing
        if len(places) != len(item['meta'].get(PlacesListName, [])):
            difference = True
        if not alert['id'] in oldIdPlaces:
            oldIdPlaces[alert['id']] = {}
        for oldPlace in item['meta'].get(PlacesListName, []):
            if 'place_id' in oldPlace:
                oldIdPlaces[alert['id']][oldPlace['place_id']] = \
                    oldPlace['country']
        if alert['place_id'] not in places:
            difference = True
        if (not difference and places[alert['place_id']] != place):
            difference = True
        if alert['place_id'] == item['meta'].get('place_id', None):
            for key in place:
                if item['meta'].get(key, None) != place[key]:
                    difference = True
        if not difference:
            return 'identical', nDeleted
        item['description'] = desc
        action = 'updated'
    else:
        # create the item
        item = model['item'].createItem(
            str(alert['id']),
            user,
            folder,
            description=desc
        )
        action = 'added'
    itemUpdateAndSave(model, item, meta, place)
    return action, nDeleted


def itemUpdateAndSave(model, item, meta=None, addPlace=None, delPlaces=None):
    """
    Update an item with new metadata, an additional place, or by deleting a
    place.

    :param model: a dictionary of girder model references.
    :param item: the item to modify and save.
    :param meta: optional dictionary of metadata to update.
    :param addPlace: optional place dictionary to add to the places list.
    :param delPlaces: optional list of place_id to remove from the places list.
    """
    item['meta'] = item.get('meta', {})
    if meta:
        # add/update metadata
        item['meta'].update(meta)
    # Put the current places in a dictionary so we can add or remove from it
    places = getPlacesDict(item)
    if addPlace:
        places[addPlace['place_id']] = addPlace
    if delPlaces:
        for delPlace in delPlaces:
            if delPlace in places and len(places)>1:
                del places[delPlace]
    # Convert places back to an array
    item['meta'][PlacesListName] = places.values()
    # Store the place with the lowest id in the main metadata
    minPlaceId = str(min([int(placeId) for placeId in places]))
    item['meta']['place_id'] = minPlaceId
    item['meta'].update(places[minPlaceId])
    # Save the item
    model['item'].save(item, validate=False)


def getPlacesDict(item):
    """
    Generate a dictionary with place_id as the key and the values of those
    places as the values from the item['meta'][PlacesListName] list.  If an
    entry doesn't have a place_id key, don't include it in the dictionary.

    :param item: item to extract the places from.
    :returns places: the places dictionary.
    """
    places = {}
    for place in item['meta'].get(PlacesListName, []):
        if 'place_id' in place:
            places[place['place_id']] = place
    return places


def removeMissingAlerts(model, processedIds, oldIdPlaces, oldStart, folder):
    """
    Remove alerts that are in the database but weren't in the responses from
    HealthMap.  We had to have examined at least maximumDaysPerAlert days of
    data on or before the most recent record we saw of an alert for it to be a
    candidate for removal.  If a place was not in that data, then the place can
    be removed from our alert record, under the assumption that HealthMap
    edited the place to a different location.


    :param model: a dictionary of girder model references.
    :param processedIds: a dictionary of all alert ids we have processed, each
                         of which is a dictionary of place_ids that we have
                         received during this session from HealthMap and also a
                         'lastDay' value with the last date that we observed
                         this alert.
    :param oldIdPlaces: a dictionary of all alert ids that we examined in our
                        database, each of which is a dictionary of place_ids
                        in the database.
    :param oldStart: the start date of observed alerts.
    :param folder: parent folder for all alerts.
    :returns: nUpdated: number of items that were updated.
    """
    maximumDaysPerAlert = 3

    maxDelta = 0
    for id in processedIds:
        delta = processedIds[id]['lastDay'] - processedIds[id]['firstDay']
        delta = delta.days
        if delta > maxDelta:
            maxDelta = delta
    if maxDelta+1>maximumDaysPerAlert:
        print('WARNING: some alerts span %d days.  Increase '
              'maximumDaysPerAlert.  Not removing old places.' % (maxDelta+1))
        return
    nUpdated = 0
    for id in oldIdPlaces:
        if id not in processedIds:
            continue
        if (processedIds[id]['lastDay'] < oldStart +
                datetime.timedelta(maximumDaysPerAlert-1)):
            continue
        missingPlaces = []
        for place_id in oldIdPlaces[id]:
            if place_id not in processedIds[id]:
                missingPlaces.append(place_id)
        if not len(missingPlaces):
            continue
        items = girderSearch(model['item'], {
            'name': id,
            'folderId': folder['_id']
        })
        # We expect exactly one item in the database.
        if len(items) != 1:
            continue
        oldCountries = [oldIdPlaces[id][pid] for pid in oldIdPlaces[id]
                        if oldIdPlaces[id][pid] is not None and
                        oldIdPlaces[id][pid] not in processedIds[id].values()]
        if len(missingPlaces)>1:
            oldStr = str(sorted([int(oldPlace) for oldPlace in missingPlaces]))
        else:
            oldStr = missingPlaces[0]
        if len(oldCountries):
            oldStr += ' - '+', '.join(oldCountries)
        print "Alert %s place changed (was %s)" % (id, oldStr)
        itemUpdateAndSave(model, items[0], delPlaces=missingPlaces)
        nUpdated += 1
    return nUpdated


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
        raise Exception('Could not find healthmap collection.')

    # get the folder containing all of the alerts
    response = girderSearch(model['folder'], {'name': config['allAlertsFolder'],
                                              'parentCollection': 'collection',
                                              'parentId': collection['_id']})
    if len(response) > 0:
        folder = response[0]
    else:
        raise Exception('Could not find healthmap folder.')

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

    cleanDatabase(model, folder)

    loadAlerts(config, model, user, folder, start, end)


def cleanDatabase(model, folder):
    """
    Remove erroneous items from the database, clean up legacy values, and
    ensure minimum record patterns.

    :param model: a dictionary of girder model references.
    :param folder: parent folder for all alerts.
    """
    print 'Checking database'
    # All of our entries should have a date, feed, link, latitude, longitude,
    # and disease.  If not, remove them.
    requiredList = ('date', 'feed', 'link', 'latitude', 'longitude', 'disease')
    query = {'folderId': folder['_id'], '$or': [
        {'meta.'+key: {'$exists': 0}} for key in requiredList]}
    items = girderSearch(model['item'], query, limit=1, timeout=False)
    if len(items):
        print 'Removing items with missing fields'
        total = 0
        while len(items):
            items = girderSearch(model['item'], query, timeout=False)
            total += len(items)
            for item in items:
                model['item'].remove(item)
        print "  Removed %d items" % total
    # Ensure that all items have a diseases list
    query = {'folderId': folder['_id'], 'meta.diseases': {'$exists': 0}}
    items = girderSearch(model['item'], query, limit=1, timeout=False)
    if len(items):
        print 'Adding diseases list to old items'
        total = 0
        while len(items):
            items = girderSearch(model['item'], query, timeout=False)
            total += len(items)
            for item in items:
                # Make an array of the one disease we know about
                item['meta']['diseases'] = [item['meta']['disease']]
                model['item'].save(item)
        print "  Modified %d items" % total
    # Ensure that all items have a places list
    query = {'folderId': folder['_id'], 'meta.'+PlacesListName: {'$exists': 0}}
    items = girderSearch(model['item'], query, limit=1, timeout=False)
    if len(items):
        print 'Adding %s field to old items' % PlacesListName
        total = 0
        while len(items):
            items = girderSearch(model['item'], query, timeout=False)
            total += len(items)
            for item in items:
                # Make an array of the place information we know about
                place = {}
                for key in ('latitude', 'longitude', 'country', 'disease',
                            'rating', 'species', 'diseases', 'place_name',
                            'place_id', 'geonameid'):
                    if key in item['meta']:
                        place[key] = item['meta'][key]
                item['meta'][PlacesListName] = [place]
                model['item'].save(item)
        print "  Modified %d items" % total


if __name__ == '__main__':
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
