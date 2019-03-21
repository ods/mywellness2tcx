#!/usr/bin/env python

from datetime import datetime, timedelta
import json
import sys
from xml.etree import ElementTree as et


TCD_NS = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'
AX_NS = 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def mywellness2tcx(in_file, out_file, start_dt):
    with open(in_file) as fp:
        data = json.load(fp)

    analitics = data['data']['analitics']
    fields = [
        descriptor['pr']['name']
        for descriptor in analitics['descriptor']
    ]

    samples = []
    for sample in analitics['samples']:
        dt = start_dt + timedelta(seconds=sample['t'])
        values = dict(zip(fields, sample['vs']))
        samples.append((dt, values))

    # Strip point at the end with no activity
    while samples:
        dt, sample = samples[-1]
        if sample['Speed'] != 0 or sample['Power'] != 0:
            break
        samples.pop()

    # Distances in HDistance are very inaccurate.  Loading them to Strava will
    # lead to calculated speed having interchanging 0 and 72 km/h values only
    # and sawtooth graph for it.

    # Calclulate distance from recorded speed data
    prev_dt, sample = samples[0]
    dist = sample['HDistance']
    for dt, sample in samples[1:]:
        dist += (dt - prev_dt).seconds * sample['Speed'] / 3.6
        prev_dt = dt

    # Correction factor to get the same total distance
    # TODO Do smoothing within moving window to get closer distances at eache
    # point, not just at the end.
    fact = sample['HDistance'] / dist
    # Something went wrong if it's not close to 1
    assert 0.95 < fact < 1.05

    # Recalculate distances once more, now with correction factor
    prev_dt, sample = samples[0]
    dist = sample['HDistance']
    sample['SmoothDistance'] = dist
    for dt, sample in samples[1:]:
        dist += (dt - prev_dt).seconds * sample['Speed'] / 3.6 * fact
        sample['SmoothDistance'] = dist
        #print(f"{sample['SmoothDistance'] - sample['HDistance']:.1f}")
        prev_dt = dt

    # Dump the activity into XML

    tcd = et.Element('TrainingCenterDatabase', xmlns=TCD_NS)
    activities = et.SubElement(tcd, 'Activities')
    activity = et.SubElement(activities, 'Activity', Sport='Biking')
    # Id field hase type xsd:dateTime!
    et.SubElement(activity, 'Id').text = iso(start_dt)
    lap = et.SubElement(activity, 'Lap', StartTime=iso(start_dt))
    track = et.SubElement(lap, 'Track')

    for dt, sample in samples:
        point = et.SubElement(track, 'Trackpoint')
        et.SubElement(point, 'Time').text = iso(dt)
        et.SubElement(point, 'DistanceMeters').text = str(sample['SmoothDistance'])
        et.SubElement(point, 'Cadence').text = str(sample['Rpm'])
        extensions = et.SubElement(point, 'Extensions')
        tpx = et.SubElement(extensions, 'TPX', xmlns=AX_NS)
        et.SubElement(tpx, 'Speed').text = str(sample['Speed'] / 3.6)
        et.SubElement(tpx, 'Watts').text = str(sample['Power'])

    doc = et.ElementTree(tcd)

    with open(out_file, 'wb') as out_fp:
        doc.write(out_fp, encoding='ascii', xml_declaration=True)


if __name__ == '__main__':
    in_file = sys.argv[1]
    base_name = (
        in_file[:-5] if in_file.lower().endswith('.json')
        else in_file
    )
    out_file = base_name + '.tcx'

    # There is no time in JSON and date is in localized format only
    start_dt = datetime.strptime(sys.argv[2], '%Y-%m-%dT%H:%M')

    mywellness2tcx(in_file, out_file, start_dt)
