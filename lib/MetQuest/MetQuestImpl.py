# -*- coding: utf-8 -*-
#BEGIN_HEADER
import os
import sys
from unittest.mock import patch

# 1. The Cloud Path Injection
# KBase mounts the repo to /kb/module. We force Python to see the Raman Lab code.
module_path = os.path.abspath(os.path.join("/kb/module", "lib", "metquest_core"))
if module_path not in sys.path:
    sys.path.append(module_path)

# Now it is safe to import the original execution engine
from metquest.execute_metquest import execute_all_codes
#END_HEADER


class MetQuest:
    '''
    Module Name:
    MetQuest

    Module Description:
    A KBase module: MetQuest
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.0.1"
    GIT_URL = ""
    GIT_COMMIT_HASH = ""

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.shared_folder = config['scratch']
        #END_CONSTRUCTOR
        pass


    def run_metquest(self, ctx, params):
        """
        :param params: instance of type "MetQuestParams" -> structure:
           parameter "workspace_name" of String, parameter "input_fba_model"
           of String, parameter "seeds" of list of String, parameter
           "sources" of list of String, parameter "targets" of list of
           String, parameter "cutoff" of Long
        :returns: instance of type "MetQuestResults" -> structure: parameter
           "report_name" of String, parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_metquest
        #END run_metquest

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method run_metquest return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
