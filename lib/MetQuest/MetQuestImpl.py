# -*- coding: utf-8 -*-
#BEGIN_HEADER
import os
import sys
import shutil
import uuid
import io
import logging
from contextlib import redirect_stdout
from unittest.mock import patch
import cobra

module_path = os.path.abspath(os.path.join("/kb/module", "lib", "metquest_core"))
if module_path not in sys.path:
    sys.path.append(module_path)

from metquest.execute_metquest import execute_all_codes
from MetQuest.baseclient import BaseClient

logging.basicConfig(level=logging.INFO)
#END_HEADER


class MetQuest:
    '''
    Module Name:
    MetQuest

    Module Description:
    A KBase module: MetQuest
    '''

    VERSION = "0.0.1"
    GIT_URL = ""
    GIT_COMMIT_HASH = ""

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

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
        logging.info(f"Starting MetQuest execution pipeline with params: {params}")
        cb_client = BaseClient(self.callback_url, token=ctx.get('token'))

        wrapper_dir = os.path.join(self.shared_folder, "mq_sandbox_" + str(uuid.uuid4())[:8])
        target_dir = os.path.join(wrapper_dir, "batch_1")
        os.makedirs(target_dir, exist_ok=True)

        model_input = str(params['input_fba_model']).strip()
        ws_name = params['workspace_name']
        model_ref = model_input if "/" in model_input else f"{ws_name}/{model_input}"

        # Resolve exact model_name and workspace_name via async SDK run_job
        obj_info = cb_client.run_job(
            'DataFileUtil.get_object_info3',
            [{'objects': [{'ref': model_ref}]}]
        )['infos'][0]
        model_name = obj_info[1]
        model_ws = obj_info[7]

        logging.info(f"Exporting FBAModel '{model_name}' from workspace '{model_ws}' to SBML...")
        model_data = cb_client.run_job(
            'fba_tools.model_to_sbml_file',
            [{'model_name': model_name, 'workspace_name': model_ws}]
        )
        temp_sbml = model_data['file_path']

        try:
            cobra_model = cobra.io.read_sbml_model(temp_sbml)
            model_id = cobra_model.id if cobra_model.id else model_name
            model_met_ids = {m.id for m in cobra_model.metabolites}
            logging.info(f"Extracted Model ID: '{model_id}' with {len(model_met_ids)} metabolites.")
            logging.info(f"Sample SBML metabolite IDs: {list(model_met_ids)[:10]}")
        except Exception as e:
            raise ValueError(f"Failed to parse SBML Model via Cobra: {str(e)}")

        # Save SBML with filename matching model_id so MetQuest graph prefixes align
        sbml_path = os.path.join(target_dir, f"{model_id}.xml")
        shutil.copy(temp_sbml, sbml_path)

        def resolve_met_id(raw_id):
            if raw_id in model_met_ids:
                return raw_id
            if f"M_{raw_id}" in model_met_ids:
                return f"M_{raw_id}"
            if raw_id.startswith("M_") and raw_id[2:] in model_met_ids:
                return raw_id[2:]
            return raw_id

        def write_prefixed_file(filename, input_list):
            file_path = os.path.join(target_dir, filename)
            with open(file_path, 'w') as f:
                for item in (input_list or []):
                    for token in str(item).replace(',', ' ').split():
                        clean_token = token.strip()
                        if clean_token:
                            if clean_token.startswith(model_id + " "):
                                f.write(f"{clean_token}\n")
                            else:
                                resolved = resolve_met_id(clean_token)
                                f.write(f"{model_id} {resolved}\n")

        write_prefixed_file('seed_mets.txt', params.get('seeds', []))
        write_prefixed_file('source_mets.txt', params.get('sources', []))
        write_prefixed_file('target_mets.txt', params.get('targets', []))

        user_cutoff = int(params.get('cutoff', params.get('pathway_length', 15)))
        cutoff_file_path = os.path.join(target_dir, 'cutoff.txt')
        with open(cutoff_file_path, 'w') as f:
            for i in range(1, user_cutoff + 1):
                f.write(f"{i}\n")

        logging.info(f"Executing MetQuest in {wrapper_dir}...")
        original_cwd = os.getcwd()
        stdout_buffer = io.StringIO()
        try:
            with patch.object(sys, 'argv', [sys.argv[0], wrapper_dir]), \
                 patch('builtins.input', return_value=wrapper_dir), \
                 redirect_stdout(stdout_buffer):
                execute_all_codes()
        except BaseException as e:
            os.chdir(original_cwd)
            captured = stdout_buffer.getvalue()
            raise RuntimeError(f"MetQuest engine exited early: {str(e)}\nLog:\n{captured}")
        finally:
            os.chdir(original_cwd)

        engine_stdout = stdout_buffer.getvalue()
        logging.info(f"MetQuest Console Output:\n{engine_stdout}")

        results_dir = os.path.join(target_dir, "Results")
        os.makedirs(results_dir, exist_ok=True)
        with open(os.path.join(results_dir, "MetQuest_Execution_Summary.txt"), "w") as f:
            f.write(engine_stdout)

        html_dir = os.path.join(self.shared_folder, "html_report_" + str(uuid.uuid4())[:8])
        os.makedirs(html_dir, exist_ok=True)
        html_path = os.path.join(html_dir, "index.html")

        input_filenames = {f"{model_id}.xml", 'model.xml', 'seed_mets.txt', 'source_mets.txt', 'target_mets.txt', 'cutoff.txt'}
        output_files = []
        pathway_previews = []
        for root, _, files in os.walk(wrapper_dir):
            for file_name in sorted(files):
                if file_name in input_filenames or file_name.endswith(('.pickle', '.gpickle')):
                    continue
                file_path = os.path.join(root, file_name)
                output_files.append({
                    'path': file_path,
                    'name': file_name,
                    'description': f'MetQuest generated output: {file_name}'
                })
                if file_name.endswith('.txt') and file_name != "MetQuest_Execution_Summary.txt":
                    try:
                        with open(file_path, 'r') as pf:
                            pathway_previews.append((file_name, pf.read(20000)))
                    except Exception:
                        pass

        with open(html_path, "w") as hf:
            hf.write("<html><head><meta charset='utf-8'><style>")
            hf.write("body{font-family:monospace,sans-serif;padding:16px;background:#fafafa;color:#222;}")
            hf.write("pre{background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:6px;overflow-x:auto;}")
            hf.write("</style></head><body>")
            hf.write(f"<h2>MetQuest Pathway Analysis Summary (Model: {model_id}, Cutoff: {user_cutoff})</h2>")
            hf.write("<h3>Console & Scope Summary</h3>")
            hf.write(f"<pre>{engine_stdout}</pre>")
            for fname, preview in pathway_previews:
                hf.write(f"<h3>File: {fname}</h3><pre>{preview}</pre>")
            hf.write("</body></html>")

        uploaded_files = []
        if output_files:
            uploaded_files = cb_client.run_job('DataFileUtil.file_to_shock_mass', [output_files])

        file_links = []
        for i, file_info in enumerate(output_files):
            file_links.append({
                'shock_id': uploaded_files[i]['shock_id'],
                'name': file_info['name'],
                'label': file_info['name'],
                'description': file_info['description']
            })

        html_upload = cb_client.run_job(
            'DataFileUtil.file_to_shock',
            [{'file_path': html_dir, 'pack': 'zip'}]
        )

        report_info = cb_client.run_job(
            'KBaseReport.create_extended_report',
            [{
                'message': f'MetQuest pathway analysis completed (Model ID: {model_id}, Cutoff: {user_cutoff}). Generated {len(file_links)} output file(s).',
                'direct_html_link_index': 0,
                'html_links': [{
                    'shock_id': html_upload['shock_id'],
                    'name': 'index.html',
                    'label': 'MetQuest Pathway Report'
                }],
                'file_links': file_links,
                'report_object_name': 'metquest_report_' + str(uuid.uuid4())[:8],
                'workspace_name': ws_name
            }]
        )

        output = {
            'report_name': report_info['name'],
            'report_ref': report_info['ref']
        }
        #END run_metquest

        if not isinstance(output, dict):
            raise ValueError('Method run_metquest return value ' +
                             'output is not type dict as required.')
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
