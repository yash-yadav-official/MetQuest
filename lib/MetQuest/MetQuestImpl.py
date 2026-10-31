# -*- coding: utf-8 -*-
#BEGIN_HEADER
import os
import re
import sys
import uuid
import io
import html
import logging
from contextlib import redirect_stdout
from unittest.mock import patch
import cobra

module_path = os.path.abspath(os.path.join("/kb/module", "lib", "metquest_core"))
if module_path not in sys.path:
    sys.path.append(module_path)

from metquest.execute_metquest import execute_all_codes
from MetQuest.baseclient import BaseClient
from Workspace.WorkspaceClient import Workspace

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
    GIT_URL = "https://github.com/yash-yadav-official/MetQuest"
    GIT_COMMIT_HASH = "main"

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.shared_folder = config['scratch']
        self.ws_url = config.get('workspace-url', 'https://kbase.us/services/ws')
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
        token = ctx.get('token')
        cb_client = BaseClient(self.callback_url, token=token)

        wrapper_dir = os.path.join(self.shared_folder, "mq_sandbox_" + str(uuid.uuid4())[:8])
        target_dir = os.path.join(wrapper_dir, "batch_1")
        os.makedirs(target_dir, exist_ok=True)

        model_input = str(params['input_fba_model']).strip()
        ws_name = params['workspace_name']

        if "/" in model_input:
            ws_client = Workspace(self.ws_url, token=token)
            obj_info = ws_client.get_object_info3({'objects': [{'ref': model_input}]})['infos'][0]
            model_name = obj_info[1]
            model_ws = obj_info[7]
        else:
            model_name = model_input
            model_ws = ws_name

        logging.info(f"Exporting FBAModel '{model_name}' from workspace '{model_ws}' to SBML...")
        model_data = cb_client.call_method(
            'fba_tools.model_to_sbml_file',
            [{'model_name': model_name, 'workspace_name': model_ws}]
        )
        temp_sbml = model_data.get('path') or model_data.get('file_path')
        if not temp_sbml:
            raise ValueError(f"Could not find SBML path in fba_tools response: {model_data}")

        try:
            cobra_model = cobra.io.read_sbml_model(temp_sbml)
            clean_id = re.sub(r'[^A-Za-z0-9_.-]', '_', model_name or cobra_model.id or "model")
            cobra_model.id = clean_id
            model_id = clean_id
            model_met_ids = {m.id for m in cobra_model.metabolites}
            met_name_map = {m.id: (m.name or m.id) for m in cobra_model.metabolites}
            rxn_name_map = {r.id: (r.name or r.id) for r in cobra_model.reactions}
            logging.info(f"Using sanitized Model ID: '{model_id}' with {len(model_met_ids)} metabolites.")
        except Exception as e:
            raise ValueError(f"Failed to parse SBML Model via Cobra: {str(e)}")

        sbml_path = os.path.join(target_dir, f"{model_id}.xml")
        cobra.io.write_sbml_model(cobra_model, sbml_path)

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

        engine_stdout = stdout_buffer.getvalue().strip() or "MetQuest execution completed."
        logging.info(f"MetQuest Console Output:\n{engine_stdout}")

        results_dir = os.path.join(target_dir, "Results")
        os.makedirs(results_dir, exist_ok=True)
        with open(os.path.join(results_dir, "MetQuest_Execution_Summary.txt"), "w") as f:
            f.write(engine_stdout + "\n")

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
                if not os.path.isfile(file_path) or os.path.getsize(file_path) == 0:
                    continue
                output_files.append({
                    'file_path': file_path,
                    'name': file_name,
                    'description': f'MetQuest generated output: {file_name}'
                })
                if file_name.endswith('.txt') and file_name != "MetQuest_Execution_Summary.txt":
                    try:
                        with open(file_path, 'r') as pf:
                            pathway_previews.append((file_name, pf.read(20000)))
                    except Exception:
                        pass

        # Extract referenced rxn and cpd IDs from stdout & previews for human-readable legend
        combined_text = engine_stdout + "\n" + "\n".join(p[1] for p in pathway_previews)
        referenced_rxns = sorted(set(re.findall(r'rxn\d+_[a-z0-9]+', combined_text)))
        referenced_cpds = sorted(set(re.findall(r'cpd\d+_[a-z0-9]+', combined_text)))

        with open(html_path, "w") as hf:
            hf.write("<html><head><meta charset='utf-8'><style>")
            hf.write("body{font-family:system-ui,-apple-system,sans-serif;padding:20px;background:#f8f9fa;color:#212529;line-height:1.5;}")
            hf.write("h2,h3{color:#0b5ed7;border-bottom:1px solid #dee2e6;padding-bottom:6px;}")
            hf.write("pre{background:#1e1e1e;color:#d4d4d4;padding:14px;border-radius:6px;overflow-x:auto;font-family:monospace;font-size:13px;}")
            hf.write("table{border-collapse:collapse;width:100%;margin-bottom:20px;background:#fff;font-size:13px;}")
            hf.write("th,td{border:1px solid #dee2e6;padding:8px 12px;text-align:left;}")
            hf.write("th{background:#e9ecef;font-weight:600;}")
            hf.write("</style></head><body>")
            hf.write(f"<h2>MetQuest Pathway Analysis Report &mdash; Model: <code>{html.escape(model_id)}</code> (Cutoff: {user_cutoff})</h2>")

            if referenced_rxns or referenced_cpds:
                hf.write("<h3>Reaction &amp; Metabolite Name Reference</h3>")
                hf.write("<table><thead><tr><th>ID</th><th>Type</th><th>Biochemical Name in Model</th></tr></thead><tbody>")
                for rid in referenced_rxns:
                    rname = rxn_name_map.get(rid) or rxn_name_map.get(f"R_{rid}") or "Reaction in model"
                    hf.write(f"<tr><td><code>{html.escape(rid)}</code></td><td>Reaction</td><td>{html.escape(rname)}</td></tr>")
                for cid in referenced_cpds:
                    cname = met_name_map.get(cid) or met_name_map.get(f"M_{cid}") or "Metabolite in model"
                    hf.write(f"<tr><td><code>{html.escape(cid)}</code></td><td>Metabolite</td><td>{html.escape(cname)}</td></tr>")
                hf.write("</tbody></table>")

            hf.write("<h3>Execution &amp; Scope Summary</h3>")
            hf.write(f"<pre>{html.escape(engine_stdout)}</pre>")
            for fname, preview in pathway_previews:
                hf.write(f"<h3>Generated Pathway File: <code>{html.escape(fname)}</code></h3><pre>{html.escape(preview)}</pre>")
            hf.write("</body></html>")

        # Fast batch upload to Shock via file_to_shock_mass (with fallback)
        file_links = []
        if output_files:
            try:
                mass_inputs = [{'file_path': f['file_path']} for f in output_files]
                uploaded_files = cb_client.call_method('DataFileUtil.file_to_shock_mass', [mass_inputs])
                for i, file_info in enumerate(output_files):
                    file_links.append({
                        'shock_id': uploaded_files[i]['shock_id'],
                        'name': file_info['name'],
                        'label': file_info['name'],
                        'description': file_info['description']
                    })
            except Exception as e:
                logging.warning(f"file_to_shock_mass fallback triggered ({e}); uploading sequentially.")
                for file_info in output_files:
                    shock_res = cb_client.call_method(
                        'DataFileUtil.file_to_shock',
                        [{'file_path': file_info['file_path']}]
                    )
                    file_links.append({
                        'shock_id': shock_res['shock_id'],
                        'name': file_info['name'],
                        'label': file_info['name'],
                        'description': file_info['description']
                    })

        report_message = (
            f"MetQuest pathway analysis completed (Model ID: {model_id}, Cutoff: {user_cutoff}). "
            f"Generated {len(file_links)} output file(s)."
        )

        try:
            html_upload = cb_client.call_method(
                'DataFileUtil.file_to_shock',
                [{'file_path': html_dir, 'pack': 'zip'}]
            )
            report_info = cb_client.call_method(
                'KBaseReport.create_extended_report',
                [{
                    'message': report_message,
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
        except Exception as e:
            logging.warning(f"HTML zip report fallback triggered ({e}); creating standard extended report.")
            report_info = cb_client.call_method(
                'KBaseReport.create_extended_report',
                [{
                    'message': report_message + "\n\n" + engine_stdout[:1500],
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
