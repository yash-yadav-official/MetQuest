# MetQuest — KBase SDK Module

A KBase Narrative application wrapping **MetQuest** (*Enumerating all possible biosynthetic pathways in metabolic networks*, Ravikrishnan et al., *Scientific Reports*, 2018) from the Computational Systems Biology Laboratory, IIT Madras.

## Overview
Given a KBase `FBAModel` object, a set of **Seed Metabolites** (currency cofactors and medium nutrients), **Source Metabolites**, **Target Metabolites**, and a **Pathway Length Cutoff**, this module:
1. Exports the `FBAModel` to SBML via `fba_tools.model_to_sbml_file` and constructs a directed bipartite reaction–metabolite graph.
2. Computes the reachable metabolic scope from the seed set via Guided Breadth-First Search (GBFS).
3. Enumerates all branched and cyclic pathways from the source(s) to the target(s) up to the specified reaction cutoff.
4. Generates an interactive KBase HTML report with biochemical name mappings and downloadable pathway text files.
