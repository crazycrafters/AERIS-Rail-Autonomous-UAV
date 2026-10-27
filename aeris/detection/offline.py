"""Small trainable diagonal-normality baseline on pre-extracted numeric features.

This is not an image detector. Feature extractors must be fixed before evaluation.
"""
import json
import math
from pathlib import Path
from statistics import mean, pstdev


def read_records(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if not rows:
        raise ValueError('Empty dataset')
    ids = set()
    dimension = None
    for row in rows:
        if not isinstance(row.get('id'), str) or not row['id'] or row['id'] in ids:
            raise ValueError('Each observation needs a unique nonempty id')
        ids.add(row['id'])
        if row.get('split') not in ('train', 'validation', 'test'):
            raise ValueError('Unknown dataset split')
        if not isinstance(row.get('site'), str) or not row['site']:
            raise ValueError('Missing site')
        if row.get('label') not in ('normal', 'anomaly'):
            raise ValueError('Expected normal/anomaly label')
        if type(row.get('quality_ok')) is not bool:
            raise ValueError('quality_ok must be boolean')
        features = row.get('features')
        if not isinstance(features, list) or not features:
            raise ValueError('Expected nonempty feature vector')
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in features):
            raise ValueError('Features must be finite numbers')
        dimension = dimension or len(features)
        if len(features) != dimension:
            raise ValueError('Feature dimensions differ')
        segment = row.get('segment')
        if type(segment) is not int or segment < 0:
            raise ValueError('segment must be a nonnegative integer')
    sites = {}
    for row in rows:
        previous = sites.setdefault(row['site'], row['split'])
        if previous != row['split']:
            raise ValueError('Site leakage across dataset splits')
    return rows


class NormalityModel:
    def __init__(self, center, scale, threshold):
        if not center or len(center) != len(scale):
            raise ValueError('Invalid model dimensions')
        if not all(math.isfinite(x) for x in center + scale + [threshold]):
            raise ValueError('Invalid model values')
        if min(scale) <= 0 or threshold < 0:
            raise ValueError('Invalid model scale or threshold')
        self.center, self.scale, self.threshold = center, scale, threshold

    def score(self, features):
        if len(features) != len(self.center) or not all(math.isfinite(x) for x in features):
            raise ValueError('Invalid inference features')
        return math.sqrt(mean(((x - m) / s) ** 2 for x, m, s in zip(features, self.center, self.scale)))

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(version=1, kind='diagonal_normality',
                                       center=self.center, scale=self.scale, threshold=self.threshold), indent=2))

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text())
        if data['version'] != 1 or data['kind'] != 'diagonal_normality':
            raise ValueError('Unsupported model')
        return cls(data['center'], data['scale'], data['threshold'])


def train(rows, false_alarm_rate=0.05):
    if not 0 < false_alarm_rate < 1:
        raise ValueError('False alarm rate must be between 0 and 1')
    normals = [r['features'] for r in rows if r['split'] == 'train' and r['label'] == 'normal' and r['quality_ok']]
    validation = [r['features'] for r in rows if r['split'] == 'validation' and r['label'] == 'normal' and r['quality_ok']]
    if len(normals) < 2 or not validation:
        raise ValueError('Need >=2 accepted training normals and >=1 validation normal')
    columns = list(zip(*normals))
    model = NormalityModel([mean(c) for c in columns], [max(pstdev(c), 1e-6) for c in columns], 0)
    scores = sorted(model.score(x) for x in validation)
    model.threshold = scores[max(0, math.ceil((1 - false_alarm_rate) * len(scores)) - 1)]
    return model


def evaluate(model, rows):
    test = [r for r in rows if r['split'] == 'test']
    accepted = [r for r in test if r['quality_ok']]
    if not accepted or {r['label'] for r in accepted} != {'normal', 'anomaly'}:
        raise ValueError('Evaluation needs accepted test normals and anomalies')
    tp = fp = tn = fn = 0
    for row in accepted:
        alert = model.score(row['features']) > model.threshold
        anomaly = row['label'] == 'anomaly'
        tp += alert and anomaly
        fp += alert and not anomaly
        tn += not alert and not anomaly
        fn += not alert and anomaly
    return dict(accepted=len(accepted), quality_rejected=len(test)-len(accepted),
                true_positive=tp, false_positive=fp, true_negative=tn, false_negative=fn,
                precision=tp/(tp+fp) if tp+fp else None, recall=tp/(tp+fn),
                false_positive_rate=fp/(fp+tn), threshold=model.threshold)


class FeatureReplayDetector:
    """Offline adapter uses only features and quality; ignores labels at inference."""
    def __init__(self, model, rows):
        self.model = model
        self.rows = {}
        for row in rows:
            if row['split'] != 'test':
                continue
            if row['segment'] in self.rows:
                raise ValueError('Replay requires one test observation per segment')
            self.rows[row['segment']] = row

    def observe(self, segment):
        row = self.rows.get(segment)
        if row is None:
            return dict(segment=segment, quality_ok=False, known_score=0.0,
                        anomaly_score=0.0, review_required=False, source='missing_observation')
        score = self.model.score(row['features'])
        return dict(segment=segment, quality_ok=row['quality_ok'], known_score=0.0,
                    anomaly_score=score,
                    review_required=row['quality_ok'] and score > self.model.threshold,
                    source='offline_features', evidence_id=row['id'])
