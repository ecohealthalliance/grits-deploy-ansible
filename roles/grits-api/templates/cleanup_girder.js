//This script removes girder fields we no longer use.
db.item.update({}, {
        '$unset' : {
            //We use processingQueuedOn instead of these status fields now
            'meta.processing':'',
            'meta.diagnosing':'',
            //This field should be private.scrapedData
            'private.scraped_data': ''
        }
    }, {
        'multi': true
    }
);
