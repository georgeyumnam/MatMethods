# coding: utf-8

from __future__ import division, print_function, unicode_literals, absolute_import

"""
This module defines the database classes.
"""

import zlib
import json

from pymatgen.electronic_structure.bandstructure import BandStructure, BandStructureSymmLine

import gridfs
from pymongo import ASCENDING, DESCENDING

from matmethods.utils.database import MMDb
from matmethods.utils.utils import get_logger

__author__ = 'Kiran Mathew'
__credits__ = 'Anubhav Jain'
__email__ = 'kmathew@lbl.gov'

logger = get_logger(__name__)


class MMVaspDb(MMDb):
    """
    Class to help manage database insertions of Vasp drones
    """

    def __init__(self, host="localhost", port=27017, database="vasp", collection="tasks", user=None,
                 password=None):
        super(MMVaspDb, self).__init__(host, port, database, collection, user, password)

    def build_indexes(self, indexes=None, background=True):
        """
        Build the indexes.

        Args:
            indexes (list): list of single field indexes to be built.
            background (bool): Run in the background or not.

        TODO: make sure that the index building is sensible and check for
            existing indexes.
        """
        _indices = indexes if indexes else ["formula_pretty", "formula_anonymous",
                                            "output.energy", "output.energy_per_atom"]
        self.collection.create_index("task_id", unique=True, background=background)
        # build single field indexes
        for i in _indices:
            self.collection.create_index(i, background=background)
        # build compound indexes
        for formula in ("formula_pretty", "formula_anonymous"):
            self.collection.create_index([(formula, ASCENDING),
                                          ("output.energy", DESCENDING),
                                          ("completed_at", DESCENDING)],
                                         background=background)
            self.collection.create_index([(formula, ASCENDING),
                                          ("output.energy_per_atom", DESCENDING),
                                          ("completed_at", DESCENDING)],
                                         background=background)

    def insert_gridfs(self, d, collection="fs", compress=True):
        """
        Insert the given document into GridFS.

        Args:
            d (dict): the document
            collection (string): the GridFS collection name
            compress (bool): Whether to compress the data or not

        Returns:
            file id, the type of compression used.
        """
        if compress:
            d = zlib.compress(d.encode(), compress)
        fs = gridfs.GridFS(self.db, collection)
        fs_id = fs.put(d)
        return fs_id, "zlib"

    def get_band_structure(self, task_id, line_mode=False):
        m_task = self.collection.find_one({"task_id": task_id},
                                          {"calcs_reversed": 1})
        fs_id = m_task['calcs_reversed'][0]['bandstructure_fs_id']
        fs = gridfs.GridFS(self.db, 'bandstructure_fs')
        bs_json = zlib.decompress(fs.get(fs_id).read())
        bs_dict = json.loads(bs_json)
        if line_mode:
            return BandStructureSymmLine.from_dict(bs_dict)
        else:
            return BandStructure.from_dict(bs_dict)

    def reset(self):
        self.collection.delete_many({})
        self.db.counter.delete_one({"_id": "taskid"})
        self.db.counter.insert_one({"_id": "taskid", "c": 0})
        self.db.boltztrap.delete_many({})
        self.db.dos_fs.files.delete_many({})
        self.db.dos_fs.chunks.delete_many({})
        self.db.dos_boltztrap_fs.files.delete_many({})
        self.db.dos_boltztrap_fs.chunks.delete_many({})
        self.db.bandstructure_fs.files.delete_many({})
        self.db.bandstructure_fs.chunks.delete_many({})
        self.build_indexes()


class MMBoltztrapDb(MMDb):
    # TODO: add Boltztrap management here
    pass
