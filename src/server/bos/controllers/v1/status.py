'''
Copyright 2020-2021 Hewlett Packard Enterprise Development LP
@author: Jason Sollom
'''
import connexion
import datetime
import logging
import pickle
import flask

from bos.dbclient import BosEtcdClient
from bos.models.session_status import SessionStatus as SessionStatusModel
from bos.models.boot_set_status import BootSetStatus
from bos.models.node_change_list import NodeChangeList
from bos.models.node_errors_list import NodeErrorsList
from bos.models import Link
from bos.models.generic_metadata import GenericMetadata

LOGGER = logging.getLogger(__name__)
BASEKEY = "/session"


class BaseStatusException(BaseException):
    """
    Base Exception for BOS Status
    """
    pass


class BadPhase(BaseStatusException):
    """
    The Phase is either invalid in this context or unknown.
    """
    pass


class InvalidCategory(BaseStatusException):
    """
    The Category Name is invalid.
    """
    pass


class MissingCategory(BaseStatusException):
    """
    The Category is missing.
    """
    pass


class SessionStatusDoesNotExist(BaseStatusException):
    """
    The Session Status does not exist.
    """
    pass


class BootSetDoesNotExist(BaseStatusException):
    """
    The Boot Set does not exist.
    """
    pass


class BadSession(BaseStatusException):
    """
    The Session is invalid.
    """
    pass


class Metadata(object):
    """
    Generic metadata
    Start - Time when processing started.
    Stop  - Time when processing ended
    In_Progress - processing is in progress
    error_count - The number of errors encounter; Not finalized until complete is true
    """

    def __init__(self, start=None):
        self.start_time = start
        self.stop_time = None

    @property
    def in_progress(self):
        """
        Is the object associated with this Metadata in progress?
        This method is expected to be overridden.

        Returns:
          True or False  
        """
        return False

    @property
    def error_count(self):
        """
        Are there errors with the object associated with this Metadata complete
        This method is expected to be overridden.

        Returns:
          An error count (integer)  
        """
        return 0


class MetadataSession(Metadata):
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
    A_LONG_TIME_AGO = datetime.datetime(year=1970, month=1, day=1)

    def __init__(self, session, start=None):
        self.session = session
        self._boot_sets = []
        super().__init__(start=start)

    @property
    def boot_sets(self):
        """
        Loads all of the Boot Sets in the session from the database. 
        This will only get the Boot Sets one time and cache them.
        """
        if not self.session.boot_sets:
            return []
        if not self._boot_sets:
            for bs in self.session.boot_sets:
                self._boot_sets.append(BootSet.load(self.session.id, bs))
        return self._boot_sets

    @property
    def in_progress(self):
        """
        The Session is in_progress if any Boot Set it contains is in_progress.

        Returns:
          complete (bool): True if the Session is in progress. False if it is not.
        """
        in_progress = False
        for bs in self.boot_sets:
            if bs.metadata.in_progress:
                in_progress = True
                break
        return in_progress

    @property
    def error_count(self):
        """
        The number of nodes that have failed in a Session. This counts all
        of the failed nodes from each Boot Set.
        """
        count = 0
        for bs in self.boot_sets:
            count += bs.metadata.error_count
        return count

    @property
    def start_date(self):
        try:
            return datetime.datetime(self.metadata.start_time, self.DATETIME_FORMAT)
        except:  # noqa: E722
            return self.A_LONG_TIME_AGO

    @property
    def end_date(self):
        try:
            return datetime.datetime(self.metadata.stop_time, self.DATETIME_FORMAT)
        except:  # noqa: E722
            return self.A_LONG_TIME_AGO

    @property
    def complete(self):
        """
        We operationally define completion as any session that is started sooner than
        it has stopped. This means that it is imperative that BOA marks the end time of
        the session for this logic to make sense. In short, your status records are only
        as accurate as you can keep them.
        """
        return self.start_date > self.end_date


class MetadataBootSet(Metadata):

    def __init__(self, boot_set, start=None):
        self.boot_set = boot_set  # This is a reference to the boot set, not its name.
        super().__init__(start=start)

    @property
    def in_progress(self):
        """
        The Boot Set is in_progress if any Phase it contains is in_progress.

        Returns:
          complete (bool): True if the Boot Set is in progress. False if it is not.
        """
        in_progress = False
        for p in self.boot_set.phases:
            if p.metadata.in_progress:
                in_progress = True
                break
        return in_progress

    @property
    def complete(self):
        """
        The Boot Set is complete when each phase it contains is complete.

        Returns:
          complete (bool): True if the Boot Set is complete. False if it is not.
        """
        complete = True
        for p in self.boot_set.phases:
            if not p.metadata.complete:
                complete = False
                break
        return complete

    @property
    def error_count(self):
        """
        The number of nodes that have failed in a Boot Set. This counts all
        of the failed nodes from each phase.
        """
        count = 0
        for p in self.boot_set.phases:
            count += p.metadata.error_count
        return count


class MetadataPhase(Metadata):

    def __init__(self, boot_set, phase_name, start):
        self.boot_set = boot_set  # This is a reference to the boot set, not its name.
        self.phase = boot_set.get_phase(phase_name)
        super().__init__(start=start)

    @property
    def in_progress(self):
        """
        The Phase is in_progress if there are any nodes in the in_progress category.

        Returns:
          in_progress (bool): True if the Phase is in progress. False if it is not.
        """
        return len(self.boot_set.get_category(self.phase.name, 'in_progress').node_list) != 0

    @property
    def complete(self):
        """
        The Phase is complete if there are no nodes in the not_started or in_progress
        categories. Is that true? What about in the failed state? 

        Returns:
          complete (bool): True if the Boot Set is complete. False if it is not.
        """
        if (len(self.boot_set.get_category(self.phase.name, 'not_started').node_list) != 0
            or len(self.boot_set.get_category(self.phase.name,  # noqa: W503
                                              'in_progress').node_list) != 0):
            return False
        return True

    @property
    def error_count(self):
        """
        The number of nodes that have failed in a phase. 
        """
        return len(self.boot_set.get_category(self.phase.name, 'failed').node_list)


class BootSet(BootSetStatus):
    """
    A Boot Set operates on one or more nodes. This operation will have one or more phases.
    This records the status for a Boot Set.

    The BootSet is a composite of the BootSetStatus and various useful methods. 
    I did not make it a subclass of BootSetStatus because I need to convert it back to
    the BootSetStatus when I return it. It is easier to return just an attribute of
    this class rather than attempting to strip out the methods.
    """

    def _create_links(self):
        self_url = flask.helpers.url_for(
            '.bos_controllers_v1_status_get_v1_session_status_by_bootset', session_id=self.session,
            boot_set_name=self.name)
        self.links = [Link(rel='self', href=self_url)]

        for phase in self.phases:
            self.links.append(
                Link(
                    rel='Phase',
                    href="{}/{}".format(self_url, phase.name))
            )

    def initialize(self):
        """
        If no metadata has been specified, it initializes the metadata.
        It also creates the links
        """
        # TODO: Decide. I could have an additional property called
        # nonjson_metadata = Metadata(start_time=self._metadata.start_time)
        # if not self._metadata:
        start_value = None
        if hasattr(self.metadata, "start_time"):
            start_value = self.metadata.start_time
        self.metadata = MetadataBootSet(self, start=start_value)

        # Convert the metadata to MetadataPhase
        for i, _ in enumerate(self.phases):
            start_value = None
            if hasattr(self.phases[i].metadata, "start_time"):
                start_value = self.phases[i].metadata.start_time
            self.phases[i].metadata = MetadataPhase(self,
                                                    self.phases[i].name,
                                                    start=start_value)

        self._create_links()

    def start(self, time=None):
        if not self.metadata.start_time:
            if not time:
                self.metadata.start_time = datetime.datetime.now()
            else:
                self.metadata.start_time = time

    def stop(self, time=None):
        if not self.metadata.stop_time:
            if not time:
                self._metadata.stop_time = datetime.datetime.now()
            else:
                self._metadata.stop_time = time

    def save(self):
        """
        Save the Boot Set 
        """
        with BosEtcdClient() as bec:
            key = "{}/{}/status/{}".format(BASEKEY, self.session, self.name)
            bec.put(key=key, value=pickle.dumps(self))

    @classmethod
    def load(cls, session, name):
        """
        Load the Boot Set.

        Returns:
          A Boot Set instance
        """
        with BosEtcdClient() as bec:
            key = "{}/{}/status/{}".format(BASEKEY, session, name)
            value, _ = bec.get(key)
            if not value:
                raise BootSetDoesNotExist("ERROR: Boot Set %s not found.", name)
        return pickle.loads(value)

    @classmethod
    def delete(cls, session, name):
        """
        Delete the Boot Set

        Return:
          status (int): Returns a True if it was deleted, False if it
                        did not exist
        """
        try:
            BootSet.load(session, name)
        except BootSetDoesNotExist:
            return False
        except Exception:
            # For unexpected exceptions, just delete the key.
            pass

        with BosEtcdClient() as bec:
            key = "{}/{}/status/{}".format(BASEKEY, session, name)
            bec.delete(key)
            return True

    def update_nodes(self, phase, source, destination, nodes):
        """
        Update a phase's status. This involves moving a node from one category 
        to another.

        Args:
          phase (string): The phase we are updating
          source (string): The category the node started in
          destination (string): The category the node moved to
          nodes (set): The nodes moving 
        """
        try:

            if source == destination:
                LOGGER.warning("The source and destination are the same. Doing nothing.")
                return

            phase_index = self._get_phase_index(phase)
            source_index = self._get_category_index(phase, source)
            destination_index = self._get_category_index(phase, destination)
            if source_index is None:
                raise MissingCategory("The source category is missing.")
            if destination_index is None:
                raise MissingCategory("The destination category is missing.")

            set_nodes = set(nodes)
            source_nodes = set(self.phases[phase_index].categories[source_index].node_list)
            destination_nodes = set(self.phases[phase_index].categories[destination_index].node_list)
            not_in_source = set_nodes - source_nodes
            if not_in_source:
                LOGGER.warning("The following nodes were supposed to move from %s to %s, "
                               "but they were never in %s: %s",
                               source, destination, source, not_in_source)
                LOGGER.warning("Regardless, they are being moved to %s", destination)
            source_nodes -= set_nodes
            destination_nodes |= set_nodes
            self.phases[phase_index].categories[source_index].node_list = list(source_nodes)
            self.phases[phase_index].categories[destination_index].node_list = list(destination_nodes)
        except KeyError:
            raise

    def update_errors(self, phase_name, errors):
        """
        Update a phase's list of errors
        """
        phase = self.get_phase(phase_name)
        phase_index = self._get_phase_index(phase_name)
        if phase.errors is None:
            phase.errors = {}
        if not phase.errors:
            phase.errors = errors
            self.phases[phase_index] = phase
            return

        for error, nodes in errors.items():
            if phase.errors:
                if error in phase.errors:
                    old_nodes = set(phase.errors[error])
                    new_nodes = set(nodes)
                    all_nodes = set.union(old_nodes, new_nodes)
                    phase.errors[error] = list(all_nodes)
                    break
                else:
                    phase.errors.update({error: nodes})

        self.phases[phase_index] = phase

    def update_metadata_phase(self, phase, start=None, stop=None):
        """
        Update a phase's metadata
        """
        phase = self.get_phase(phase)
        if start:
            phase.metadata.start_time = start
        if stop:
            phase.metadata.stop_time = stop

    def _get_phase_index(self, phase_name):
        """
        Return the index of the phase

        Args:
          phase_name (str): The phase's name
        """
        pi = None
        for phase_index, p in enumerate(self.phases):
            if phase_name.lower() == p.name.lower():
                pi = phase_index
                break
        return pi

    def get_phase(self, phase):
        """
        Return the phase
        """
        pi = None
        for phase_index, p in enumerate(self.phases):
            if phase.lower() == p.name.lower():
                pi = phase_index
                break
        if pi is not None:
            return self.phases[pi]
        else:
            raise BadPhase("Phase '{}' is not found.".format(phase))

    def _get_category_index(self, phase, category):
        """
        Return the index of the phase category
        """
        phase_index = self._get_phase_index(phase)
        ci = None
        for category_index, c in enumerate(self.phases[phase_index].categories):
            if category.lower() == c.name.lower():
                ci = category_index
                break
        return ci

    def get_category(self, phase, category):
        """
        Args:
          phase (string): The phase we are interested in
          category (string): Category to retrieve

        Returns:
          PhaseCategory object
        """
        phase_index = self._get_phase_index(phase)
        category_index = self._get_category_index(phase, category)
        return self.phases[phase_index].categories[category_index]

    def set_category_nodes(self, phase, category, nodes):
        """
        Args:
          nodes (list): A list of nodes
          phase (string): The phase we are interested in
          category (string): Category to retrieve
        """
        phase_index = self._get_phase_index(phase)
        category_index = self._get_category_index(phase, category)
        self.phases[phase_index].categories[category_index].node_list = list(nodes)

    def get_all_categories(self, phase):
        """
        Returns:
          A dictionary of all categories in the phase
          Key is the category name. The value is a PhaseCategory object
        """
        phase_index = self._get_phase_index(phase)
        return self.phases[phase_index].categories


class SessionStatus(SessionStatusModel):
    """
    A Session lists the boot sets it contains as well as some metadata.

    Args:
    session (string): The Session ID
    boot_sets (string): A list contains the names of the boot sets in the session
    """

    def _create_links(self):
        self_url = flask.helpers.url_for('.bos_controllers_v1_status_get_v1_session_status',
                                         session_id=self.id)
        self.links = [Link(rel='self', href=self_url)]
        if not self.boot_sets:
            return
        for bs in self.boot_sets:
            self.links.append(
                Link(
                    rel='Boot Set',
                    href="{}/{}".format(self_url, bs))
            )

    def initialize(self):
        """
        It converts any original metadata into the operational metadata.
        It creates links.
        """
        start_value = None
        if hasattr(self.metadata, "start_time"):
            start_value = self.metadata.start_time
        self.metadata = MetadataSession(self, start=start_value)
        self._create_links()

    def start(self, time=None):
        if not self.metadata.start_time:
            if not time:
                self._metadata.start_time = datetime.datetime.now()
            else:
                self._metadata.start_time = time

    def stop(self, time=None):
        if not self.metadata.stop_time:
            if not time:
                self._metadata.stop_time = datetime.datetime.now()
            else:
                self._metadata.stop_time = time

    def save(self):
        """
        Save the Session 
        """
        with BosEtcdClient() as bec:
            key = "{}/{}/status".format(BASEKEY, self.id)
            bec.put(key=key, value=pickle.dumps(self))

    @classmethod
    def load(cls, session_id):
        """
        Load the Session.

        Returns:
          A Session instance
        """
        with BosEtcdClient() as bec:
            key = "{}/{}/status".format(BASEKEY, session_id)
            value, _ = bec.get(key)
            if not value:
                raise SessionStatusDoesNotExist("ERROR: Session %s not found.", session_id)
        return pickle.loads(value)

    @classmethod
    def delete(cls, session_id):
        """
        Delete the Session

        Return:
          status (int): Returns a True if it was deleted, False if it
                        did not exist
        """
        try:
            SessionStatus.load(session_id)
        except SessionStatusDoesNotExist:
            return False
        except Exception:
            # For unexpected exceptions, just delete the key.
            pass
        with BosEtcdClient() as bec:
            key = "{}/{}/status".format(BASEKEY, session_id)
            bec.delete(key)
            return True


def create_v1_session_status(session_id):
    """
    Create a Status for the Session

    Args:
        session (string): Session ID
    """
    LOGGER.debug("create_v1_session_status: %s/status/", session_id)
    # Look up the Session. If it already exists, do not create a new one, but
    # return a 409.
    try:
        session_status = None
        status = 409
        session_status = SessionStatus.load(session_id)
    except SessionStatusDoesNotExist:
        request_body = connexion.request.get_json()
        LOGGER.debug("Request body: {}".format(request_body))
        request_body['id'] = session_id
        session_status = SessionStatus.from_dict(request_body)
        session_status.initialize()
        session_status.start()
        session_status.save()
        status = 200
    return session_status, status


def create_v1_boot_set_status(session_id, boot_set_name):
    """
    Create a Status for Boot Set 

    Args:
        session (string): Session ID
        boot_set_name (string): Boot Set Name
        phases (list): Phases in the Boot Set (strings)
        nodes (list): Nodes in the Boot Set
    """

    LOGGER.debug("create_v1_boot_set_status: %s/status/%s", session_id,
                 boot_set_name)
    try:
        bs = BootSet.load(session_id, boot_set_name)
        status = 409
    except BootSetDoesNotExist:
        request_body = connexion.request.get_json()
        LOGGER.debug("Request body: {}".format(request_body))
        request_body['name'] = boot_set_name
        request_body['session'] = session_id
        bs = BootSet.from_dict(request_body)
        bs.initialize()
        bs.start()
        bs.save()
        status = 200
    return bs, status


def update_v1_session_status(session_id):
    """
    Update an exsisting session's status
    """
    request_body = connexion.request.get_json()
    try:
        session_status = SessionStatus.load(session_id)
    except SessionStatusDoesNotExist:
        return None, 404
    if 'start_time' in request_body:
        session_status.start(request_body['start_time'])
    if 'stop_time' in request_body:
        session_status.stop(request_body['stop_time'])
    session_status.save()
    return session_status, 200


def update_v1_session_status_by_bootset(session_id, boot_set_name):
    """
    Update an existing status for a Boot Set
    """
    request_body = connexion.request.get_json()
    try:
        bs = BootSet.load(session_id, boot_set_name)
    except BootSetDoesNotExist:
        return None, 404

    for update_item in request_body:
        if update_item['update_type'] == 'NodeChangeList':
            payload = NodeChangeList.from_dict(update_item['data'])
            bs.update_nodes(update_item['phase'],
                            payload.source,
                            payload.destination,
                            payload.node_list)
        elif update_item['update_type'] == 'NodeErrorsList':
            payload = NodeErrorsList.from_dict(update_item['data'])
            bs.update_errors(update_item['phase'],
                             payload)
        elif update_item['update_type'] == 'GenericMetadata':
            payload = GenericMetadata.from_dict(update_item['data'])
            if update_item['phase'] == 'boot_set':
                # If the 'phase' specified is boot_set, update the Boot Set's metadata.
                if payload.start_time:
                    bs.metadata.start_time = payload.start_time
                if payload.stop_time:
                    bs.metadata.stop_time = payload.stop_time
            else:
                bs.update_metadata_phase(update_item['phase'],
                                         payload.start_time,
                                         payload.stop_time)
        bs.save()


def get_v1_session_status(session_id):
    """
    List the Boot Sets in the Session, so they can be queried individually.
    Provide some metadata
    """
    try:
        session = SessionStatus.load(session_id)
        status = 200
    except SessionStatusDoesNotExist:
        status = 404
        session = None
    return session, status


def get_v1_session_status_by_bootset(session_id,
                                     boot_set_name):
    try:
        bs = BootSet.load(session_id, boot_set_name)
        status = 201
    except BootSetDoesNotExist:
        bs = None
        status = 404
    return bs, status


def get_v1_session_status_by_bootset_and_phase(session_id,
                                               boot_set_name,
                                               phase_name):
    bs = BootSet.load(session_id, boot_set_name)
    return bs.get_phase(phase_name)


def get_v1_session_status_by_bootset_and_phase_and_category(session_id,
                                                            boot_set_name,
                                                            phase_name,
                                                            category_name):
    bs = BootSet.load(session_id, boot_set_name)
    return bs.get_category(phase_name, category_name)


def delete_v1_session_status(session_id):
    if SessionStatus.delete(session_id):
        return 204
    else:
        return 404


def delete_v1_boot_set_status(session_id, boot_set_name):
    if BootSet.delete(session_id, boot_set_name):
        return 204
    else:
        return 404
