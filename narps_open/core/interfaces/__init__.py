#!/usr/bin/python
# coding: utf-8

""" Generate useful and recurrent interfaces to write pipelines """

from abc import ABC, abstractmethod

from nipype.interfaces.base.core import Interface
from nipype.interfaces.utility import Function

from narps_open.core.common import remove_directory, remove_parent_directory, remove_file

class InterfaceCreator(ABC):
    """ An abstract class to shape what interface creators must provide """

    @staticmethod
    @abstractmethod
    def create_interface() -> Interface:
        """ Return a new interface (to be defined by specialized classes) """

class RemoveParentDirectoryInterfaceCreator(InterfaceCreator):
    """ An interface creator that provides an interface allowing to remove a directory,
        given one of its child's file name.
    """

    @staticmethod
    def create_interface() -> Function:
        return Function(
            function = remove_parent_directory,
            input_names = ['_', 'file_name'],
            output_names = []
            )

class RemoveDirectoryInterfaceCreator(InterfaceCreator):
    """ An interface creator that provides an interface allowing to remove a directory """

    @staticmethod
    def create_interface() -> Function:
        return Function(
            function = remove_directory,
            input_names = ['_', 'directory_name'],
            output_names = []
            )

class RemoveFileInterfaceCreator(InterfaceCreator):
    """ An interface creator that provides an interface allowing to remove a file """

    @staticmethod
    def create_interface() -> Function:
        return Function(
            function = remove_file,
            input_names = ['_', 'file_name'],
            output_names = []
            )

class InterfaceFactory():
    """ A class to generate interfaces from narps_open.core functions """

    # A list of creators, one for each function
    creators = {
        'remove_directory' : RemoveDirectoryInterfaceCreator,
        'remove_parent_directory' : RemoveParentDirectoryInterfaceCreator,
        'remove_file' : RemoveFileInterfaceCreator
    }

    @classmethod
    def create(cls, creator_name: str):
        """ Return a new Function interface
            Arguments :
                creator_name, str : the key for the creator to be used
        """
        # Actually create the interface, using a creator
        creator = cls.creators[creator_name]
        return creator.create_interface()
