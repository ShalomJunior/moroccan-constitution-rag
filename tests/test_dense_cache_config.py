import os
import unittest
from pathlib import Path
from unittest.mock import patch

from constitution_evidence.retrieval import dense_index_dir, model_cache_dir


class DenseCacheConfigContracts(unittest.TestCase):
    def test_default_and_container_paths(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(dense_index_dir(Path('/tmp/default-index')), Path('/tmp/default-index'))
            self.assertIsNone(model_cache_dir())
        with patch.dict(os.environ, {'CONSTITUTION_DENSE_INDEX': '/app/data/models/index',
                                     'CONSTITUTION_MODEL_CACHE': '/app/data/models/cache'}):
            self.assertEqual(dense_index_dir(Path('/tmp/default-index')), Path('/app/data/models/index'))
            self.assertEqual(model_cache_dir(), '/app/data/models/cache')


if __name__ == '__main__':
    unittest.main()
