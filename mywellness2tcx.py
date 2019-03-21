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
    #print(data['data'].keys())

    samples = []
    for sample in analitics['samples']:
        dt = start_dt + timedelta(seconds=sample['t'])
        values = dict(zip(fields, sample['vs']))
        samples.append((dt, values))

    while samples:
        dt, sample = samples[-1]
        if sample['Speed'] != 0 or sample['Power'] != 0:
            break
        samples.pop()

    prev_dt, sample = samples[0]
    dist = sample['HDistance']
    for dt, sample in samples[1:]:
        dist += (dt - prev_dt).seconds * sample['Speed'] / 3.6
        prev_dt = dt
    coeff = sample['HDistance'] / dist

    prev_dt, sample = samples[0]
    dist = sample['HDistance']
    sample['SmoothDistance'] = dist
    for dt, sample in samples[1:]:
        dist += (dt - prev_dt).seconds * sample['Speed'] / 3.6 * coeff
        sample['SmoothDistance'] = dist
        #print(f"{sample['SmoothDistance'] - sample['HDistance']:.1f}")
        prev_dt = dt

    tcd = et.Element('TrainingCenterDatabase', xmlns=TCD_NS)
    activities = et.SubElement(tcd, 'Activities')
    activity = et.SubElement(activities, 'Activity', Sport='Biking')
    et.SubElement(activity, 'Id').text = iso(start_dt) # TODO Use GUID
    lap = et.SubElement(activity, 'Lap', StartTime=iso(start_dt))
    track = et.SubElement(lap, 'Track')

    for dt, values in samples:
        point = et.SubElement(track, 'Trackpoint')
        et.SubElement(point, 'Time').text = iso(dt)
        et.SubElement(point, 'DistanceMeters').text = str(values['SmoothDistance'])
        et.SubElement(point, 'Cadence').text = str(values['Rpm'])
        extensions = et.SubElement(point, 'Extensions')
        tpx = et.SubElement(extensions, 'TPX', xmlns=AX_NS)
        et.SubElement(tpx, 'Speed').text = str(values['Speed'])
        et.SubElement(tpx, 'Watts').text = str(values['Power'])

    doc = et.ElementTree(tcd)

    #print(etree.tostring(doc, pretty_print=True, xml_declaration=True).decode('utf-8'))
    with open(out_file, 'wb') as out_fp:
        doc.write(out_fp, encoding='ascii', xml_declaration=True)


if __name__ == '__main__':
    in_file = sys.argv[1]
    base_name = (
        in_file[:-5] if in_file.lower().endswith('.json')
        else in_file
    )
    out_file = base_name + '.tcx'

    start_dt = datetime.strptime(sys.argv[2], '%Y-%m-%dT%H:%M')

    mywellness2tcx(in_file, out_file, start_dt)
