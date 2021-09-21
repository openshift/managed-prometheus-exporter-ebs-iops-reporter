#!/usr/bin/env python

from sets import Set

import argparse
import boto3
import botocore
import datetime
import logging
import os
import re
import time

from prometheus_client import start_http_server, Gauge, Counter

EBS_IOPS = Gauge("ebs_iops_credits",
                 "Percent of burstable IOPS credit available", labelnames=['vol_id'])

# A list (implemented as a Set) of all active volumes.
ACTIVE_VOLUMES = Set([])

# Period in minutes from cloudwatch to request
# See https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetMetricData.html
CLOUDWATCH_PERIOD = 5

BOTO_ERRS = Counter('boto_exceptions', 'The total number of boto exceptions')


def chunks(l, n):
    """
    Chunks up an array +l+ into chunks of +n+ size
    Based on https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]


def get_utcnow():
    # Split out the request for UTC from the round_time function, built-ins cannot be mocked.
    timetoround = datetime.datetime.utcnow()
    return timetoround


def round_time(timetoround, period):
    """
    Round the current date (in utc) to the nearest +period+ minutes. 
    For example, if the current time is 16:23 and +period+ is 10 (minutes), the
    return time will be 16:20.
    Based on:
    https://stackoverflow.com/questions/3463930/how-to-round-the-minute-of-a-datetime-object-python
    """
    t = timetoround
    t += datetime.timedelta(minutes=period/2.0)
    t -= datetime.timedelta(minutes=t.minute % period,
                            seconds=t.second,
                            microseconds=t.microsecond)
    return t


def collect(aws):
    """
    Collect the current data from the AWS API
    """

    # All the volumes CloudWatch tells us it knows about (whether or not it has data)
    volumes = Set([])

    # List of volumes that we've actually had data back for the API
    seen_volumes = Set([])

    # get the volume IDs and filter the results to show only metrics that have had data points published in the past three hours
    volumePager = cw.get_paginator('list_metrics')
    for p in volumePager.paginate(MetricName='BurstBalance', Namespace='AWS/EBS'):
        for v in p['Metrics']:
            volumes.add(v['Dimensions'][0]['Value'])

    dimensionCriteria = []
    for volume in list(volumes):
        dimensionCriteria.append({
            'Id': re.sub(r'^vol-', "vol_", volume, 0),
            'MetricStat': {
                'Metric': {
                    'Namespace': 'AWS/EBS',
                    'MetricName': 'BurstBalance',
                    'Dimensions': [
                        {
                            'Name': 'VolumeId', 'Value': volume
                        }
                    ]
                },
                'Period': CLOUDWATCH_PERIOD * 36,
                'Stat': 'Average',
                'Unit': 'Percent',
            }
        }
        )

    # get data for all the volume IDs
    volumeDataPager = cw.get_paginator('get_metric_data')
    timetoround = get_utcnow()
    time_start = round_time(timetoround, CLOUDWATCH_PERIOD)
    logging.debug("Requesting from %s to %s with period of %d minutes",
                  time_start -
                  (datetime.timedelta(minutes=CLOUDWATCH_PERIOD) * 2),
                  time_start-datetime.timedelta(minutes=CLOUDWATCH_PERIOD),
                  CLOUDWATCH_PERIOD*60)

    # We have to go in chunks of 100 volumes (now, dimensionCriteria) otherwise
    # Error: The collection MetricDataQueries must not have a size greater than 100.
    # This is a limitation of the AWS CloudWatch API
    for dimensionChunk in chunks(dimensionCriteria, 100):
        # If the period is 5 minutes and the time is now 09:39 request from
        # 09:30 - 09:35
        # The intent is to get a full section of data; since 09:35-09:39 isn't a full period,
        # the data might be unreliable.
        for response in volumeDataPager.paginate(
            StartTime=time_start -
                (datetime.timedelta(minutes=CLOUDWATCH_PERIOD) * 2),
            EndTime=time_start-datetime.timedelta(minutes=CLOUDWATCH_PERIOD),
            MetricDataQueries=dimensionChunk,
        ):
            for mdr in response['MetricDataResults']:
                if len(mdr['Values']) > 0:
                    seen_volumes.add(mdr['Label'])
                    ACTIVE_VOLUMES.add(mdr['Label'])
                    EBS_IOPS.labels(vol_id=mdr['Label']).set(mdr['Values'][0])
                    logging.debug("%s has Values", mdr['Label'])
                else:
                    logging.debug("%s has no Values", mdr['Label'])

    logging.debug("Have %d ACTIVE_VOLUMES, seen %d volumes, total volumes from list_metrics %d", len(
        ACTIVE_VOLUMES), len(seen_volumes), len(volumes))
    for inactive_volume in ACTIVE_VOLUMES - seen_volumes:
        logging.info("Removing vol_id='%s' from Prometheus ", inactive_volume)
        EBS_IOPS.remove(inactive_volume)
        ACTIVE_VOLUMES.remove(inactive_volume)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')

    parser = argparse.ArgumentParser(
        description='Options for EBS IOPS Exporter')
    parser.add_argument('-p', '--aws-profile',
                        help='Name of AWS credentials profile to use', required=False, default="default")
    parser.add_argument('-r', '--aws-region', help='AWS Region to use',
                        required=False, default="us-east-1")
    args = vars(parser.parse_args())

    # Preference order for the AWS profile:
    # 1. Environment variables (AWS_PROFILE)
    # 2. Argument to program (--aws-profile)
    # 3. "default", if neither are specified

    if "AWS_PROFILE" in os.environ:
        args['aws_profile'] = os.environ['AWS_PROFILE']

    # If AWS_CONFIG_FILE is set then use the region in that file.
    # Else use the passed value or default.
    if "AWS_CONFIG_FILE" in os.environ:
        session = boto3.session.Session(profile_name=args['aws_profile'])
        args['aws_region'] = session.region_name
    else:
        session = boto3.session.Session(
            profile_name=args['aws_profile'], region_name=args['aws_region'])

    logging.info("Started ebs-iops-reporter with aws_profile=%s, aws_region=%s",
                 args['aws_profile'], args['aws_region'])

    cw = session.client('cloudwatch')

    start_http_server(8080)
    while True:
        try:
            collect(cw)
        except botocore.exceptions.ClientError as err:
            BOTO_ERRS.inc()
            logging.error("Caught boto error")
            logging.error('Error Message: {}'.format(
                err.response['Error']['Message']))
            logging.error('Request ID: {}'.format(
                err.response['ResponseMetadata']['RequestId']))
            logging.error('Http code: {}'.format(
                err.response['ResponseMetadata']['HTTPStatusCode']))
        finally:
            # Sleep for the interval
            logging.info("Going to sleep for %d seconds", CLOUDWATCH_PERIOD*60)
            time.sleep(CLOUDWATCH_PERIOD * 60)
