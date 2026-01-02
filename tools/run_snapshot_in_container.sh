#!/usr/bin/env bash
# 컨테이너 내부에서 snapshot/compare 작업을 실행하는 래퍼 스크립트
# 사용법:
#   호스트에서 실행:
#     ./tools/run_snapshot_in_container.sh snapshot /app/snapshots/run1.json
#     ./tools/run_snapshot_in_container.sh compare /app/snapshots/run1.json /app/snapshots/run2.json /app/snapshots/diff.json
# 설명:
# - 이 스크립트는 로컬에 있는 Python 스크립트를 컨테이너로 복사하지 않고, 컨테이너에서 직접 Python 코드를 실행합니다.
# - 컨테이너 이름은 기본값으로 ksubscribe_python_unified를 사용합니다. 필요하면 CONTAINER 환경변수로 변경하세요.
# - 컨테이너 내부에 pymongo가 설치되어 있어야 합니다.

set -euo pipefail
CONTAINER=${CONTAINER:-ksubscribe_python_unified}
CMD=${1:-}

function usage(){
  cat <<'USAGE'
Usage:
  snapshot: ./tools/run_snapshot_in_container.sh snapshot /app/snapshots/run1.json
  compare:  ./tools/run_snapshot_in_container.sh compare /app/snapshots/run1.json /app/snapshots/run2.json /app/snapshots/diff.json
Environment:
  CONTAINER: 컨테이너 이름 (기본: ksubscribe_python_unified)
Notes:
  - 출력 경로(예: /app/snapshots/...)는 컨테이너 내부 경로입니다. 컨테이너의 /app 경로가 호스트의 프로젝트 루트와 바인드되어 있다면 호스트에서 해당 파일을 바로 확인할 수 있습니다.
USAGE
}

if [[ "$CMD" == "snapshot" ]]; then
  OUT=${2:-}
  if [[ -z "$OUT" ]]; then
    echo "snapshot 명령 사용법: $0 snapshot /app/snapshots/run1.json"
    exit 1
  fi

  docker exec -i "$CONTAINER" sh -c "python3 - <<'PY'
import json
import os
from datetime import datetime
from pymongo import MongoClient

out = '$OUT'
client = MongoClient('mongodb://ksubscribe_mongodb:27017', serverSelectionTimeoutMS=5000)
db = client['mycontents']
coll = db['contents']
fields = ['_id','url','title','rawCollectDt','metaAnalyzeDt']
projection = {f: 1 for f in fields}

cursor = coll.find({}, projection)
docs = []
for d in cursor:
    item = {}
    for f in fields:
        v = d.get(f)
        if f == '_id':
            item['_id'] = str(v)
        elif hasattr(v, 'isoformat'):
            item[f] = v.isoformat()
        else:
            item[f] = v
    docs.append(item)

meta = {'created_at': datetime.utcnow().isoformat(), 'count': len(docs), 'fields': fields}
payload = {'meta': meta, 'docs': docs}

os.makedirs(os.path.dirname(out) or '/', exist_ok=True)
with open(out, 'w', encoding='utf-8') as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print('Snapshot saved:', out, 'count=', len(docs))
PY"

  echo "스냅샷이 컨테이너 내부에 생성되었습니다: $OUT"
  exit 0

elif [[ "$CMD" == "compare" ]]; then
  OLD=${2:-}
  NEW=${3:-}
  OUT=${4:-}
  if [[ -z "$OLD" || -z "$NEW" ]]; then
    echo "compare 명령 사용법: $0 compare /app/snapshots/old.json /app/snapshots/new.json /app/snapshots/diff.json"
    exit 1
  fi

  docker exec -i "$CONTAINER" sh -c "python3 - <<'PY'
import json
import os
old_path = '$OLD'
new_path = '$NEW'
out_path = '$OUT' if '$OUT'!='' else None

with open(old_path, 'r', encoding='utf-8') as f:
    old = json.load(f)
with open(new_path, 'r', encoding='utf-8') as f:
    new = json.load(f)

old_ids = {d['_id'] for d in old['docs']}
new_ids = {d['_id'] for d in new['docs']}
added = sorted(list(new_ids - old_ids))
removed = sorted(list(old_ids - new_ids))
common = sorted(list(old_ids & new_ids))
new_map = {d['_id']: d for d in new['docs']}
old_map = {d['_id']: d for d in old['docs']}

report = {'old_snapshot': os.path.basename(old_path), 'new_snapshot': os.path.basename(new_path),
          'old_count': old['meta'].get('count'), 'new_count': new['meta'].get('count'),
          'added_count': len(added), 'removed_count': len(removed), 'common_count': len(common),
          'added': [], 'removed': []}

for _id in added:
    d = new_map.get(_id,{})
    report['added'].append({'_id': _id, 'url': d.get('url'), 'title': d.get('title')})
for _id in removed:
    d = old_map.get(_id,{})
    report['removed'].append({'_id': _id, 'url': d.get('url'), 'title': d.get('title')})

if out_path:
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print('Comparison saved:', out_path)
else:
    print(json.dumps(report, ensure_ascii=False, indent=2))

print('Old count:', report['old_count'], 'New count:', report['new_count'])
print('Added:', report['added_count'], 'Removed:', report['removed_count'], 'Common:', report['common_count'])
PY"

  echo "비교 작업 완료"
  exit 0

else
  usage
  exit 1
fi
