
package us.kbase.metquest;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import javax.annotation.Generated;
import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * <p>Original spec-file type: MetQuestParams</p>
 * 
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "workspace_name",
    "input_fba_model",
    "seeds",
    "sources",
    "targets",
    "cutoff"
})
public class MetQuestParams {

    @JsonProperty("workspace_name")
    private java.lang.String workspaceName;
    @JsonProperty("input_fba_model")
    private java.lang.String inputFbaModel;
    @JsonProperty("seeds")
    private List<String> seeds;
    @JsonProperty("sources")
    private List<String> sources;
    @JsonProperty("targets")
    private List<String> targets;
    @JsonProperty("cutoff")
    private Long cutoff;
    private Map<java.lang.String, Object> additionalProperties = new HashMap<java.lang.String, Object>();

    @JsonProperty("workspace_name")
    public java.lang.String getWorkspaceName() {
        return workspaceName;
    }

    @JsonProperty("workspace_name")
    public void setWorkspaceName(java.lang.String workspaceName) {
        this.workspaceName = workspaceName;
    }

    public MetQuestParams withWorkspaceName(java.lang.String workspaceName) {
        this.workspaceName = workspaceName;
        return this;
    }

    @JsonProperty("input_fba_model")
    public java.lang.String getInputFbaModel() {
        return inputFbaModel;
    }

    @JsonProperty("input_fba_model")
    public void setInputFbaModel(java.lang.String inputFbaModel) {
        this.inputFbaModel = inputFbaModel;
    }

    public MetQuestParams withInputFbaModel(java.lang.String inputFbaModel) {
        this.inputFbaModel = inputFbaModel;
        return this;
    }

    @JsonProperty("seeds")
    public List<String> getSeeds() {
        return seeds;
    }

    @JsonProperty("seeds")
    public void setSeeds(List<String> seeds) {
        this.seeds = seeds;
    }

    public MetQuestParams withSeeds(List<String> seeds) {
        this.seeds = seeds;
        return this;
    }

    @JsonProperty("sources")
    public List<String> getSources() {
        return sources;
    }

    @JsonProperty("sources")
    public void setSources(List<String> sources) {
        this.sources = sources;
    }

    public MetQuestParams withSources(List<String> sources) {
        this.sources = sources;
        return this;
    }

    @JsonProperty("targets")
    public List<String> getTargets() {
        return targets;
    }

    @JsonProperty("targets")
    public void setTargets(List<String> targets) {
        this.targets = targets;
    }

    public MetQuestParams withTargets(List<String> targets) {
        this.targets = targets;
        return this;
    }

    @JsonProperty("cutoff")
    public Long getCutoff() {
        return cutoff;
    }

    @JsonProperty("cutoff")
    public void setCutoff(Long cutoff) {
        this.cutoff = cutoff;
    }

    public MetQuestParams withCutoff(Long cutoff) {
        this.cutoff = cutoff;
        return this;
    }

    @JsonAnyGetter
    public Map<java.lang.String, Object> getAdditionalProperties() {
        return this.additionalProperties;
    }

    @JsonAnySetter
    public void setAdditionalProperties(java.lang.String name, Object value) {
        this.additionalProperties.put(name, value);
    }

    @Override
    public java.lang.String toString() {
        return ((((((((((((((("MetQuestParams"+" [workspaceName=")+ workspaceName)+", inputFbaModel=")+ inputFbaModel)+", seeds=")+ seeds)+", sources=")+ sources)+", targets=")+ targets)+", cutoff=")+ cutoff)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
