#!/usr/bin/env python3
"""
contents 스냅샷 및 비교 도구

Usage:
  # 1) 현재 contents 컬렉션을 스냅샷으로 저장
  python3 tools/snapshot_compare_contents.py snapshot --mongo-uri mongodb://ksubscribe_mongodb:27017 --out ./snapshots/run1.json

  # 2) 나중에 두 스냅샷을 비교
  python3 tools/snapshot_compare_contents.py compare --old ./snapshots/run1.json --new ./snapshots/run2.json --out ./snapshots/diff_run1_run2.json

  # 옵션: --fields 필드 목록(콤마 구분)만 저장 (기본: _id,url,title,rawCollectDt,metaAnalyzeDt)

The script stores minimal metadata per document and can compute added/removed/unchanged sets.

Note:
- 이 스크립트는 컨테이너 내부에서 실행하도록 설계되었습니다. 로컬에서 실행하려면 MongoDB 접속 정보(--mongo-uri) 를 적절히 지정하세요.
- 필요 패키지: pymongo (컨테이너에 설치되어 있으면 바로 사용 가능). 설치가 필요하면 `pip install pymongo`.
"""

import argparse
import json
import os
import sys
from datetime import datetime

try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None

DEFAULT_FIELDS = ["_id", "url", "title", "rawCollectDt", "metaAnalyzeDt"]


def iso_now():
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def connect_mongo(uri):
    if MongoClient is None:
        print("pymongo가 설치되어 있지 않습니다. 컨테이너 내부에서 실행하거나 'pip install pymongo'를 수행하세요.")
        sys.exit(1)
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def do_snapshot(mongo_uri, out_path, fields):
    client = connect_mongo(mongo_uri)
    db = client.get_database('mycontents')
    coll = db.get_collection('contents')

    projection = {f: 1 for f in fields}
    cursor = coll.find({}, projection)

    docs = []
    for d in cursor:
        # convert ObjectId and datetimes to strings
        item = {}
        for f in fields:
            v = d.get(f)
            if f == '_id':
                item['_id'] = str(v)
            elif isinstance(v, datetime):
                item[f] = v.isoformat()
            else:
                item[f] = v
        docs.append(item)

    meta = {
        'created_at': datetime.utcnow().isoformat(),
        'count': len(docs),
        'fields': fields,
    }

    payload = {'meta': meta, 'docs': docs}

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Snapshot saved: {out_path} (count={len(docs)})")


def do_compare(old_path, new_path, out_path=None):
    with open(old_path, 'r', encoding='utf-8') as f:
        old = json.load(f)
    with open(new_path, 'r', encoding='utf-8') as f:
        new = json.load(f)

    old_ids = {d['_id'] for d in old['docs']}
    new_ids = {d['_id'] for d in new['docs']}

    added = new_ids - old_ids
    removed = old_ids - new_ids
    common = old_ids & new_ids

    # Map id->doc for more info (url/title)
    new_map = {d['_id']: d for d in new['docs']}
    old_map = {d['_id']: d for d in old['docs']}

    report = {
        'old_snapshot': os.path.basename(old_path),
        'new_snapshot': os.path.basename(new_path),
        'old_count': old['meta'].get('count'),
        'new_count': new['meta'].get('count'),
        'added_count': len(added),
        'removed_count': len(removed),
        'common_count': len(common),
        'added': [],
        'removed': [],
    }

    for _id in sorted(added):
        d = new_map.get(_id, {})
        report['added'].append({'_id': _id, 'url': d.get('url'), 'title': d.get('title')})

    for _id in sorted(removed):
        d = old_map.get(_id, {})
        report['removed'].append({'_id': _id, 'url': d.get('url'), 'title': d.get('title')})

    if out_path:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"Comparison saved: {out_path}")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    print(f"Old count: {report['old_count']}, New count: {report['new_count']}")
    print(f"Added: {report['added_count']}, Removed: {report['removed_count']}, Common: {report['common_count']}")


def parse_args():
    p = argparse.ArgumentParser(description='Snapshot and compare contents collection')
    sub = p.add_subparsers(dest='cmd')

    s1 = sub.add_parser('snapshot', help='Create a snapshot JSON of contents collection')
    s1.add_argument('--mongo-uri', default='mongodb://ksubscribe_mongodb:27017', help='MongoDB URI')
    s1.add_argument('--out', required=True, help='Output snapshot file path (e.g. snapshots/run1.json)')
    s1.add_argument('--fields', default=','.join(DEFAULT_FIELDS), help='Comma-separated fields to include')

    s2 = sub.add_parser('compare', help='Compare two snapshot JSON files')
    s2.add_argument('--old', required=True)
    s2.add_argument('--new', required=True)
    s2.add_argument('--out', help='Optional output file for comparison result')

    return p.parse_args()


def main():
    args = parse_args()
    if args.cmd == 'snapshot':
        fields = [f.strip() for f in args.fields.split(',') if f.strip()]
        do_snapshot(args.mongo_uri, args.out, fields)
    elif args.cmd == 'compare':
        do_compare(args.old, args.new, args.out)
    else:
        print('사용법: snapshot 또는 compare 명령을 사용하세요. 예:')
        print('  python3 tools/snapshot_compare_contents.py snapshot --out snapshots/run1.json')
        print('  python3 tools/snapshot_compare_contents.py compare --old snapshots/run1.json --new snapshots/run2.json')


if __name__ == '__main__':
    main()
