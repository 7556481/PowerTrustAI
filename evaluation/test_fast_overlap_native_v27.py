"""Required native stored-payload contract; dedicated CI installs frozen Tantivy."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from core.models import Evidence,EvidenceProvenance

class PackedLookupTests(unittest.TestCase):
    def test_old_identity_and_original_payload_need_no_sqlite(self):
        import tantivy,sqlite3
        from evaluation.fast_overlap_pack_v27 import PackedCatalog,sha
        from backend.serialization import wire
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);native=root/'index';native.mkdir();schema=tantivy.SchemaBuilder();schema.add_text_field('fid',stored=True,tokenizer_name='raw');schema.add_text_field('terms',stored=True);schema.add_bytes_field('payload',stored=True)
            index=tantivy.Index(schema.build(),path=str(native));writer=index.writer(heap_size=20000000,num_threads=1)
            text='alpha beta';provenance=EvidenceProvenance('doc','doc-v','f'*64,'legacy-fid','k',0,len(text),1,1)
            e=Evidence('legacy-id','doc','doc-v','chars[0:10)',text,'synthetic_fixture',provenance=provenance)
            payload=json.dumps({'evidence':wire(e),'terms_sha':hashlib.sha256(text.encode()).hexdigest(),'body_sha':hashlib.sha256(text.encode()).hexdigest()}).encode();doc=tantivy.Document();doc.add_text('fid','legacy-fid');doc.add_text('terms',text);doc.add_bytes('payload',payload);writer.add_document(doc);writer.commit();writer.wait_merging_threads();index.reload()
            (root/'asset.json').write_text(json.dumps({'knowledge_version':'k','files':{p.name:sha(p) for p in native.iterdir() if p.is_file() and not p.name.endswith('.lock')}}))
            with patch.object(sqlite3,'connect',side_effect=PermissionError('unavailable')):
                catalog=PackedCatalog(root);self.assertEqual(catalog.evidence('legacy-fid','k'),e);self.assertEqual(catalog.verify_evidence(e),e)
