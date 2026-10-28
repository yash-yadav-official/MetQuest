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
        print(f"Starting MetQuest run with params: {params}")
        
        # 1. Setup workspace & paths
        ws_name = params['workspace_name']
        scratch = self.shared_folder
        output_dir = os.path.join(scratch, "metquest_output")
        os.makedirs(output_dir, exist_ok=True)
        
        # 2. Initialize clients
        dfu = DataFileUtil(self.callback_url)
        fba = fba_tools(self.callback_url)
        
        # 3. Export FBAModel to SBML file
        model_ref = params['input_fba_model']
        print(f"Exporting model {model_ref} to SBML...")
        export_result = fba.export_object_as_sbml({
            'input_ref': model_ref,
            'destination_dir': scratch
        })
        sbml_path = export_result.get('file_path')
        if not sbml_path or not os.path.exists(sbml_path):
            raise ValueError(f"Failed to export model to SBML. Result: {export_result}")
        
        # 4. Prepare MetQuest text input parameters
        # MetQuest core expects model_id metabolite_id format (e.g. model_name cpd00027_c0)
        # We parse the model name from the SBML filename
        model_id = os.path.splitext(os.path.basename(sbml_path))[0]
        
        def write_met_file(filename, mets_list):
            filepath = os.path.join(scratch, filename)
            with open(filepath, 'w') as f:
                for m in mets_list:
                    f.write(f"{model_id} {m.strip()}\n")
            return filepath

        seed_file = write_met_file("seed_mets.txt", params.get('seeds', []))
        source_file = write_met_file("source_mets.txt", params.get('sources', []))
        target_file = write_met_file("target_mets.txt", params.get('targets', []))
        
        cutoff_file = os.path.join(scratch, "cutoff.txt")
        with open(cutoff_file, 'w') as f:
            f.write(str(params.get('cutoff', 15)) + "\n")
            
        # 5. Execute MetQuest core pipeline
        print("Executing MetQuest core algorithm...")
        try:
            execute_all_codes(
                xml_file=sbml_path,
                seed_file=seed_file,
                source_file=source_file,
                target_file=target_file,
                cutoff_file=cutoff_file,
                output_dir=output_dir
            )
        except Exception as e:
            raise RuntimeError(f"MetQuest execution failed: {str(e)}")
            
        # 6. Package results into KBaseReport
        print("Packaging results into KBase report...")
        report_client = KBaseReport(self.callback_url)
        
        # Upload output directory to Shock/DataFileUtil so report viewer can render it
        upload_result = dfu.file_to_shock({
            'file_path': output_dir,
            'pack': 'zip'
        })
        
        report_info = report_client.create_extended_report({
            'message': 'MetQuest pathway analysis completed successfully.',
            'direct_html_link_index': 0,
            'file_links': [{
                'shock_id': upload_result['shock_id'],
                'name': 'metquest_results.zip',
                'label': 'MetQuest Results Archive',
                'description': 'Identified metabolic pathways and output files'
            }],
            'report_object_name': 'metquest_report_' + str(os.urandom(4).hex()),
            'workspace_name': ws_name
        })
        
        output = {
            'report_name': report_info['report_name'],
            'report_ref': report_info['report_ref']
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
