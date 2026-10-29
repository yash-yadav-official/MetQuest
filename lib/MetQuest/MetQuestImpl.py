# -*- coding: utf-8 -*-
#BEGIN_HEADER
import os
import sys
import shutil
import logging
from unittest.mock import patch
import cobra

# 1. The Cloud Path Injection
# KBase mounts the repo to /kb/module. We force Python to see the Raman Lab code.
module_path = os.path.abspath(os.path.join("/kb/module", "lib", "metquest_core"))
if module_path not in sys.path:
    sys.path.append(module_path)

# Now it is safe to import the original execution engine
from metquest.execute_metquest import execute_all_codes
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.KBaseReportClient import KBaseReport
try:
    from installed_clients.fba_toolsClient import fba_tools
except ImportError:
    fba_tools = None

logging.basicConfig(level=logging.INFO)
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
        logging.info("Starting MetQuest execution pipeline...")
        dfu = DataFileUtil(self.callback_url)

        # 1. Establish the nested directory structure MetQuest requires
        wrapper_dir = os.path.join(self.shared_folder, "mq_sandbox")
        target_dir = os.path.join(wrapper_dir, "batch_1")
        if os.path.exists(wrapper_dir):
            shutil.rmtree(wrapper_dir)
        os.makedirs(target_dir, exist_ok=True)

        # 2. Pull down the KBase Cloud FBAModel and convert it to a local SBML XML file
        model_input = params['input_fba_model']
        ws_name = params['workspace_name']
        logging.info(f"Downloading FBA model reference: {model_input}")

        if "/" in str(model_input):
            obj_info = dfu.get_object_info3({'objects': [{'ref': model_input}]})['infos'][0]
            model_name = obj_info[1]
            model_ws = obj_info[7]
        else:
            model_name = str(model_input)
            model_ws = ws_name

        if fba_tools is not None:
            fba = fba_tools(self.callback_url)
            model_data = fba.model_to_sbml_file({'model_name': model_name, 'workspace_name': model_ws})
        else:
            model_data = dfu._client.call_method(
                'fba_tools.model_to_sbml_file',
                [{'model_name': model_name, 'workspace_name': model_ws}],
                service_ver='release'
            )[0]

        sbml_path = os.path.join(target_dir, 'model.xml')
        shutil.copy(model_data['file_path'], sbml_path)

        # 3. Read the model via Cobra to extract the exact <model id>
        try:
            cobra_model = cobra.io.read_sbml_model(sbml_path)
            model_id = cobra_model.id if cobra_model.id else "model"
            logging.info(f"Successfully extracted Model ID prefix: {model_id}")
            sample_mets = [m.id for m in cobra_model.metabolites[:10]]
            logging.info(f"Sample metabolite IDs in SBML: {sample_mets}")
        except Exception as e:
            raise ValueError(f"Failed to parse SBML Model via Cobra: {str(e)}")

        # 4. Helper function to format and prefix metabolites
        def write_prefixed_file(filename, input_list):
            file_path = os.path.join(target_dir, filename)
            with open(file_path, 'w') as f:
                for item in (input_list or []):
                    item_str = str(item).strip()
                    if item_str:
                        clean_item = item_str if item_str.startswith(model_id + " ") else f"{model_id} {item_str}"
                        f.write(f"{clean_item}\n")

        # 5. Write the 4 configuration text files into target_dir (batch_1)
        write_prefixed_file('seed_mets.txt', params.get('seeds', []))
        write_prefixed_file('source_mets.txt', params.get('sources', []))
        write_prefixed_file('target_mets.txt', params.get('targets', []))

        user_cutoff = int(params.get('cutoff', params.get('pathway_length', 15)))
        cutoff_file_path = os.path.join(target_dir, 'cutoff.txt')
        with open(cutoff_file_path, 'w') as f:
            for i in range(1, user_cutoff + 1):
                f.write(f"{i}\n")

        # 6. Execute the MetQuest Engine Programmatically
        logging.info(f"Auto-feeding execution path to engine: {wrapper_dir}")
        try:
            with patch('builtins.input', return_value=wrapper_dir):
                execute_all_codes()
            logging.info("--- METQUEST ENGINE COMPLETED SUCCESSFULLY ---")
        except Exception as e:
            logging.error("--- METQUEST ENGINE CRASHED ---")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"MetQuest core execution engine crashed: {str(e)}")

        # 7. Package and upload the resulting pathway files back to KBase
        logging.info("Packaging MetQuest output files for KBase Report...")
        input_filenames = {'model.xml', 'seed_mets.txt', 'source_mets.txt', 'target_mets.txt', 'cutoff.txt'}
        output_files = []
        for root, _, files in os.walk(wrapper_dir):
            for file_name in files:
                if file_name in input_filenames:
                    continue
                file_path = os.path.join(root, file_name)
                output_files.append({
                    'path': file_path,
                    'name': file_name,
                    'description': f'MetQuest generated output: {file_name}'
                })

        uploaded_files = []
        if output_files:
            uploaded_files = dfu.file_to_shock_mass(output_files)

        file_links = []
        for i, file_info in enumerate(output_files):
            file_links.append({
                'shock_id': uploaded_files[i]['shock_id'],
                'name': file_info['name'],
                'label': file_info['name'],
                'description': file_info['description']
            })

        report_client = KBaseReport(self.callback_url)
        report_info = report_client.create_extended_report({
            'message': f'MetQuest graph compilation and pathway search completed successfully (cutoff={user_cutoff}). Generated {len(file_links)} output file(s).',
            'file_links': file_links,
            'workspace_name': params['workspace_name']
        })

        output = {
            'report_name': report_info['name'],
            'report_ref': report_info['ref']
        }
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
