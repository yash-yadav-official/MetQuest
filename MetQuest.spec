/*
A KBase module: MetQuest
*/

module MetQuest {
    typedef structure {
        string workspace_name;
        string input_fba_model;
        list<string> seeds;
        list<string> sources;
        list<string> targets;
        int cutoff;
    } MetQuestParams;

    typedef structure {
        string report_name;
        string report_ref;
    } MetQuestResults;

    funcdef run_metquest(MetQuestParams params) returns (MetQuestResults output) authentication required;
};
