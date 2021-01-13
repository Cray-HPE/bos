#!/usr/bin/env python3
# Copyright 2020, Cray Inc.

import copy
import datetime
import logging
import os
import pytest
import random
import types
import unittest

import connexion
import flask
from flask import url_for
from builtins import staticmethod

os.environ["ETCD_HOST"] = 'localhost'
os.environ["ETCD_PORT"] = '2379'

from bos.controllers.v1.status import InvalidCategory, BadPhase, BootSetDoesNotExist  # noqa: E402
from bos.controllers.v1.status import Session, BootSet, Metadata, get_v1_session_status  # noqa: E402
from bos.controllers.v1.status import update_v1_session_status_by_bootset  # noqa: E402
from bos.controllers.v1.status import create_v1_boot_set_status  # noqa: E402
from bos.controllers.v1.status import get_v1_session_status_by_bootset  # noqa: E402
from bos.controllers.v1.status import get_v1_session_status_by_bootset_and_phase_and_category  # noqa: E402
from bos.controllers.v1.status import MetadataPhase, get_v1_session_status_by_bootset_and_phase  # noqa: E402
from bos.controllers.v1.status import create_v1_session_status, update_v1_session_status  # noqa: E402
from bos.dbclient import BosEtcdClient  # noqa: E402
from bos.models.generic_metadata import GenericMetadata  # noqa: E402

LOGGER = logging.getLogger(__name__)


class TestBosEtcdClient():

    def testPut(self):
        s = BosEtcdClient()
        s.put('key', 'value')
        value, metadata = s.get('key')
        assert value.decode('utf-8') == 'value'
        print("Metadata: %s", metadata)


def _compare_phasecategory(cat1, cat2):
    assert cat1.name == cat2.name
    assert cat1.nodes == cat2.nodes


def _compare_objects(obj1, obj2, attribute_list):
    """
    Compare the specified attributes of two objects
    """
    if not isinstance(attribute_list, list):
        raise ValueError("attribute_list is not a list.")
    for attribute in attribute_list:
        assert getattr(obj1, attribute) == getattr(obj2, attribute)


def _compare_phases(phase1, phase2):
    """
    Compare two phases, except for metadata
    """
    for attrib in ['name', 'errors', 'categories']:
        assert getattr(phase1, attrib) == getattr(phase2, attrib)


def _compare_categories(cat1, cat2):
    """
    Compare two categories, except for metadata
    """
    for attrib in ['name', 'node_list']:
        assert getattr(cat1, attrib) == getattr(cat2, attrib)


def _compare_bootset(bootset1, bootset2):
    for attribute in ['name', 'links', 'session']:
        assert getattr(bootset1, attribute) == getattr(bootset2, attribute)
    for i, phase1 in enumerate(bootset1.phases):
        phase_comp = bootset2.get_phase(bootset1.phases[i].name)
        _compare_phases(phase1, phase_comp)
#        for attrib in ['name', 'errors', 'categories']:
#            assert getattr(bootset1.phases[i], attrib) == getattr(bootset2.phases[j], attrib)


def _convert_metadata(metadata):
    dikt = {}
    if hasattr(metadata, 'start_time'):
        dikt['start_time'] = metadata.start_time
    if hasattr(metadata, 'stop_time'):
        dikt['stop_time'] = metadata.stop_time
    if hasattr(metadata, 'complete'):
        dikt['complete'] = metadata.complete
    if hasattr(metadata, 'in_progress'):
        dikt['in_progress'] = metadata.in_progress
    if hasattr(metadata, 'error_count'):
        dikt['error_count'] = metadata.error_count
    # return GenericMetadata(**dikt)
    return dikt


example_boot_set = {'name': 'test-boot-set',
                    'metadata': None,
                    'phases': [{'name': 'shutdown',
                                'metadata': {'complete': None,
                                             'error_count': None,
                                             'in_progress': None,
                                             'start_time': None,
                                             'stop_time': None},
                                'categories': [{'name': 'not_started',
                                                'node_list': ['x3000c0s19b1n0',
                                                              'x3000c0s19b2n0',
                                                              'x3000c0s19b3n0']},
                                               {'name': 'in_progress',
                                                'node_list': []},
                                               {'name': 'succeeded',
                                                'node_list': []},
                                               {'name': 'failed',
                                                'node_list': []},
                                               {'name': 'excluded',
                                                'node_list': []}
                                               ],
                                'errors': {'Sloth': ['x3000c0s19b1n0'],
                                           'Greed': ['x3000c0s19b2n0'],
                                           'Hubris': ['x3000c0s19b3n0']}
                                },
                               {'name': 'boot',
                                'metadata': {'complete': None,
                                             'error_count': None,
                                             'in_progress': None,
                                             'start_time': None,
                                             'stop_time': None},
                                'categories': [{'name': 'not_started',
                                                'node_list': ['x3000c0s19b1n0',
                                                              'x3000c0s19b2n0',
                                                              'x3000c0s19b3n0']},
                                               {'name': 'in_progress',
                                                'node_list': []},
                                               {'name': 'succeeded',
                                                'node_list': []},
                                               {'name': 'failed',
                                                'node_list': []},
                                               {'name': 'excluded',
                                                'node_list': []}
                                               ],
                                'errors': {'Sloth': ['x3000c0s19b1n0'],
                                           'Greed': ['x3000c0s19b2n0'],
                                           'Hubris': ['x3000c0s19b3n0']}

                                },
                               {'name': 'configure',
                                'metadata': {'complete': None,
                                             'error_count': None,
                                             'in_progress': None,
                                             'start_time': None,
                                             'stop_time': None},
                                'categories': [{'name': 'not_started',
                                                'node_list': ['x3000c0s19b1n0',
                                                              'x3000c0s19b2n0',
                                                              'x3000c0s19b3n0']},
                                               {'name': 'in_progress',
                                                'node_list': []},
                                               {'name': 'succeeded',
                                                'node_list': []},
                                               {'name': 'failed',
                                                'node_list': []},
                                               {'name': 'excluded',
                                                'node_list': []}
                                               ],
                                'errors': {'Sloth': ['x3000c0s19b1n0'],
                                           'Greed': ['x3000c0s19b2n0'],
                                           'Hubris': ['x3000c0s19b3n0']}
                                }
                               ]
                    }


class MockResponseBootSetCreation():

    @staticmethod
    def get_json():
        return copy.deepcopy(example_boot_set)


class TestBootSet(object):

    valid_categories = ['excluded', 'failed', 'succeeded', 'not_started', 'in_progress']

    @pytest.mark.parametrize("nodes", [["x3000c0s19b1n0"],
                                       ["x3000c0s19b1n0", "x3000c0s19b2n0",
                                        "x3000c0s19b3n0"]])
    @pytest.mark.parametrize("phases", [['shutdown', 'boot', 'configure'],
                                        ['shutdown', 'boot'],
                                        ['boot', 'configure'],
                                        ['configure'],
                                        ['boot'],
                                        ['shutdown']])
    def testSaveLoadBootSet(self, phases, nodes):
        session_id = "session-123"
        boot_set_name = "boot-set1"
        ebs = copy.deepcopy(example_boot_set)
        ebs['session'] = session_id
        ebs['name'] = boot_set_name
        bs = BootSet.from_dict(ebs)
        bs.save()
        bs_comp = bs.load(session_id, boot_set_name)
        assert bs == bs_comp
        BootSet.delete(session_id, boot_set_name)

    def testLoadNoExistentBootSet(self):
        session = "session-invalid"
        bootset = "boot-set-invalid"
        with pytest.raises(BootSetDoesNotExist):
            BootSet.load(session, bootset)

    @pytest.mark.parametrize("nodes", [["x3000c0s19b1n0"],
                                       ["x3000c0s19b1n0", "x3000c0s19b2n0",
                                        "x3000c0s19b3n0"]])
    @pytest.mark.parametrize("phases", [['shutdown', 'boot', 'configure'],
                                        ['shutdown', 'boot'],
                                        ['boot', 'configure'],
                                        ['configure'],
                                        ['boot'],
                                        ['shutdown']])
    @pytest.mark.parametrize("source_category", valid_categories)
    @pytest.mark.parametrize("destination_category", valid_categories)
    def testUpdateBootSet_nodes(self, phases, nodes,
                                source_category,
                                destination_category):
        session_id = "session-123"
        boot_set_name = "boot-set1"
        ebs = copy.deepcopy(example_boot_set)
        ebs['session'] = session_id
        ebs['name'] = boot_set_name
        bs = BootSet.from_dict(ebs)
        bs_comp = BootSet.from_dict(ebs)
        assert bs == bs_comp
        moving_nodes = set(random.choices(nodes, k=random.randint(1, max([1, len(nodes) - 1]))))
        update_phase = random.choices(phases, k=1)[0]
        bs.update_nodes(update_phase, source_category, destination_category, moving_nodes)
        # bs_comp.phases[update_phase].categories[source_category].nodes -= set(moving_nodes)
        if source_category != destination_category:
            source_nodes = set(bs_comp.get_category(update_phase, source_category).node_list)
            source_nodes -= moving_nodes
            destination_nodes = set(bs_comp.get_category(update_phase, destination_category).node_list)
            destination_nodes |= moving_nodes
            bs_comp.set_category_nodes(update_phase, source_category, list(source_nodes))
            bs_comp.set_category_nodes(update_phase, destination_category, list(destination_nodes))
        assert bs == bs_comp
        BootSet.delete(session_id, boot_set_name)
        # _compare_bootset(bs, bs_comp)

    @pytest.mark.parametrize("nodes", [["x3000c0s19b1n0"],
                                       ["x3000c0s19b1n0", "x3000c0s19b2n0",
                                        "x3000c0s19b3n0"]])
    @pytest.mark.parametrize("phases", [['shutdown', 'boot', 'configure'],
                                        ['shutdown', 'boot'],
                                        ['boot', 'configure'],
                                        ['configure'],
                                        ['boot'],
                                        ['shutdown']])
    def testUpdateBootSet_errors(self, nodes, phases):
        session_id = "session-123"
        boot_set_name = "boot-set1"
        ebs = copy.deepcopy(example_boot_set)
        ebs['session'] = session_id
        ebs['name'] = boot_set_name
        bs = BootSet.from_dict(ebs)
        errors = {'Sucked': nodes,
                  'Dumb': nodes,
                  'Too beautiful to live': nodes}
        for phase in phases:
            bs.update_errors(phase, errors)
        for phase in phases:
            p = bs.get_phase(phase)
            for k, v in errors.items():
                assert v == p.errors[k]

    @pytest.mark.parametrize("phases", [['shutdown', 'boot', 'configure'],
                                        ['shutdown', 'boot'],
                                        ['boot', 'configure'],
                                        ['configure'],
                                        ['boot'],
                                        ['shutdown']])
    def testUpdateBootSet_metadata(self, phases):
        session_id = "session-123"
        boot_set_name = "boot-set1"
        ebs = copy.deepcopy(example_boot_set)
        ebs['session'] = session_id
        ebs['name'] = boot_set_name
        bs = BootSet.from_dict(ebs)
        start = datetime.datetime(1976, 9, 12, 16, 30, 0, 79043)
        stop = datetime.datetime(1977, 12, 15, 18, 30, 0, 79043)
        for phase in phases:
            bs.update_metadata_phase(phase, start, stop)
        for phase in phases:
            p = bs.get_phase(phase)
            assert start == p.metadata.start_time
            assert stop == p.metadata.stop_time


def _compare_session(session1, session2):
    assert session1.id == session2.id
    assert session1.boot_sets == session2.boot_sets


class MockResponse():

    @staticmethod
    def get_json():
        return copy.deepcoy(example_boot_set)


class MockResponse1():

    @staticmethod
    def get_json():
        resp = [{'update_type': 'NodeChangeList',
                 'phase': 'shutdown',
                 'data': {'phase': 'shutdown',
                          'source': 'not_started',
                          'destination': 'succeeded',
                          'node_list': ["x3000c0s19b1n0", "x3000c0s19b2n0", "x3000c0s19b3n0"]
                          }
                 }
                ]
        return resp


class MockResponse2():

    @staticmethod
    def get_json():
        return {'boot_sets': ['boot_set1', 'boot_set2', 'boot_set3']}


class MockResponse3():

    @staticmethod
    def get_json():
        resp = [{'update_type': 'NodeErrorsList',
                 'phase': 'shutdown',
                 'data': {'Dumb': ["x3000c0s19b1n0", "x3000c0s19b2n0"],
                          'Too beautiful to live': ["x3000c0s19b3n0"]
                          }
                 }
                ]
        return resp


class MockResponse4():

    @staticmethod
    def get_json():
        resp = [
            {'update_type': 'GenericMetadata',
             'phase': 'shutdown',
             'data': {
                 "start_time": "2020-04-24T12:00",
                 "stop_time": "2020-04-24T12:00"}
             }
        ]
        return resp


class MockResponse5():

    @staticmethod
    def get_json():
        resp = {'start_time': '1:00',
                'stop_time': '2:00'}
        return resp


class TestAPIEndpoints(object):

    valid_categories = ['excluded', 'failed', 'succeeded', 'not_started', 'in_progress']

    def mockresponse(self, *args, **kwargs):
        session_id = "1234"
        response = [
            {
                "href": "/v1/session/{}".format(session_id),
                "rel": "self"
            },
            {
                "href": "/v1/session/{}/status/boot_set1".format(session_id),
                "rel": "Boot Set"
            },
            {
                "href": "/v1/session/{}/status/boot_set2".format(session_id),
                "rel": "Boot Set"
            },
            {
                "href": "/v1/session/{}/status/boot_set3".format(session_id),
                "rel": "Boot Set"
            }
        ]
        return response

    def testCreateV1BootSetStatus(self, monkeypatch):
        session_id = "session-123"
        # import pdb;pdb.set_trace()
        # monkeypatch.setattr("flask", "url_for", mockresponse(session_id))
        # monkeypatch.setattr("url_for", "__call__", mockresponse(session_id))
        # monkeypatch.setattr("", "url_for", mockresponse(session_id))
        # monkeypatch.setattr(".", "url_for", mockresponse(session_id))
        # import pdb;pdb.set_trace()

        monkeypatch.setattr("flask.helpers.url_for", self.mockresponse)
        monkeypatch.setattr(connexion, "request", MockResponseBootSetCreation)
        boot_set_name = "test-boot-set"
        BootSet.delete(session_id, boot_set_name)
        bs, _status = create_v1_boot_set_status(session_id, boot_set_name)
        ebs = copy.deepcopy(example_boot_set)
        ebs['session'] = session_id
        ebs['name'] = boot_set_name
        bs_comp = BootSet.from_dict(ebs)
        bs_comp.initialize()
        bs_comp.metadata.start_time = bs.metadata.start_time
        _compare_bootset(bs, bs_comp)
        BootSet.delete(session_id, boot_set_name)

    def testUpdateV1SessionStatusByBootSetNodeChangeList(self, monkeypatch):

        monkeypatch.setattr("flask.helpers.url_for", self.mockresponse)
        monkeypatch.setattr(connexion, "request", MockResponseBootSetCreation)
        session_id = "session-123"
        boot_set_name = "test-boot-set"
        create_v1_boot_set_status(session_id, boot_set_name)

        monkeypatch.setattr(connexion, "request", MockResponse1)
        update_v1_session_status_by_bootset(session_id, boot_set_name)

        bs = BootSet.load(session_id, boot_set_name)
        # TODO Create a Boot Set to compare against the updated Boot Set
        nodes = ["x3000c0s19b1n0", "x3000c0s19b2n0", "x3000c0s19b3n0"]
        ebs = copy.deepcopy(example_boot_set)
        ebs['session'] = session_id
        ebs['name'] = boot_set_name
        bs_comp = BootSet.from_dict(ebs)
        bs_comp.initialize()
        bs_comp.update_nodes('shutdown', 'not_started', 'succeeded', nodes)
        _compare_bootset(bs, bs_comp)
        BootSet.delete(session_id, boot_set_name)

    def testUpdateV1SessionStatusByBootSetNodeErrorsList(self, monkeypatch):

        monkeypatch.setattr("flask.helpers.url_for", self.mockresponse)
        monkeypatch.setattr(connexion, "request", MockResponseBootSetCreation)
        session_id = "session-123"
        boot_set_name = "test-boot-set"
        create_v1_boot_set_status(session_id, boot_set_name)

        monkeypatch.setattr(connexion, "request", MockResponse3)
        update_v1_session_status_by_bootset(session_id, boot_set_name)

        bs = BootSet.load(session_id, boot_set_name)
        # TODO Create a Boot Set to compare against the updated Boot Set
        ebs = copy.deepcopy(example_boot_set)
        ebs['session'] = session_id
        ebs['name'] = boot_set_name
        bs_comp = BootSet.from_dict(ebs)
        bs_comp.initialize()
        bs_comp.update_errors('shutdown', {'Dumb': ["x3000c0s19b1n0", "x3000c0s19b2n0"],
                                           'Too beautiful to live': ["x3000c0s19b3n0"]
                                           })
        _compare_bootset(bs, bs_comp)
        BootSet.delete(session_id, boot_set_name)

    def testUpdateV1SessionStatusByBootSetGenericMetadata(self, monkeypatch):

        monkeypatch.setattr("flask.helpers.url_for", self.mockresponse)
        monkeypatch.setattr(connexion, "request", MockResponseBootSetCreation)
        session_id = "session-123"
        boot_set_name = "test-boot-set"
        create_v1_boot_set_status(session_id, boot_set_name)

        monkeypatch.setattr(connexion, "request", MockResponse4)
        update_v1_session_status_by_bootset(session_id, boot_set_name)

        bs = BootSet.load(session_id, boot_set_name)
        # TODO Create a Boot Set to compare against the updated Boot Set
        ebs = copy.deepcopy(example_boot_set)
        ebs['session'] = session_id
        ebs['name'] = boot_set_name
        bs_comp = BootSet.from_dict(ebs)
        bs_comp.initialize()
        bs_comp.update_metadata_phase('shutdown', "2020-04-24T12:00",
                                      "2020-04-24T12:00")
        _compare_bootset(bs, bs_comp)
        phase = bs.get_phase('shutdown')
        phase_comp = bs_comp.get_phase('shutdown')
        assert phase.metadata.start_time == phase_comp.metadata.start_time
        assert phase.metadata.stop_time == phase_comp.metadata.stop_time
        BootSet.delete(session_id, boot_set_name)

    def testGetV1SessionStatusByBootSet(self, monkeypatch):
        monkeypatch.setattr("flask.helpers.url_for", self.mockresponse)
        monkeypatch.setattr(connexion, "request", MockResponseBootSetCreation)
        session_id = "session-123"
        boot_set_name = "test-boot-set"
        create_v1_boot_set_status(session_id, boot_set_name)
        monkeypatch.setattr(connexion, "request", MockResponse)
        bs, status = get_v1_session_status_by_bootset(session_id, boot_set_name)
        # TODO Find a way to pass these in as parameters
        ebs = copy.deepcopy(example_boot_set)
        ebs['session'] = session_id
        ebs['name'] = boot_set_name
        bs_comp = BootSet.from_dict(ebs)
        bs_comp.initialize()
        bs_comp.metadata.start_time = bs.metadata.start_time
        _compare_bootset(bs, bs_comp)
        assert status == 201
        BootSet.delete(session_id, boot_set_name)

    def testGetV1SessionStatusByBootSetAndPhase(self, monkeypatch):
        monkeypatch.setattr("flask.helpers.url_for", self.mockresponse)
        monkeypatch.setattr(connexion, "request", MockResponseBootSetCreation)
        session_id = "session-123"
        boot_set_name = "test-boot-set"
        create_v1_boot_set_status(session_id, boot_set_name)
        monkeypatch.setattr(connexion, "request", MockResponse)
        bs, _status = get_v1_session_status_by_bootset(session_id, boot_set_name)
        ebs = copy.deepcopy(example_boot_set)
        ebs['session'] = session_id
        ebs['name'] = boot_set_name
        bs_comp = BootSet.from_dict(ebs)
        bs_comp.initialize()
        bs_comp.metadata.start_time = bs.metadata.start_time
        # TODO Find a way to pass these in as parameters
        phases = ['shutdown', 'boot', 'configure']
        for phase in phases:
            current_phase = get_v1_session_status_by_bootset_and_phase(session_id, boot_set_name, phase)
            _compare_phases(current_phase, bs_comp.get_phase(phase))
        BootSet.delete(session_id, boot_set_name)

    def testGetV1SessionStatusByBootSetAndPhaseAndCategory(self, monkeypatch):
        monkeypatch.setattr("flask.helpers.url_for", self.mockresponse)
        monkeypatch.setattr(connexion, "request", MockResponseBootSetCreation)
        session_id = "session-123"
        boot_set_name = "test-boot-set"
        create_v1_boot_set_status(session_id, boot_set_name)
        monkeypatch.setattr(connexion, "request", MockResponse)
        bs, _status = get_v1_session_status_by_bootset(session_id, boot_set_name)
        ebs = copy.deepcopy(example_boot_set)
        ebs['session'] = session_id
        ebs['name'] = boot_set_name
        bs_comp = BootSet.from_dict(ebs)
        bs_comp.initialize()
        bs_comp.metadata.start_time = bs.metadata.start_time
        # TODO Find a way to pass these in as parameters
        phases = ['shutdown', 'boot', 'configure']
        for phase in phases:
            for category in self.valid_categories:
                current_category = get_v1_session_status_by_bootset_and_phase_and_category(session_id,
                                                                                           boot_set_name,
                                                                                           phase,
                                                                                           category)
                category_comp = bs_comp.get_category(phase, category)
                _compare_categories(current_category, category_comp)
        BootSet.delete(session_id, boot_set_name)

    def testCreateV1SessionStatus(self, monkeypatch):

        session_id = "session-123"
        monkeypatch.setattr("flask.helpers.url_for", self.mockresponse)
        monkeypatch.setattr(connexion, "request", MockResponse2)
        session, _status = create_v1_session_status(session_id)

        monkeypatch.setattr(connexion, "request", MockResponseBootSetCreation)
        boot_sets = ['boot_set1', 'boot_set2', 'boot_set3']
        for boot_set_name in boot_sets:
            BootSet.delete(session_id, boot_set_name)
            _bs, _status = create_v1_boot_set_status(session_id, boot_set_name)

        # TODO Find a way to pass in these parameters
        # We cannot use the session.metadata because it is not JSON serializable
        # and the 'from_dict' method will choke on it.
        # That is why it must be converted.
        feeder_dict = {'boot_sets': boot_sets, 'id': session_id,
                       'metadata': _convert_metadata(session.metadata)}
        session_from_dict = Session.from_dict(feeder_dict)
        session_from_params = Session(boot_sets=boot_sets, metadata=session.metadata)
        session_from_params.id = session_id

        _compare_session(session, session_from_dict)
        _compare_session(session, session_from_params)
        Session.delete(session_id)

    def testGetV1SessionStatus(self, monkeypatch):
        monkeypatch.setattr("flask.helpers.url_for", self.mockresponse)
        monkeypatch.setattr(connexion, "request", MockResponse2)
        session_id = "session-123"
        create_v1_session_status(session_id)
        session, _status = get_v1_session_status(session_id)
        # TODO Find a way to pass in these parameters
        boot_sets = ['boot_set1', 'boot_set2', 'boot_set3']
        session_comp = Session(boot_sets=boot_sets, metadata=session.metadata, id=session_id)

        _compare_session(session, session_comp)
        Session.delete(session_id)

    def testUpdateV1SessionStatus(self, monkeypatch):
        monkeypatch.setattr("flask.helpers.url_for", self.mockresponse)

        session_id = "session-123"
        # Create Session Status
        monkeypatch.setattr(connexion, "request", MockResponse2)
        session, _status = create_v1_session_status(session_id)
        # TODO Find a way to pass in these parameters
        boot_sets = ['boot_set1', 'boot_set2', 'boot_set3']
        # We cannot use the session.metadata because it is not JSON serializable
        # and the 'from_dict' method will choke on it.
        # That is why it must be converted.
        feeder_dict = {'boot_sets': boot_sets, 'id': session_id,
                       'metadata': _convert_metadata(session.metadata)}
        feeder_dict['metadata']['start_time'] = '1:00'
        feeder_dict['metadata']['stop_time'] = '2:00'
        session_from_dict = Session.from_dict(feeder_dict)

        # Update Session's Status with start_time and stop_time
        monkeypatch.setattr(connexion, "request", MockResponse5)
        session, status = update_v1_session_status(session_id)

        assert status == 200
        _compare_session(session, session_from_dict)

        Session.delete(session_id)
