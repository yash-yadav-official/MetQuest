# MetQuest KBase Module Release Notes

## Version 0.0.1 (Initial Release)
- Integrated the `metquest` graph-theoretic pathway enumeration engine (Ravikrishnan et al., *Scientific Reports*, 2018) with KBase `FBAModel` objects.
- Added automated SBML export via `fba_tools`, bipartite reaction-metabolite NetworkX graph construction, and guided breadth-first search (GBFS) scope evaluation.
- Added interactive HTML report generation featuring biochemical reaction/compound name tables, Jaccard-dissimilar pathway summaries, bottleneck reaction frequencies, and downloadable branched/cyclic pathway files across all cutoffs.
