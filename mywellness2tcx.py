#!/usr/bin/env python

from datetime import datetime, timedelta
import json
import sys

from lxml import etree

from eplant import ElementPlant


plant = ElementPlant(
    default_namespace='http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
    nsmap={
        'ax': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2',
    }
)

tcd, ax = plant.namespaces('', 'ax')


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
    current_dist = None
    current_dist_samples = []
    for sample in analitics['samples']:
        dt = start_dt + timedelta(seconds=sample['t'])
        values = dict(zip(fields, sample['vs']))
        samples.append((dt, values))

        dist = values['HDistance']
        if dist == current_dist:
            current_dist_samples.append(values)
        else:
            if current_dist is not None:
                diff = dist - current_dist
                incr = diff / len(current_dist_samples)
                for i, values_to_change in enumerate(current_dist_samples):
                    values_to_change['NormDistance'] = current_dist + i * incr
            current_dist = dist
            current_dist_samples = [values]
    for values_to_change in current_dist_samples:
        values_to_change['NormDistance'] = current_dist

    points = []
    for dt, values in samples:

        points.append(
            tcd.Trackpoint(
                tcd.Time(iso(dt)),
                tcd.DistanceMeters(str(values['NormDistance'])),
                tcd.Cadence(str(values['Rpm'])),
                tcd.Extensions(
                    ax.TPX(
                        ax.Speed(str(values['Speed'])),
                        ax.Watts(str(values['Power'])),
                    ),
                )
            )
        )

    doc = tcd.TrainingCenterDatabase(
        tcd.Activities(
            tcd.Activity(
                {'Sport': 'Biking'},
                tcd.Id(iso(start_dt)),
                tcd.Lap(
                    {'StartTime': iso(start_dt)},
                    tcd.Track(
                        *points,
                    )
                )
            )
        )
    )

    #print(etree.tostring(doc, pretty_print=True, xml_declaration=True).decode('utf-8'))
    with open(out_file, 'wb') as out_fp:
        out_fp.write(etree.tostring(doc, pretty_print=True, xml_declaration=True))


if __name__ == '__main__':
    in_file = sys.argv[1]
    base_name = (
        in_file[:-5] if in_file.lower().endswith('.json')
        else in_file
    )
    out_file = base_name + '.tcx'

    start_dt = datetime.strptime(sys.argv[2], '%Y-%m-%dT%H:%M')

    mywellness2tcx(in_file, out_file, start_dt)
