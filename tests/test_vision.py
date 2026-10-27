"""Dataset and evidence tests; train/infer integration also has a geometry smoke run."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from aeris.vision.dataset import validate, sha256
from aeris.vision.pipeline import ImageReplayDetector, replay_images, new_directory

AVAILABLE = all(importlib.util.find_spec(n) for n in ('PIL','yaml'))


@unittest.skipUnless(AVAILABLE, 'optional Pillow and PyYAML required')
class VisionTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows=[]
        for i,split in enumerate(('train','val','test')):
            for folder in ('images','labels'):
                (self.root/folder/split).mkdir(parents=True)
            image=Path('images')/split/'frame.png'
            Image.new('RGB',(32,32),(i*60,0,0)).save(self.root/image)
            (self.root/'labels'/split/'frame.txt').write_text('0 0.5 0.5 0.5 0.5\n')
            self.rows.append(dict(image=image.as_posix(),site=split,session=split,asset_group=split,split=split))
        self.data=self.root/'data.yaml'
        self.data.write_text(f'path: {self.root.as_posix()}\ntrain: images/train\nval: images/val\ntest: images/test\nnames: [fastener_missing]\n')
        self.manifest=self.root/'manifest.csv'
        self.write_manifest()

    def write_manifest(self):
        with self.manifest.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(self.rows[0]));w.writeheader();w.writerows(self.rows)

    def test_valid_annotations_audited(self):
        report=validate(self.data,self.manifest)
        self.assertEqual(report['splits']['train']['boxes_by_class'],{'fastener_missing':1})

    def test_out_of_bounds_box_rejected(self):
        (self.root/'labels/train/frame.txt').write_text('0 0.9 0.5 0.8 0.5')
        with self.assertRaisesRegex(ValueError,'bounds'):
            validate(self.data,self.manifest)

    def test_missing_label_not_treated_as_negative(self):
        (self.root/'labels/test/frame.txt').unlink()
        with self.assertRaisesRegex(ValueError,'Missing annotation'):
            validate(self.data,self.manifest)

    def test_split_leakage_rejected(self):
        self.rows[2]['site']='train';self.write_manifest()
        with self.assertRaisesRegex(ValueError,'leakage'):
            validate(self.data,self.manifest)

    def test_duplicate_content_across_sites_rejected(self):
        (self.root/'images/test/frame.png').write_bytes((self.root/'images/train/frame.png').read_bytes())
        with self.assertRaisesRegex(ValueError,'Duplicate image'):
            validate(self.data,self.manifest)

    def test_replay_requires_observability(self):
        image=self.root/'images/test/frame.png'
        predictions=self.root/'predictions.json'
        predictions.write_text(json.dumps([dict(image_sha256=sha256(image),weights_sha256='fixture',
            detections=[dict(class_name='fastener_missing',confidence=.8,xyxy=[0,0,10,10])])]))
        manifest=self.root/'replay.json'
        manifest.write_text(json.dumps([dict(segment=0,image=str(image),quality_ok=True,asset_observed=False)]))
        detector=ImageReplayDetector(predictions,manifest,['fastener_missing'])
        self.assertFalse(detector.observe(0)['quality_ok'])
        self.assertFalse(detector.observe(0)['review_required'])
        report=replay_images(predictions,manifest,['fastener_missing'],self.root/'replay')
        self.assertEqual(report['status'],'image_quality_blocked')
        self.assertEqual(report['covered_segments'],0)
        row=json.loads(manifest.read_text());row[0]['asset_observed']=True
        manifest.write_text(json.dumps(row))
        report=replay_images(predictions,manifest,['fastener_missing'],self.root/'accepted')
        self.assertEqual(report['status'],'completed')
        resumed=replay_images(predictions,manifest,['fastener_missing'],self.root/'resumed',
                              resume=self.root/'accepted/checkpoint.json')
        self.assertEqual(resumed['sorties'],0)
        row[0]['quality_ok']=False
        manifest.write_text(json.dumps(row))
        with self.assertRaisesRegex(ValueError,'inputs differ'):
            replay_images(predictions,manifest,['fastener_missing'],self.root/'wrong-resume',
                          resume=self.root/'accepted/checkpoint.json')

    def test_output_overwrite_rejected(self):
        with self.assertRaisesRegex(ValueError,'overwrite'):
            new_directory(self.root)


class ReportTests(unittest.TestCase):
    def test_evidence_is_escaped(self):
        from aeris.report import render
        output=render(dict(status='completed',observations=[dict(segment=0,evidence_id='<script>alert(1)</script>')]))
        self.assertNotIn('<script>',output)
        self.assertIn('&lt;script&gt;',output)


if __name__=='__main__':
    unittest.main()
